"""Two invented, offline cases for the public layout selector and common exit.

From a checkout, install Pillow, then run this file with Python 3.11+:
    python portable_layout_smoke.py --regular regular.ttf --bold bold.ttf
Without font arguments the demo tries a local Latin regular/bold pair. Font
fingerprints and runtime versions are printed alongside the artifact digests.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import ImageFont, features
from PIL import __version__ as pillow_version

if __package__:
    from .portable_layout_engine import load_engine
else:
    from portable_layout_engine import load_engine


def smoke_fonts(regular=None, bold=None):
    regular = regular or os.getenv("SIX_ARMS_FONT_REGULAR")
    bold = bold or os.getenv("SIX_ARMS_FONT_BOLD")
    if bool(regular) != bool(bold):
        raise ValueError("Please provide both regular and bold font paths")
    if regular:
        return Path(regular).resolve(strict=True), Path(bold).resolve(strict=True)
    for names in (
        ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
        ("segoeui.ttf", "segoeuib.ttf"),
        ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"),
        ("Arial.ttf", "Arial Bold.ttf"),
    ):
        try:
            return tuple(
                Path(ImageFont.truetype(n, 14).path).resolve(strict=True) for n in names
            )
        except OSError:
            continue
    raise ValueError("Set --regular and --bold to two readable TrueType font files")


def samples(engine):
    for size, title, records in (
        ("2x2", "Cabinet", [("North", 18)]),
        ("2x4", "Two probes", [("North", 18), ("South", 21)]),
    ):
        query = f"Show {title} temperature readings and open the log."
        handler = {"call": "openLog", "args": {"target": "demo"}}
        bindings = [
            {
                "writeResultTo": "/sensor",
                "candidateOutputFields": [label for label, _ in records],
            }
        ]
        request = {
            "size": size,
            "title": title,
            "userQuery": query,
            "candidateDataBindings": bindings,
            "candidateEventCandidates": [
                {"label": "Log", "action": handler, "capabilityId": "synthetic.log"}
            ],
        }
        source = engine.trial.source_for(request, {"sensor": dict(records)})
        effective = {
            "size": size,
            "domain": "demo",
            "title": title,
            "items": [
                {
                    "id": "probe" + str(i),
                    "text": str(value),
                    "path": "/sensor/" + label,
                    "unit": "C",
                    "entity": label,
                    "label": label,
                    "role": "primary",
                }
                for i, (label, value) in enumerate(records)
            ],
            "actions": [{"id": "a1", "label": "Log"}],
        }
        content = engine.model.parse_output(
            "content", engine.trial.signature(effective), source
        )
        yield source, content


def smoke(engine):
    if __package__:
        from .portable_enhanced_layout import advance, select
    else:
        from portable_enhanced_layout import advance, select
    cases = []
    for source, content in samples(engine):
        size = source["size"]
        tree = engine.program.program_route(content)
        current = engine.model.parse_output(
            "structure", engine.trial.signature(tree), source, content=content
        )
        for phase in ("geometry", "theme", "emit"):
            current = advance(engine, phase, content, current, source)
        result = {"entry": {"status": "valid_unchanged"}}
        engine._finish(current, source, result)
        if result["status"] != "accepted":
            raise RuntimeError(
                f"Common exit rejected synthetic {size}: {result['status']}"
            )
        checks = result["final_native"]["checks"]
        if sorted(checks["bound_paths"]) != sorted(source["candidate_paths"]) or checks[
            "action_handlers"
        ] != [engine.trial.signature(source["candidate_actions"][0]["handler"])]:
            raise RuntimeError("Synthetic test lost a bound fact or changed its action")
        expected = result["final_native"]["sha256"]
        outputs, decision = select(
            "synthetic-" + size, content, source, result["entry"], engine
        )
        if outputs != {"compatible": expected, "standard": expected}:
            raise RuntimeError(
                f"Policies did not preserve the passing standard-font baseline for {size}"
            )
        cases.append(
            {
                "size": size,
                "data_items": len(content["items"]),
                "actions": len(content["actions"]),
                "first_sha256": result["first_native"]["sha256"],
                "final_sha256": expected,
                "common_exit": result["exit"]["status"],
                "policy_decisions": decision,
            }
        )
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regular", type=Path)
    parser.add_argument("--bold", type=Path)
    args = parser.parse_args()
    regular, bold = smoke_fonts(args.regular, args.bold)
    os.environ.update(SIX_ARMS_FONT_REGULAR=str(regular), SIX_ARMS_FONT_BOLD=str(bold))
    engine = load_engine()
    evidence = {
        "kind": "synthetic offline smoke",
        "new_model_calls": 0,
        "new_device_calls": 0,
        "pillow": pillow_version,
        "freetype": features.version_module("freetype2"),
        "reference_sha256": {
            k: hashlib.sha256(v.read_bytes()).hexdigest()
            for k, v in engine.native.dependency_files().items()
        },
        "cases": smoke(engine),
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
