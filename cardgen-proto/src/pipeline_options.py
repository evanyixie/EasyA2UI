"""流水线运行选项：模型输出不合法时，程序要不要替它收拾。

三个选项**只影响"出错时的处置"**，不影响正常路径的产物：
  repair_plan         入口修正：info/action 去重、stat→percent、悬空关系清洗、
                      未归属字段并入首对象（都改内容集合）
  repair_card         出口修正：按校验结果缩字号、截断、降档、换组件（不改语义）
  placeholder_card    解析失败时输出占位卡（实验模式必须关，否则失败被掩盖）

默认全开，与 v3.x 的行为完全一致。实验时用环境变量或显式传参关闭，
关闭后不改变正常路径（无违规时三个选项都不做事）。

环境变量（统一前缀 CARDGEN_）：
  CARDGEN_REPAIR_PLAN=0
  CARDGEN_REPAIR_CARD=0
  CARDGEN_PLACEHOLDER_CARD=0
"""
import os
from dataclasses import dataclass, replace

ENV_PREFIX = "CARDGEN_"

_REPAIR_PLAN_ENV = ENV_PREFIX + "REPAIR_PLAN"
_REPAIR_CARD_ENV = ENV_PREFIX + "REPAIR_CARD"
_PLACEHOLDER_ENV = ENV_PREFIX + "PLACEHOLDER_CARD"

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _read_switch(env_name: str, default: bool) -> bool:
    """读一个布尔开关：未设置用默认值；写了但看不懂就按默认值处理（不静默反转）。"""
    raw = (os.environ.get(env_name) or "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    return default


@dataclass(frozen=True)
class PipelineOptions:
    """一次生成的行为选项。冻结，避免流水线中途被改。"""

    repair_plan: bool = True
    repair_card: bool = True
    placeholder_card: bool = True

    def describe(self) -> dict:
        """写进日志的形态：字段名与 dataclass 一致，便于回放实验。"""
        return {"repair_plan": self.repair_plan,
                "repair_card": self.repair_card,
                "placeholder_card": self.placeholder_card}

    def without_repair(self) -> "PipelineOptions":
        """关掉两个修复点，保留占位卡行为（对应实验里的“无补救”组）。"""
        return replace(self, repair_plan=False, repair_card=False)


def load_options(**overrides) -> PipelineOptions:
    """从环境变量读选项；overrides 用于测试或批跑脚本显式指定。"""
    base = PipelineOptions(
        repair_plan=_read_switch(_REPAIR_PLAN_ENV, True),
        repair_card=_read_switch(_REPAIR_CARD_ENV, True),
        placeholder_card=_read_switch(_PLACEHOLDER_ENV, True),
    )
    return replace(base, **overrides) if overrides else base
