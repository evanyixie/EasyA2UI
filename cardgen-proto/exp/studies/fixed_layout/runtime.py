"""连接随仓 Easy 验证器以及显式配置的研究测量、数据模型和分配器。"""

import os
import sys
from importlib import import_module
from pathlib import Path

from evidence import sha

HARNESS = Path(__file__).resolve().parent.parent / "six_arms" / "harness_v2"
sys.path.insert(0, str(HARNESS))
program = import_module("program_stages")
trial = import_module("trial")

measurement = program.measurement_files()
reference = measurement["measure.py"].resolve().parent
data_model = program._module("fixed_data_model", reference / "data_model.py")
allocation = program._module("fixed_allocation", reference / "space_allocation.py")
signature, validate = trial.signature, trial.VALIDATE
model = os.environ.get("FIXED_LAYOUT_MODEL") or trial.MODEL
api = os.environ.get("FIXED_LAYOUT_API") or trial.API


def dependencies():
    files = {
        **measurement,
        "space_allocation.py": reference / "space_allocation.py",
        "data_model.py": reference / "data_model.py",
        "six_arms/program_stages.py": Path(program.__file__),
        "six_arms/trial.py": Path(trial.__file__),
        "Easy/validate.py": trial.UPSTREAM / "src/validate.py",
        "Easy/conditions.py": trial.UPSTREAM / "exp/conditions.py",
    }
    return {k: sha(p) for k, p in files.items()}
