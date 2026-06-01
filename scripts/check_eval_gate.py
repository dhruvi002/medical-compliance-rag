"""
Assert that the most recent eval report meets the Phase 6 baseline thresholds.

Exits 0 if all thresholds pass, exits 1 with a human-readable message if any fail.

Thresholds are set ~3 points below Phase 6 results to tolerate LLM judge variance.
"""
import glob
import json
import sys
from pathlib import Path

THRESHOLDS = {
    "retrieval.hit_rate@5": 0.70,
    "retrieval.mrr@5": 0.58,
    "generation.faithfulness": 0.78,
    "generation.context_precision": 0.66,
}


def latest_report(reports_dir: str) -> dict:
    pattern = str(Path(reports_dir) / "eval_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"ERROR: no eval_*.json found in {reports_dir}", file=sys.stderr)
        sys.exit(1)
    path = files[-1]
    with open(path) as f:
        data = json.load(f)
    print(f"Checking: {path}")
    return data


def main():
    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    data = latest_report(str(reports_dir))

    failures = []
    for key, threshold in THRESHOLDS.items():
        section, metric = key.split(".", 1)
        section_data = data.get(section, {})

        # Skip generation metrics when generation eval was skipped
        if section == "generation" and "error" in section_data:
            print(f"  SKIP {key}: generation eval not run ({section_data['error']})")
            continue

        value = section_data.get(metric)
        if value is None:
            failures.append(f"  MISSING {key}: metric not found in report")
            continue

        status = "PASS" if value >= threshold else "FAIL"
        print(f"  {status} {key}={value:.4f} (threshold={threshold})")
        if status == "FAIL":
            failures.append(f"  {key}={value:.4f} < threshold {threshold}")

    if failures:
        print("\nEval gate FAILED:")
        for msg in failures:
            print(msg)
        sys.exit(1)

    print("\nEval gate PASSED.")


if __name__ == "__main__":
    main()
