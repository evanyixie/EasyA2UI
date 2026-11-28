import base64
import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture
def edge_module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import web_geometry_edge

    return web_geometry_edge


def test_never_launch_with_existing_browser_profile(edge_module, tmp_path, monkeypatch):
    def no_process(*args, **kwargs):
        pytest.fail("Launched Edge for an existing user profile")

    monkeypatch.setattr(edge_module.subprocess, "Popen", no_process)
    page = tmp_path / "local.html"
    page.touch()
    existing = tmp_path / "personal-browser"
    existing.mkdir()
    sentinel = existing / "Local State"
    sentinel.write_bytes(b"original settings")
    with pytest.raises(FileExistsError):
        edge_module.read_report(page, existing, page)
    assert (
        list(existing.iterdir()) == [sentinel]
        and sentinel.read_bytes() == b"original settings"
    )


def test_new_marker_still_locked_during_startup(edge_module, tmp_path, monkeypatch):
    def locked(*args, **kwargs):
        raise PermissionError("The browser has not released the marker")

    monkeypatch.setattr(Path, "read_text", locked)
    assert edge_module.browser_address(tmp_path) is None


def test_marker_allows_only_the_new_local_browser(edge_module, tmp_path):
    marker = tmp_path / "DevToolsActivePort"
    assert edge_module.browser_address(tmp_path) is None
    marker.write_text("12234\n", encoding="ascii")
    assert edge_module.browser_address(tmp_path) is None
    b = "/devtools/browser/11111111-2222-3333-4444-555555555555"
    marker.write_text(f"12234\n{b}", encoding="ascii")
    assert edge_module.browser_address(tmp_path) == (12234, f"ws://127.0.0.1:12234{b}")
    for invalid in (
        "0\n" + b,
        "65536\n" + b,
        "12234\nws://external.test/",
        "12234\n" + b + "?goto=external",
    ):
        marker.write_text(invalid, encoding="ascii")
        with pytest.raises(ValueError, match="Unexpected browser endpoint"):
            edge_module.browser_address(tmp_path)


class FakeBrowser:
    def __init__(
        self,
        page,
        *,
        duplicate=False,
        navigated=False,
        report="aGVsbG8=",
        observations=(),
    ):
        self.page = page
        self.duplicate = duplicate
        self.navigated = navigated
        self.observations = iter(observations)
        self.report = report
        self.requests = []

    def send(self, data):
        self.requests.append(json.loads(data))

    def recv(self, *, timeout):
        assert timeout > 0
        r = self.requests[-1]
        out = {"id": r["id"]}
        if r["method"] == "Browser.getVersion":
            result = dict.fromkeys(
                ("product", "userAgent", "revision", "protocolVersion", "jsVersion"),
                "stub",
            )
        elif r["method"] == "Target.getTargets":
            own = {"type": "page", "targetId": "own", "url": self.page}
            result = {
                "targetInfos": [
                    {"type": "page", "targetId": "other", "url": "about:blank"},
                    own,
                ]
            }
            if self.duplicate:
                result["targetInfos"].append({**own, "targetId": "second"})
        elif r["method"] == "Target.attachToTarget":
            assert r["params"]["targetId"] == "own"
            result = {"sessionId": "own-session"}
        else:
            assert r["method"] == "Runtime.evaluate" and r["sessionId"] == "own-session"
            out["sessionId"] = "own-session"
            result = {
                "result": {
                    "value": next(
                        self.observations,
                        [
                            "file:///different-file.html"
                            if self.navigated
                            else self.page,
                            "complete",
                            self.report,
                        ],
                    )
                }
            }
        out["result"] = result
        return json.dumps(out)


def test_selects_exact_file_and_validates_report_and_runtime(edge_module):
    page = "file:///private/sample.html"
    runtime = {}
    assert (
        edge_module.measurement(FakeBrowser(page), page, time.monotonic() + 2, runtime)
        == "aGVsbG8="
    )
    assert runtime["product"] == "stub"
    transient = FakeBrowser(
        page,
        observations=[["about:blank", "complete", "unrelated"], ["", "loading", None]],
    )
    assert edge_module.measurement(transient, page, time.monotonic() + 2) == "aGVsbG8="
    after_commit = FakeBrowser(
        page, observations=[[page, "loading", ""], ["about:blank", "complete", None]]
    )
    with pytest.raises(RuntimeError, match="navigated"):
        edge_module.measurement(after_commit, page, time.monotonic() + 2)
    for client, message in (
        (FakeBrowser(page, duplicate=True), "Multiple tabs"),
        (FakeBrowser(page, navigated=True), "navigated"),
        (FakeBrowser(page, report="plain text"), "Invalid base64"),
    ):
        with pytest.raises((RuntimeError, ValueError), match=message):
            edge_module.measurement(client, page, time.monotonic() + 2)
    with pytest.raises(TimeoutError):
        edge_module.measurement(
            FakeBrowser(page, report=""), page, time.monotonic() + 0.01
        )


@pytest.mark.skipif(
    not os.environ.get("EASY_A2UI_TEST_EDGE"),
    reason="opt-in synthetic headless Edge smoke",
)
def test_real_edge_returns_layout_and_releases_disposable_profile(
    edge_module, tmp_path
):
    with TemporaryDirectory(dir=tmp_path) as folder:
        scratch = Path(folder)
        page = scratch / "synthetic.html"
        page.write_text(
            """<!doctype html><meta charset=utf-8>
            <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-test'">
            <div id="box" style="width:62px;height:29px"></div><pre id="report"></pre>
            <script nonce="test">const b=box.getBoundingClientRect();report.textContent=btoa(JSON.stringify([b.width,b.height]))</script>""",
            encoding="utf-8",
        )
        runtime = {}
        encoded = edge_module.read_report(
            page,
            scratch / "new-profile",
            Path(os.environ["EASY_A2UI_TEST_EDGE"]),
            runtime=runtime,
        )
        assert json.loads(base64.b64decode(encoded)) == [62, 29]
        assert runtime["product"].startswith("Edg/") and runtime["protocolVersion"]
    assert not scratch.exists()
