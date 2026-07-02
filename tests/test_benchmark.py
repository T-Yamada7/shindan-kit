"""benchmark.py と、ベンチマーク値の唯一の情報源(sme-benchmarks.json)の整合性テスト。"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "zaimu-shindan" / "scripts"
REFERENCES_DIR = REPO_ROOT / "skills" / "zaimu-shindan" / "references"
SAMPLE_CSV = REPO_ROOT / "examples" / "sample-sme" / "kessan.csv"

sys.path.insert(0, str(SCRIPTS_DIR))
from benchmark import BENCHMARKS, compare  # noqa: E402
from calc_ratios import compute_all  # noqa: E402
from validate_input import normalize_csv  # noqa: E402

_MD_ROW = re.compile(r"^\|\s*([^\|]+?)\s*\|\s*([\d.]+)\s*\|\s*(%|回)\s*\|\s*(高い方が良い|低い方が良い)\s*\|$")


def _parse_md_table():
    """sme-benchmarks.md の表を解析し、{指標名: (値, higher_is_better)} を返す。"""
    text = (REFERENCES_DIR / "sme-benchmarks.md").read_text(encoding="utf-8")
    parsed = {}
    for line in text.splitlines():
        m = _MD_ROW.match(line.strip())
        if m:
            name, value, _unit, direction = m.groups()
            parsed[name] = (float(value), direction == "高い方が良い")
    return parsed


def test_json_is_readable_and_has_16_indicators():
    data = json.loads((REFERENCES_DIR / "sme-benchmarks.json").read_text(encoding="utf-8"))
    assert len(data["benchmarks"]) == 16
    assert "source_status" in data


def test_md_table_matches_json_single_source():
    md_values = _parse_md_table()
    assert set(md_values.keys()) == set(BENCHMARKS.keys()), (
        "sme-benchmarks.md の表と sme-benchmarks.json の指標名が一致しません。"
        "値を変更した際は両方を同期してください。"
    )
    for name, (value, higher_is_better) in md_values.items():
        assert value == BENCHMARKS[name]["value"], f"{name}: md={value}, json={BENCHMARKS[name]['value']}"
        assert higher_is_better == BENCHMARKS[name]["higher_is_better"], f"{name}: 方向が不一致"


def test_compare_uses_latest_period_by_default():
    periods = normalize_csv(SAMPLE_CSV)
    ratios = compute_all(periods)
    result = compare(ratios)
    assert result["period"] == "FY2023"
    assert result["comparison"]["自己資本比率"]["evaluation"] == "benchmark_or_above"
    assert result["comparison"]["ROA"]["evaluation"] == "below_benchmark"


def test_compare_unknown_period_raises_keyerror():
    periods = normalize_csv(SAMPLE_CSV)
    ratios = compute_all(periods)
    with pytest.raises(KeyError):
        compare(ratios, period="FY1999")
