"""calc_ratios.py の全16指標をゴールデン値と照合するテスト。

ゴールデン値は examples/sample-sme/kessan.csv（架空中小製造業3期分・業績悪化シナリオ）に対して
calc_ratios.py を実行した結果であり、各指標の定義式（skills/zaimu-shindan/references/ratio-definitions.md）
に基づき手計算でも検算済みの値である。
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "zaimu-shindan" / "scripts"
SAMPLE_CSV = REPO_ROOT / "examples" / "sample-sme" / "kessan.csv"

sys.path.insert(0, str(SCRIPTS_DIR))
from calc_ratios import compute_all  # noqa: E402
from validate_input import normalize_csv  # noqa: E402

GOLDEN = {
    "FY2021": {
        "売上高総利益率": 30.0,
        "売上高営業利益率": 10.0,
        "売上高経常利益率": 9.6,
        "ROA": 7.5,
        "ROE": 15.0,
        "流動比率": 183.33,
        "当座比率": 116.67,
        "自己資本比率": 50.0,
        "固定長期適合率": 64.29,
        "負債比率": 100.0,
        "総資産回転率": 1.25,
        "売上債権回転率": 6.25,
        "棚卸資産回転率": 8.33,
        "有形固定資産回転率": 3.33,
        "売上高成長率": None,
        "営業利益成長率": None,
    },
    "FY2022": {
        "売上高総利益率": 29.17,
        "売上高営業利益率": 8.75,
        "売上高経常利益率": 8.12,
        "ROA": 5.03,
        "ROE": 10.26,
        "流動比率": 176.0,
        "当座比率": 108.0,
        "自己資本比率": 48.99,
        "固定長期適合率": 65.2,
        "負債比率": 104.1,
        "総資産回転率": 1.21,
        "売上債権回転率": 5.65,
        "棚卸資産回転率": 7.38,
        "有形固定資産回転率": 3.24,
        "売上高成長率": -4.0,
        "営業利益成長率": -16.0,
    },
    "FY2023": {
        "売上高総利益率": 25.58,
        "売上高営業利益率": 3.49,
        "売上高経常利益率": 2.33,
        "ROA": 0.5,
        "ROE": 1.14,
        "流動比率": 160.71,
        "当座比率": 89.29,
        "自己資本比率": 43.75,
        "固定長期適合率": 67.31,
        "負債比率": 128.57,
        "総資産回転率": 1.07,
        "売上債権回転率": 4.53,
        "棚卸資産回転率": 5.38,
        "有形固定資産回転率": 2.97,
        "売上高成長率": -10.42,
        "営業利益成長率": -64.29,
    },
}


@pytest.fixture(scope="module")
def ratios():
    periods = normalize_csv(SAMPLE_CSV)
    return compute_all(periods)


def test_periods_order(ratios):
    assert ratios["periods_order"] == ["FY2021", "FY2022", "FY2023"]


@pytest.mark.parametrize("period", ["FY2021", "FY2022", "FY2023"])
def test_all_16_indicators_present(ratios, period):
    assert set(ratios["ratios"][period].keys()) == set(GOLDEN["FY2021"].keys())
    assert len(ratios["ratios"][period]) == 16


@pytest.mark.parametrize("period", ["FY2021", "FY2022", "FY2023"])
@pytest.mark.parametrize("indicator", list(GOLDEN["FY2021"].keys()))
def test_golden_value(ratios, period, indicator):
    expected = GOLDEN[period][indicator]
    actual = ratios["ratios"][period][indicator]["value"]
    assert actual == expected, f"{period}/{indicator}: expected {expected}, got {actual}"


def test_first_period_has_no_yoy_growth(ratios):
    fy2021 = ratios["ratios"]["FY2021"]
    assert fy2021["売上高成長率"]["note"] == "前期データがないため算出不可"
    assert fy2021["営業利益成長率"]["note"] == "前期データがないため算出不可"


def test_yoy_change_matches_value_diff(ratios):
    fy2022 = ratios["ratios"]["FY2022"]["売上高営業利益率"]
    fy2021 = ratios["ratios"]["FY2021"]["売上高営業利益率"]
    assert fy2022["yoy_change"] == round(fy2022["value"] - fy2021["value"], 2)


def test_json_roundtrip_is_stable(ratios):
    # ratios.json はサブエージェント・fact-checkerが参照する契約なので、
    # JSON化しても値が壊れないことを確認する。
    dumped = json.loads(json.dumps(ratios, ensure_ascii=False))
    assert dumped == ratios
