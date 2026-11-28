"""Public adapter for the frozen program stages and common native-artifact exit.

Configure SIX_ARMS_FONT_REGULAR and SIX_ARMS_FONT_BOLD before importing the
layout harness. SIX_ARMS_MEASURE_PY or GENUI_ROOT can select a compatible
external reference engine; otherwise use the adjacent reference implementation.
"""

import hashlib
import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
STAGE_ERRORS = (
    ValueError,
    KeyError,
    IndexError,
    TypeError,
    RuntimeError,
    AttributeError,
    RecursionError,
)


@dataclass(frozen=True)
class LayoutEngine:
    trial: ModuleType
    model: ModuleType
    program: ModuleType
    native: ModuleType
    evidence: ModuleType
    STAGE_ERRORS = STAGE_ERRORS

    def _program_wire(self, phase, content, tree, source):
        if phase == "structure":
            obj = self.program.program_route(content)
        elif phase == "geometry":
            obj = self.program.program_geometry(tree, content)
        elif phase == "theme":
            obj = self.program.program_theme(tree, content)
        elif phase == "emit":
            rows = self.program.program_emit(
                tree, content, self.trial.context_for(source)
            )
            return "\n".join(self.trial.signature(row) for row in rows)
        else:
            raise ValueError(f"Unknown program stage: {phase}")
        return self.trial.signature(obj)

    @staticmethod
    def _native_wire(messages, newline):
        lines = (json.dumps(m, ensure_ascii=False, allow_nan=False) for m in messages)
        return (newline.join(lines) + newline).encode("utf-8")

    def _artifact(self, wire, source):
        try:
            checks = self.trial.inspect_card(
                [json.loads(line) for line in wire.splitlines()], source
            )
        except STAGE_ERRORS as exc:
            checks = {
                "errors": [f"{type(exc).__name__}: {exc}"],
                "check_exception": {"type": type(exc).__name__, "message": str(exc)},
            }
        return {
            "text": wire.decode("utf-8"),
            "sha256": hashlib.sha256(wire).hexdigest(),
            "checks": checks,
        }

    def _finish(self, messages, source, result):
        """Keep the original byte encoding, source checks, repair trace and commit rules."""
        raw = self._native_wire(messages, "\r\n")
        first = self._artifact(raw, source)
        result.update(
            first_native=first,
            final_native=first,
            first_native_after_entry_repair=result["entry"]["status"]
            == "repaired_and_valid",
        )
        if first["checks"]["errors"]:
            result.update(
                status="artifact_checks_rejected",
                failed_stage="independent_output_check",
                exit={"status": "skipped_source_check", "rounds": []},
            )
            return
        final_raw, report = self.native.repair(raw)
        result["exit"] = report
        for attempt in report["rounds"]:
            restored = self.evidence.replay_changes(raw, attempt)
            candidate = self._native_wire(restored, "\n")
            attempt["candidate"] = self._artifact(candidate, source)
            if attempt["accepted"] and candidate != final_raw:
                raise RuntimeError("Accepted repair differs from the recorded changes")
        final = first if raw == final_raw else self._artifact(final_raw, source)
        if final["checks"]["errors"]:
            report.update(uncommitted_native=final, effective_candidate_committed=False)
            result.update(
                status="artifact_checks_rejected",
                failed_stage="post_repair_output_check",
            )
            return
        result["final_native"] = final
        if report["status"] in ("no_change", "repaired"):
            result["status"] = "accepted"
        else:
            result.update(
                status={
                    "unsupported": "geometry_unknown",
                    "unresolved": "geometry_unresolved",
                }[report["status"]],
                failed_stage="reference_geometry",
            )


def load_engine():
    """Construct the existing public stages with their original shared repair."""
    # The published harness uses sibling top-level imports in both CLI and tests.
    sys.path.insert(0, str(HERE))
    try:
        modules = [
            importlib.import_module(name)
            for name in (
                "harness_v2.trial",
                "harness_v2.model_stages",
                "harness_v2.program_stages",
                "repair.native_repair",
                "repair.evidence",
            )
        ]
    finally:
        sys.path.remove(str(HERE))
    engine = LayoutEngine(*modules)
    if any(
        not Path(mod.__file__).resolve().is_relative_to(HERE)
        for mod in modules + [engine.native.fidelity]
    ):
        raise ImportError(
            "A different layout harness is loaded; start a fresh Python interpreter"
        )
    if (
        engine.native.program is not engine.program
        or engine.evidence.native is not engine.native
    ):
        raise ImportError(
            "Native repair and layout stages must share one implementation"
        )
    explicit = os.environ.get("SIX_ARMS_MEASURE_PY")
    external = os.environ.get("GENUI_ROOT")
    expected = (
        Path(explicit)
        if explicit
        else (
            Path(external) / "src/genui_device/measure.py"
            if external
            else HERE / "reference_text_measure.py"
        )
    )
    if engine.program.MEASURE_FILE is None and not explicit and not external:
        engine.program.MEASURE_FILE = expected
    configured = (
        (engine.program.MEASURE_FILE, expected),
        (engine.program.REGULAR, os.environ.get("SIX_ARMS_FONT_REGULAR")),
        (engine.program.BOLD, os.environ.get("SIX_ARMS_FONT_BOLD")),
    )
    for actual, wanted in configured:
        present = actual.resolve() if actual else None
        requested = Path(wanted).resolve() if wanted else None
        if present != requested:
            raise RuntimeError(
                "Reference paths changed after import; restart Python with the desired environment"
            )
    engine.native.dependency_files()
    return engine
