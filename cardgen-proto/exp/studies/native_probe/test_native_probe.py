"""对照实拍时实际发送的四份合成输入。"""

import hashlib
from pathlib import Path

from make_probes import write_probes


def test_capture_input_bytes(tmp_path: Path) -> None:
    output = tmp_path / "inputs"
    write_probes(output)
    digests = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.jsonl")}
    assert digests == {
        "compound_top": "a233b7137c5fdc6e8c1cda24a8a5840ba2f28c710de6b147f3f54159a838c3fd",
        "object_top": "706c2d33dfbc589304b0c0a8dea2cd22bf523c7e157861864e4ad4bb220f154d",
        "template_start": "ee5288e24c74a6a5d2a5feb97299e82bd6841f820e4d668715f40839d4b9ee3f",
        "template_top": "4a001e9269c89c7392d1a99abde9cd493afe994cbcceca477d0ca12c0fd66492",
    }
