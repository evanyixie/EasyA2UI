import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from six_arms import cache_token_cost

    return cache_token_cost


def tokens(hit=2, miss=3, output=7):
    return {
        "prompt_tokens": hit + miss,
        "completion_tokens": output,
        "total_tokens": hit + miss + output,
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": miss,
    }


def test_both_identities_and_unknown_usage(study):
    t = tokens()
    unknown = dict.fromkeys(t)
    v = study.measured([{"tokens": t}, {"tokens": unknown}])
    assert v["metered_requests"] == v["unknown_usage_calls"] == 1
    assert (v["prompt_tokens"], v["total_tokens"]) == (5, 12)
    with pytest.raises(ValueError, match="Cache and prompt"):
        study.measured([{"tokens": {**t, "prompt_cache_hit_tokens": 5}}])
    with pytest.raises(ValueError, match="Inconsistent"):
        study.measured([{"tokens": {**t, "total_tokens": 17}}])
    with pytest.raises(ValueError, match="Partial cache"):
        study.measured([{"tokens": {**unknown, "prompt_cache_hit_tokens": 0}}])
    with pytest.raises(ValueError, match="Invalid token"):
        study.measured([{"tokens": {**t, "prompt_cache_hit_tokens": True}}])


def test_lookup_of_metered_and_unmetered_raw_receipts(study, tmp_path):
    ledger = {}
    for idx, (t, provider) in enumerate([(tokens(), "provider"), ({}, None)]):
        stage = f"stage{idx}"
        origin = tmp_path / "live/case/L4/calls" / stage
        origin.mkdir(parents=True)
        local = f"local{idx}"
        key = hashlib.sha256(local.encode()).hexdigest()
        state, status, attempts = ("completed", 200, 1) if t else ("failed", None, None)
        raw = {
            "stage": stage,
            "physical_attempts": attempts,
            "http_status": status,
            "request_id": provider,
            "usage": {**t, "prompt_tokens_details": {"cached_tokens": 2}}
            if t
            else None,
        }
        body = json.dumps(raw).encode()
        (origin / "call.json").write_bytes(body)
        (origin / "seal.json").write_text(
            json.dumps(
                {
                    "local_request_id": local,
                    "state": state,
                    "receipt_sha256": hashlib.sha256(body).hexdigest(),
                }
            )
        )
        ledger[key] = (
            "L4",
            {
                "phase": stage,
                "state": state,
                "attempts": attempts,
                "http_status": status,
                "provider": hashlib.sha256(provider.encode()).hexdigest()
                if provider
                else None,
                "tokens": t or dict.fromkeys(tokens()),
            },
        )
    assert study.verify_receipts(tmp_path, ledger) == 1
    p = tmp_path / "live/case/L4/calls/stage0/call.json"
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Receipt hash"):
        study.verify_receipts(tmp_path, ledger)


def test_hypothetical_rates_apply_only_to_metered_tokens(study):
    row = {**tokens(), "unknown_usage_calls": 3}
    report = {"all": row, "arms": {"L4": row}}
    r = study.estimate(report, [Decimal("0.1"), Decimal("1.2"), Decimal(2)], "units")
    assert Decimal(r["all"]["known_usage_estimate"]) == Decimal("0.0000178")
    assert r["arms"]["L4"]["unpriced_request_intents"] == 3
    for bad in ("NaN", "-1", "Infinity"):
        with pytest.raises(ValueError, match="nonnegative rates"):
            study.estimate(report, [Decimal(bad)] * 3, "units")


def test_public_table_reconciles_old_totals_and_exposes_no_default_price(study):
    public = json.loads(study.OUTPUT.read_bytes())
    parent = json.loads(study.PARENT.read_bytes())
    study.verify_public(public, parent)
    assert "rates_per_million" not in public
    public["arms"]["L3"]["metered_requests"] -= 1
    with pytest.raises(ValueError, match="coverage"):
        study.verify_public(public, parent)
