"""Read a generated local measurement page via a fresh headless Edge instance."""

import base64
import binascii
import json
import os
import re
import socket
import subprocess
import time
from contextlib import suppress
from itertools import count
from pathlib import Path


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError("Timed out waiting for the isolated Edge measurement")
    return seconds


def browser_address(profile):
    """Trust only the browser endpoint written to this invocation's new profile."""
    marker = profile / "DevToolsActivePort"
    try:
        lines = marker.read_text(encoding="ascii").splitlines()
    except (FileNotFoundError, PermissionError):
        # Windows can still hold the exclusive creation handle for this marker.
        # connect_browser applies the same finite startup deadline in both cases.
        return None
    if len(lines) < 2:
        return None  # The new process can still be writing the marker.
    if (
        len(lines) != 2
        or not re.fullmatch(r"[0-9]{1,5}", lines[0])
        or not 1 <= int(lines[0]) <= 65535
        or not re.fullmatch(
            r"/devtools/browser/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",
            lines[1],
        )
    ):
        raise ValueError("Unexpected browser endpoint in the new temporary profile")
    port = int(lines[0])
    return port, f"ws://127.0.0.1:{port}{lines[1]}"


def connect_browser(profile, deadline):
    from websockets.sync.client import connect

    while True:
        address = browser_address(profile)
        if address is not None:
            port, uri = address
            # Connect directly even if the environment has configured network proxies.
            try:
                sock = socket.create_connection(
                    ("127.0.0.1", port), timeout=remaining(deadline)
                )
            except ConnectionRefusedError:
                pass
            else:
                try:
                    return connect(
                        uri,
                        sock=sock,
                        proxy=None,
                        open_timeout=remaining(deadline),
                        close_timeout=1,
                        ping_interval=None,
                        max_size=16 << 20,
                    )
                except BaseException:
                    sock.close()
                    raise
        time.sleep(min(0.05, remaining(deadline)))


def command(ws, number, method, params, session, deadline):
    request = {"id": number, "method": method, "params": params}
    if session is not None:
        request["sessionId"] = session
    ws.send(json.dumps(request))
    while True:
        response = json.loads(ws.recv(timeout=remaining(deadline)))
        if response.get("id") == number:
            if response.get("sessionId") != session or "error" in response:
                raise RuntimeError(f"Edge rejected the measurement command {method}")
            return response["result"]


def windows_process_waiter(ws):
    """Pin process handles before closing this browser so its cache files unlock."""
    if os.name != "nt":
        return lambda: None
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    processes = command(
        ws, -2, "SystemInfo.getProcessInfo", {}, None, time.monotonic() + 2
    )["processInfo"]
    handles = [
        h
        for proc in processes
        if (h := kernel.OpenProcess(0x00100000, False, proc["id"]))
    ]

    def wait_for_profile_release():
        deadline = time.monotonic() + 8
        try:
            for h in handles:
                if (
                    kernel.WaitForSingleObject(
                        h, max(0, int((deadline - time.monotonic()) * 1000))
                    )
                    != 0
                ):
                    raise RuntimeError(
                        "Edge did not release the isolated profile before timeout"
                    )
        finally:
            for h in handles:
                kernel.CloseHandle(h)

    return wait_for_profile_release


def measurement(ws, page_url, deadline, runtime=None):
    ids = count(1)

    def call(method, params=None, session=None):
        return command(ws, next(ids), method, params or {}, session, deadline)

    version = call("Browser.getVersion")
    if runtime is not None:
        runtime.update(
            {
                k: version[k]
                for k in (
                    "product",
                    "userAgent",
                    "revision",
                    "protocolVersion",
                    "jsVersion",
                )
            }
        )
    while True:
        infos = call("Target.getTargets")["targetInfos"]
        matches = [t for t in infos if t["type"] == "page" and t["url"] == page_url]
        if len(matches) > 1:
            raise RuntimeError("Multiple tabs match the isolated measurement page")
        if matches:
            break
        time.sleep(min(0.05, remaining(deadline)))
    session = call(
        "Target.attachToTarget", {"targetId": matches[0]["targetId"], "flatten": True}
    )["sessionId"]
    expression = "[location.href, document.readyState, document.querySelector('pre#report')?.textContent]"
    committed = False
    while True:
        evaluation = call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
            session,
        )
        if "exceptionDetails" in evaluation:
            raise RuntimeError("Edge could not evaluate the local measurement page")
        url, state, report = evaluation["result"]["value"]
        if not committed and url in ("", "about:blank"):
            time.sleep(min(0.05, remaining(deadline)))
            continue
        if url != page_url:
            raise RuntimeError(
                "The measurement tab navigated away from the generated file"
            )
        committed = True
        if state == "complete" and isinstance(report, str) and report:
            try:
                base64.b64decode(report, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError(
                    "Invalid base64 in the local Edge measurement report"
                ) from exc
            return report
        time.sleep(min(0.05, remaining(deadline)))


def read_report(
    page: Path, profile: Path, edge: Path, *, timeout_s: float = 30.0, runtime=None
) -> str:
    """Return base64 from pre#report. The caller owns the newly created profile.

    Requires websockets >=15. page is a generated, CSP-protected HTML file. Existing profiles are always
    rejected. The Edge launcher on Windows may exit before its child is ready.
    """
    page = Path(page).resolve(strict=True)
    edge = Path(edge).resolve(strict=True)
    profile = Path(profile).absolute()
    if not page.is_file() or not edge.is_file() or not 0 < timeout_s < float("inf"):
        raise ValueError("Expected local files and a finite positive deadline")
    page_url = page.as_uri()
    if not page_url.startswith("file:///") or (
        os.name == "nt" and str(profile).startswith("\\\\")
    ):
        raise ValueError("Local filesystem paths are required")
    profile.mkdir()  # Exclusive creation; never visit or attach to an existing profile.
    from websockets.exceptions import WebSocketException

    args = [
        str(edge),
        "--headless=new",
        f"--user-data-dir={profile}",
        "--remote-debugging-port=0",
        "--remote-debugging-address=127.0.0.1",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--disable-extensions",
        "--disable-client-side-phishing-detection",
        "--no-pings",
        "--disable-features=msEdgeSidebarV2,OptimizationHints",
        "--force-device-scale-factor=1",
        "--proxy-server=http://127.0.0.1:9",
        "--host-resolver-rules=MAP * ~NOTFOUND",
        page_url,
    ]
    deadline = time.monotonic() + timeout_s
    proc = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    ws = None
    try:
        ws = connect_browser(profile, deadline)
        return measurement(ws, page_url, deadline, runtime)
    finally:
        # Close via the browser socket pinned to our own marker, never by executable name.
        if ws is None:
            with suppress(OSError, RuntimeError, WebSocketException):
                ws = connect_browser(profile, time.monotonic() + 2)
        if ws is not None:
            wait = None
            try:
                wait = windows_process_waiter(ws)
            finally:
                with suppress(OSError, RuntimeError, WebSocketException):
                    command(ws, 0, "Browser.close", {}, None, time.monotonic() + 2)
                with suppress(OSError, WebSocketException):
                    ws.close()
                if wait is not None:
                    wait()
        if proc.poll() is None:
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
