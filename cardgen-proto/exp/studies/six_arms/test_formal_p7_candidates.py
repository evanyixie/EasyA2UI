import json
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture
def p7(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import formal_p7_candidates

    return formal_p7_candidates


def test_facts_reordered_handlers_with_same_capability(p7):
    actions = [
        {"capabilityId": "open", "action": {"call": "x", "args": {"to": k}}}
        for k in ("left", "right")
    ]
    request = {
        "size": "2x4",
        "userQuery": "synthetic",
        "candidateEventCandidates": actions,
        "candidateDataBindings": [{}],
    }
    source = {
        "request": request,
        "candidate_paths": ["/second", "/first"],
        "candidate_actions": [
            {"id": "a1", "capabilityId": "open"},
            {"id": "a2", "capabilityId": "open"},
        ],
    }
    original = {
        "request": request,
        "choices": [["D1.1", "/first"], ["A1", "open"], ["A2", "open"]],
    }
    before = p7.compare_question(original, source)
    assert (before["missing_fields"], before["tasks_with_same_field_set"]) == (1, 0)
    revised = {**original, "choices": [*original["choices"], ["F1.1", "/second"]]}
    done = p7.compare_question(revised, source)
    assert (
        done["missing_fields"],
        done["tasks_with_same_field_set"],
        done["tasks_same_field_set_different_order"],
    ) == (0, 1, 1)
    assert done["tasks_with_added_fields_shown_after_an_action"] == 1
    assert (
        done["tasks_same_action_id_and_capability_order"]
        == done["tasks_same_full_ordered_action_definitions"]
        == 1
    )
    reversed_handlers = {
        **revised,
        "request": {**request, "candidateEventCandidates": list(reversed(actions))},
    }
    bad = p7.compare_question(reversed_handlers, source)
    assert (
        bad["tasks_same_action_id_and_capability_order"] == 1
        and bad["tasks_same_full_ordered_action_definitions"] == 0
    )
    duplicate = {**revised, "choices": [*revised["choices"], ["F2.1", "/first"]]}
    assert p7.compare_question(duplicate, source)["duplicate_field_choices"] == 1
    with pytest.raises(ValueError):
        p7.compare_question(
            {**revised, "choices": [*revised["choices"], ["A2", "open"]]}, source
        )


def test_archived_html_and_blind_map(p7, tmp_path, monkeypatch):
    role = "synthetic"
    monkeypatch.setitem(p7.ROLES, role, 1)
    case = {"id": "blind", "choices": [], "request": {}}
    packet = {"mode": "must", "version": "v", "role": role, "cases": [case]}
    data = json.dumps(packet).encode()
    html = b"<script>const p=" + data + b";</script>"
    directory = tmp_path / role
    directory.mkdir()
    (directory / p7.FILES[0]).write_bytes(data)
    (directory / p7.FILES[1]).write_bytes(html)
    archive = tmp_path / "packet.zip"
    with ZipFile(archive, "w") as z:
        for n in p7.FILES:
            z.write(directory / n, n)
    hashes = {
        f"{role}/{name}": p7.digest((directory / name).read_bytes())
        for name in p7.FILES
    }
    admin = {
        "packets": {
            role: {"version": "v", "blind_to_task": {"blind": "synthetic-task"}}
        },
        "package_file_sha256": hashes,
    }
    monkeypatch.setitem(p7.HANDOFF, role, p7.digest(archive.read_bytes()))
    rows, _ = p7.load_packet(tmp_path, admin, role, archive)
    assert p7.overlap(rows, rows) == {
        "tasks": 1,
        "same_checkbox_ids_values_and_order": 1,
        "same_request_details": 1,
    }
    changed = html.replace(b'"id": "blind"', b'"id": "other"')
    (directory / p7.FILES[1]).write_bytes(changed)
    hashes[f"{role}/{p7.FILES[1]}"] = p7.digest(changed)
    with pytest.raises(ValueError, match="Handoff"):
        p7.load_packet(tmp_path, admin, role, archive)
    with pytest.raises(ValueError, match="HTML"):
        p7.load_packet(tmp_path, admin, role)
