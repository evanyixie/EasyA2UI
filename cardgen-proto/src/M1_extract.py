"""LLM 接入层：pipeline 只依赖 LLMClient 接口。

两种实现：
  HttpLLM  真实模型（OpenAI 兼容 Chat Completions 端点），配置来自 config/llm.json；
  MockLLM  规则式离线模型，用于零依赖回归验证。

配置缺失或 base_url/api_key/model 任一为空时，build_llm() 自动降级为 MockLLM。

失败语义：
  LLMCallError  调用层失败（连接/超时/HTTP 错误），可重试；pipeline 记为 "M1 call fail"
  其它异常      输出解析失败，pipeline 记为 "M1 parse fail"
每次调用（含重试）都会往 logs/llm_calls.jsonl 追加一行结构化日志，便于事后分析。
"""
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# cardgen-proto 根目录（src/ 的上一级）
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "llm.json"
LOG_PATH = ROOT / "logs" / "llm_calls.jsonl"
REQUIRED_KEYS = ("base_url", "api_key", "model")


class LLMCallError(RuntimeError):
    """模型调用层失败（连接失败/读超时/HTTP 错误），区别于输出解析失败。"""


def _write_llm_log(record: dict) -> None:
    """追加一行调用日志（单行 JSONL）；日志失败不影响主流程。"""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


class LLMClient:
    """模型客户端基类：除了 complete()，还负责记"用了多少"。

    统计口径：
      calls          成功完成的调用次数（论文里的“模型调用次数”）
      attempts       实际发出的请求次数（含重试，反映真实成本）
      usage          累计 token（in/out）；端点不返回 usage 时为 None
      usage_missing  没有返回 usage 的成功调用次数（用来判断 token 指标可不可信）
    """

    def __init__(self):
        self.calls = 0
        self.attempts = 0
        self.usage = {"in": None, "out": None}
        self.usage_missing = 0

    def reset_stats(self) -> None:
        self.calls = 0
        self.attempts = 0
        self.usage = {"in": None, "out": None}
        self.usage_missing = 0

    def stats(self) -> dict:
        return {"calls": self.calls, "attempts": self.attempts,
                "in_tokens": self.usage["in"], "out_tokens": self.usage["out"],
                "usage_missing": self.usage_missing}

    def _add_usage(self, usage) -> None:
        """累加一次成功调用的 token；缺失时只记一笔 usage_missing，不估算、不编数。"""
        self.calls += 1
        pin = (usage or {}).get("prompt_tokens")
        pout = (usage or {}).get("completion_tokens")
        if pin is None or pout is None:
            self.usage_missing += 1
            return
        self.usage["in"] = (self.usage["in"] or 0) + int(pin)
        self.usage["out"] = (self.usage["out"] or 0) + int(pout)

    def complete(self, prompt: str) -> str:
        raise NotImplementedError


def stats_delta(before: dict, after: dict) -> dict:
    """两次 stats() 的差：一次生成用了多少。None 表示该端点不给 token 数。"""
    def sub(a, b):
        return None if a is None or b is None else b - a
    return {"calls": after["calls"] - before["calls"],
            "attempts": after["attempts"] - before["attempts"],
            "in_tokens": sub(before["in_tokens"], after["in_tokens"]),
            "out_tokens": sub(before["out_tokens"], after["out_tokens"]),
            "usage_missing": after["usage_missing"] - before["usage_missing"]}


def load_llm_config(path: Path = CONFIG_PATH) -> dict:
    """读取配置文件；文件缺失、内容非法或非对象时返回空 dict。"""
    if not path.exists():
        return {}
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def config_ready(cfg: dict) -> bool:
    """三项必填值都非空才算可用。"""
    return all(str(cfg.get(k) or "").strip() for k in REQUIRED_KEYS)


def build_llm(path: Path = CONFIG_PATH):
    """配置完整 → 真实模型；否则降级 MockLLM（保证任何环境都能跑通）。"""
    cfg = load_llm_config(path)
    if config_ready(cfg):
        return HttpLLM.from_config(cfg)
    return MockLLM()


class HttpLLM(LLMClient):
    """真实模型客户端：OpenAI 兼容 Chat Completions 端点，零第三方依赖。

    可靠性策略：
      1. 连接超时（connect_timeout）与读取超时（timeout）分离；
      2. 失败重试 max_retries 次，重试自动关闭 json_mode（不少端点卡在
         response_format 上），首帧慢的模型靠更大的 timeout 兜底；
      3. 所有传输层异常统一包装为 LLMCallError，与解析失败区分；
      4. 每次尝试写一行调用日志（耗时/错误类型/响应长度）。
    """

    def __init__(self, base_url: str, api_key: str, model: str,
                 temperature: float = 0.0, timeout: float = 60.0,
                 json_mode: bool = True, connect_timeout: float = 10.0,
                 max_retries: int = 1, extra_payload: dict = None):
        super().__init__()
        self.base_url, self.api_key, self.model = base_url, api_key, model
        self.temperature, self.timeout, self.json_mode = temperature, timeout, json_mode
        self.connect_timeout, self.max_retries = connect_timeout, max(0, int(max_retries))
        # 厂商私有参数透传（如 GLM 的 chat_template_kwargs.enable_thinking=false）
        self.extra_payload = dict(extra_payload or {})

    @classmethod
    def from_config(cls, cfg: dict) -> "HttpLLM":
        extra = cfg.get("extra_payload") or {}
        return cls(base_url=str(cfg["base_url"]).strip(),
                   api_key=str(cfg["api_key"]).strip(),
                   model=str(cfg["model"]).strip(),
                   temperature=float(cfg.get("temperature", 0.0) or 0.0),
                   timeout=float(cfg.get("timeout", 60) or 60),
                   json_mode=bool(cfg.get("json_mode", True)),
                   connect_timeout=float(cfg.get("connect_timeout", 10) or 10),
                   max_retries=int(cfg.get("max_retries", 1) or 0),
                   extra_payload=extra if isinstance(extra, dict) else {})

    def complete(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        netloc = urllib.parse.urlsplit(self.base_url).netloc
        host = netloc
        last_err = None
        for attempt in range(1, self.max_retries + 2):
            use_json_mode = self.json_mode and attempt == 1
            payload = {"model": self.model,
                       "messages": [{"role": "user", "content": prompt}],
                       "temperature": self.temperature, **self.extra_payload}
            if use_json_mode:
                payload["response_format"] = {"type": "json_object"}
            started = time.time()
            self.attempts += 1
            try:
                if self.connect_timeout > 0:
                    self._check_connect(host)
                data = self._post(url, payload)
                content = data["choices"][0]["message"]["content"]
                self._add_usage(data.get("usage"))
                _write_llm_log({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "outcome": "ok", "attempt": attempt,
                                "host": host, "model": self.model,
                                "json_mode": use_json_mode,
                                "prompt_chars": len(prompt),
                                "duration_ms": int((time.time() - started) * 1000),
                                "response_chars": len(content),
                                "usage": data.get("usage")})
                return content
            except Exception as e:  # 传输/解析/HTTP 各类失败均记日志后重试
                _write_llm_log({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "outcome": "error", "attempt": attempt,
                                "host": host, "model": self.model,
                                "json_mode": use_json_mode,
                                "prompt_chars": len(prompt),
                                "duration_ms": int((time.time() - started) * 1000),
                                "error_type": type(e).__name__,
                                "error": str(e)[:300]})
                last_err = e
        raise LLMCallError(f"{type(last_err).__name__}: {last_err}")

    def _check_connect(self, netloc: str) -> None:
        """连接超时独立校验：避免"根本连不上"白等满读取超时。"""
        host, _, port_part = netloc.partition(":")
        default_port = 443 if self.base_url.startswith("https") else 80
        port = int(port_part) if port_part.isdigit() else default_port
        try:
            with socket.create_connection((host, port), timeout=self.connect_timeout):
                pass
        except OSError as e:
            raise LLMCallError(f"connect timeout/error to {host}:{port}: {e}") from e

    def _post(self, url: str, payload: dict) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.load(resp)


def extract_json(text: str) -> dict:
    """从模型输出中提取第一个 JSON 对象。"""
    text = re.sub(r"```(json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json object found")
    return json.loads(text[start:end + 1])


class MockLLM(LLMClient):
    """规则式离线模型：模拟封闭域内理想模型的行为（v2 扩展契约）。

    输出合法结构计划：domain / size / theme / info_items(keep) / actions /
    objects(业务对象分组)。场景规则全部关键词命中，确定性可回归：
      歌单        -> earphone 单对象 + 图标入口动作（S6）
      手机+耳机   -> battery 双对象（S4）
      耳机        -> earphone 单对象 + 蓝牙设置动作（S2）
      天气/温度   -> weather 单对象多字段（S5 主区 + 辅区）
      促销/折扣等 -> promotion（S2 + 文字按钮动作）
      提醒/到期等 -> notice（S2）
    """

    def complete(self, prompt: str) -> str:
        q = prompt.rsplit("用户：", 1)[-1].split("\n", 1)[0].strip()

        plan = {"size": "auto", "theme": None, "relations": [], "groups": []}
        items, actions, objects = [], [], []

        def add_item(t, hint, keep="must"):
            items.append({"ref": len(items) + len(actions) + 1, "type": t,
                          "content_hint": hint[:30], "keep": keep})

        def add_action(t, hint):
            actions.append({"ref": len(items) + len(actions) + 1, "type": t,
                            "label_hint": hint[:10], "keep": "must"})

        if "设备状态" in q or ("耳机仓" in q and "电量" in q):
            # 设备/指标清单（金标 q20 形态）：多对象 × 单值 → S2 + 标签值行
            plan["domain"] = "battery"
            add_item("title", "设备状态")
            add_item("stat", "剩余电量")
            add_item("stat", "耳机仓电量")
            add_item("stat", "耳机是否连接")
            objects = [{"name_hint": "手机", "fields": [2]},
                       {"name_hint": "耳机仓", "fields": [3]},
                       {"name_hint": "耳机", "fields": [4]}]
        elif "电量" in q and "充电" in q:
            # 环形 + 状态（2 条）：content 槽 percent + stat → 环里带"未充电"一行
            plan["domain"] = "battery"
            add_item("percent", "剩余电量")
            add_item("stat", "充电状态")
            objects = [{"name_hint": "手机", "fields": [1, 2]}]
        elif "电量" in q or "剩多少电" in q:
            # 环形（1 条）：单 percent → 环 + 标签 + 数值
            plan["domain"] = "battery"
            add_item("title", "手机电量")
            add_item("percent", "剩余电量")
            objects = [{"name_hint": "手机", "fields": [2]}]
        elif any(k in q for k in ("歌单", "快捷入口", "图标入口")):
            # 图标入口（数据 M2/S6）：单动作且动作是图标钮（无文字标签）→ icon_button
            plan["domain"] = "earphone"
            add_item("title", "耳机")
            add_item("stat", "已连接")
            add_item("subtitle", "FreeBuds")
            add_action("icon_button", "歌单")
        elif "手机" in q and "耳机" in q:
            plan["domain"] = "battery"
            add_item("stat", "68%")
            add_item("subtitle", "未充电")
            add_item("stat", "47%")
            add_item("subtitle", "充电中")
            objects = [{"name_hint": "手机", "fields": [1, 2]},
                       {"name_hint": "耳机盒", "fields": [3, 4]}]
        elif "耳机" in q:
            plan["domain"] = "earphone"
            add_item("title", "FreeBuds")
            add_item("subtitle", "已连接")
            add_item("stat", "盒 95%")
            add_action("primary_button", "蓝牙设置")
        elif "天气" in q or "温度" in q or "气温" in q:
            plan["domain"] = "weather"
            add_item("title", "深圳")
            add_item("stat", "26°C")
            add_item("subtitle", "晴")
            add_item("source", "最高26°C 最低16°C", keep="should")
        elif any(k in q for k in ("促销", "折扣", "双11", "优惠", "购")):
            plan["domain"] = "promotion"
            add_item("title", "双11会员促销")
            add_item("discount", "会员折扣")
            add_item("source", "活动解释权归平台所有", keep="should")
            add_action("primary_button", "立即购买")
            plan["relations"] = [{"from": 4, "to": 2, "type": "binds"},
                                 {"from": 3, "to": 1, "type": "secondary"}]
            plan["groups"] = [{"type": "section", "children": [1]},
                              {"type": "unit", "children": [2, 4]},
                              {"type": "aside", "children": [3]}]
        elif any(k in q for k in ("提醒", "到期", "通知")):
            plan["domain"] = "notice"
            add_item("title", "会员到期提醒")
            add_item("deadline", "请关注有效期")
            plan["relations"] = [{"from": 2, "to": 1, "type": "order_before"}]
            plan["groups"] = [{"type": "section", "children": [1, 2]}]
        else:
            plan["domain"] = "unknown"
            m = re.search(r"标题[是为]?[“\"'](.{2,}?)[”\"']", q)
            add_item("title", m.group(1) if m else (q[:12] or "未命名卡片"))

        plan["info_items"] = items
        plan["actions"] = actions
        plan["objects"] = objects
        # 桩模型没有 token 概念：记一次调用，token 记为缺失（不估算、不编数）
        self.calls += 1
        self.usage_missing += 1
        return json.dumps(plan, ensure_ascii=False)
