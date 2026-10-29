"""Write an explicit milestone coverage report from one compiled snapshot."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from principia_legacy.common import write_json
from principia_legacy.coverage import coverage_report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-home", type=Path, required=True)
    p.add_argument("--release")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    value = coverage_report(args.data_home, args.release)
    write_json(args.output, value)
    print({"counts": value["counts"], "subjects": value["subjects"]})
