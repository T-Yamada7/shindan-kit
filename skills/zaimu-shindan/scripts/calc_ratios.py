#!/usr/bin/env python3
"""決算書の正規化データから財務指標を計算する（決定論的コア）。

このスクリプトの出力JSON（ratios.json）のみが数値の根拠である。
LLMは財務指標を自分で暗算・推定してはならない。
単体実行例: python calc_ratios.py input.csv -o workspace/ratios.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_input import normalize_csv, ValidationError  # noqa: E402


def _safe_div(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def _pct(numerator, denominator):
    r = _safe_div(numerator, denominator)
    return None if r is None else r * 100


def compute_period_ratios(cur, prev):
    """cur: 当期の正規化済み科目辞書。prev: 前期の辞書（なければNone）。"""
    r = {}

    def add(key, category, value, formula, inputs, prev_value=None):
        yoy = None
        if value is not None and prev_value is not None:
            yoy = round(value - prev_value, 2)
        r[key] = {
            "category": category,
            "value": None if value is None else round(value, 2),
            "formula": formula,
            "inputs": inputs,
            "yoy_change": yoy,
        }

    gross_profit = cur["売上高"] - cur["売上原価"]
    prev_gross_profit = (prev["売上高"] - prev["売上原価"]) if prev else None

    # --- 収益性 ---
    add("売上高総利益率", "収益性", _pct(gross_profit, cur["売上高"]),
        "(売上高-売上原価)/売上高*100",
        {"売上高": cur["売上高"], "売上原価": cur["売上原価"]},
        _pct(prev_gross_profit, prev["売上高"]) if prev else None)

    add("売上高営業利益率", "収益性", _pct(cur["営業利益"], cur["売上高"]),
        "営業利益/売上高*100",
        {"営業利益": cur["営業利益"], "売上高": cur["売上高"]},
        _pct(prev["営業利益"], prev["売上高"]) if prev else None)

    add("売上高経常利益率", "収益性", _pct(cur["経常利益"], cur["売上高"]),
        "経常利益/売上高*100",
        {"経常利益": cur["経常利益"], "売上高": cur["売上高"]},
        _pct(prev["経常利益"], prev["売上高"]) if prev else None)

    add("ROA", "収益性", _pct(cur["当期純利益"], cur["資産合計"]),
        "当期純利益/資産合計(期末)*100",
        {"当期純利益": cur["当期純利益"], "資産合計": cur["資産合計"]},
        _pct(prev["当期純利益"], prev["資産合計"]) if prev else None)

    add("ROE", "収益性", _pct(cur["当期純利益"], cur["純資産合計"]),
        "当期純利益/純資産合計(期末)*100",
        {"当期純利益": cur["当期純利益"], "純資産合計": cur["純資産合計"]},
        _pct(prev["当期純利益"], prev["純資産合計"]) if prev else None)

    # --- 安全性 ---
    add("流動比率", "安全性", _pct(cur["流動資産合計"], cur["流動負債合計"]),
        "流動資産合計/流動負債合計*100",
        {"流動資産合計": cur["流動資産合計"], "流動負債合計": cur["流動負債合計"]},
        _pct(prev["流動資産合計"], prev["流動負債合計"]) if prev else None)

    quick_assets = cur["現金及び預金"] + cur["売上債権"]
    prev_quick_assets = (prev["現金及び預金"] + prev["売上債権"]) if prev else None
    add("当座比率", "安全性", _pct(quick_assets, cur["流動負債合計"]),
        "(現金及び預金+売上債権)/流動負債合計*100",
        {"現金及び預金": cur["現金及び預金"], "売上債権": cur["売上債権"], "流動負債合計": cur["流動負債合計"]},
        _pct(prev_quick_assets, prev["流動負債合計"]) if prev else None)

    add("自己資本比率", "安全性", _pct(cur["純資産合計"], cur["資産合計"]),
        "純資産合計/資産合計*100",
        {"純資産合計": cur["純資産合計"], "資産合計": cur["資産合計"]},
        _pct(prev["純資産合計"], prev["資産合計"]) if prev else None)

    fixed_lt_capital = cur["純資産合計"] + cur["固定負債合計"]
    prev_fixed_lt_capital = (prev["純資産合計"] + prev["固定負債合計"]) if prev else None
    add("固定長期適合率", "安全性", _pct(cur["固定資産合計"], fixed_lt_capital),
        "固定資産合計/(純資産合計+固定負債合計)*100",
        {"固定資産合計": cur["固定資産合計"], "純資産合計": cur["純資産合計"], "固定負債合計": cur["固定負債合計"]},
        _pct(prev["固定資産合計"], prev_fixed_lt_capital) if prev else None)

    add("負債比率", "安全性", _pct(cur["負債合計"], cur["純資産合計"]),
        "負債合計/純資産合計*100",
        {"負債合計": cur["負債合計"], "純資産合計": cur["純資産合計"]},
        _pct(prev["負債合計"], prev["純資産合計"]) if prev else None)

    # --- 効率性（回転率、単位:回） ---
    add("総資産回転率", "効率性", _safe_div(cur["売上高"], cur["資産合計"]),
        "売上高/資産合計",
        {"売上高": cur["売上高"], "資産合計": cur["資産合計"]},
        _safe_div(prev["売上高"], prev["資産合計"]) if prev else None)

    add("売上債権回転率", "効率性", _safe_div(cur["売上高"], cur["売上債権"]),
        "売上高/売上債権",
        {"売上高": cur["売上高"], "売上債権": cur["売上債権"]},
        _safe_div(prev["売上高"], prev["売上債権"]) if prev else None)

    add("棚卸資産回転率", "効率性", _safe_div(cur["売上高"], cur["棚卸資産"]),
        "売上高/棚卸資産",
        {"売上高": cur["売上高"], "棚卸資産": cur["棚卸資産"]},
        _safe_div(prev["売上高"], prev["棚卸資産"]) if prev else None)

    add("有形固定資産回転率", "効率性", _safe_div(cur["売上高"], cur["有形固定資産"]),
        "売上高/有形固定資産",
        {"売上高": cur["売上高"], "有形固定資産": cur["有形固定資産"]},
        _safe_div(prev["売上高"], prev["有形固定資産"]) if prev else None)

    # --- 成長性（前期比較。前期データがなければ算出不可） ---
    if prev is not None:
        add("売上高成長率", "成長性", _pct(cur["売上高"] - prev["売上高"], prev["売上高"]),
            "(当期売上高-前期売上高)/前期売上高*100",
            {"当期売上高": cur["売上高"], "前期売上高": prev["売上高"]})
        add("営業利益成長率", "成長性", _pct(cur["営業利益"] - prev["営業利益"], prev["営業利益"]),
            "(当期営業利益-前期営業利益)/前期営業利益*100",
            {"当期営業利益": cur["営業利益"], "前期営業利益": prev["営業利益"]})
    else:
        for key, formula in [
            ("売上高成長率", "(当期売上高-前期売上高)/前期売上高*100"),
            ("営業利益成長率", "(当期営業利益-前期営業利益)/前期営業利益*100"),
        ]:
            r[key] = {
                "category": "成長性",
                "value": None,
                "formula": formula,
                "inputs": {},
                "yoy_change": None,
                "note": "前期データがないため算出不可",
            }

    return r


def compute_all(periods):
    """periods: {period: 正規化済み科目辞書}。挿入順=時系列の古い順を前提とする。"""
    period_names = list(periods.keys())
    result = {}
    for i, name in enumerate(period_names):
        prev = periods[period_names[i - 1]] if i > 0 else None
        result[name] = compute_period_ratios(periods[name], prev)
    return {
        "periods_order": period_names,
        "ratios": result,
    }


def main():
    parser = argparse.ArgumentParser(description="決算書CSVから財務指標を計算する（決定論的コア）")
    parser.add_argument("input_csv", help="入力CSV（period,item,value形式）")
    parser.add_argument("-o", "--output", default=None, help="ratios.jsonの出力先（省略時は標準出力）")
    args = parser.parse_args()

    try:
        periods = normalize_csv(args.input_csv)
    except ValidationError as e:
        print(f"検証エラー:\n{e}", file=sys.stderr)
        sys.exit(1)

    result = compute_all(periods)
    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"財務指標を {args.output} に出力しました", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
