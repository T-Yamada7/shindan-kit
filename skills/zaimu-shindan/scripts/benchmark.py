#!/usr/bin/env python3
"""ratios.json の各指標を中小企業ベンチマークと突合する（決定論的コア）。

ベンチマーク値は references/sme-benchmarks.md に出典・調査年とともに定義する。
このスクリプトはそのファイルに記載された値をこの BENCHMARKS 辞書と同期させて使う。
単体実行例: python benchmark.py workspace/ratios.json -o workspace/benchmark.json
"""
import argparse
import json
import sys
from pathlib import Path

# 指標名 -> (ベンチマーク値, 値が高いほど良いか)
# 出典: references/sme-benchmarks.md を参照。値を更新する場合は両方のファイルを同期させること。
BENCHMARKS = {
    "売上高総利益率": {"value": 24.0, "higher_is_better": True},
    "売上高営業利益率": {"value": 3.5, "higher_is_better": True},
    "売上高経常利益率": {"value": 4.0, "higher_is_better": True},
    "ROA": {"value": 3.0, "higher_is_better": True},
    "ROE": {"value": 8.0, "higher_is_better": True},
    "流動比率": {"value": 150.0, "higher_is_better": True},
    "当座比率": {"value": 100.0, "higher_is_better": True},
    "自己資本比率": {"value": 40.0, "higher_is_better": True},
    "固定長期適合率": {"value": 90.0, "higher_is_better": False},
    "負債比率": {"value": 150.0, "higher_is_better": False},
    "総資産回転率": {"value": 1.0, "higher_is_better": True},
    "売上債権回転率": {"value": 6.0, "higher_is_better": True},
    "棚卸資産回転率": {"value": 8.0, "higher_is_better": True},
    "有形固定資産回転率": {"value": 3.0, "higher_is_better": True},
    "売上高成長率": {"value": 2.0, "higher_is_better": True},
    "営業利益成長率": {"value": 2.0, "higher_is_better": True},
}

BENCHMARK_SOURCE = "MVP暫定値（要検証）。references/sme-benchmarks.md 参照。正式出典は中小企業実態基本調査への差し替えが必要。"


def evaluate(indicator_name, value):
    bench = BENCHMARKS.get(indicator_name)
    if bench is None or value is None:
        return None
    diff = round(value - bench["value"], 2)
    if bench["higher_is_better"]:
        evaluation = "benchmark_or_above" if diff >= 0 else "below_benchmark"
    else:
        evaluation = "benchmark_or_below" if diff <= 0 else "above_benchmark"
    return {
        "benchmark_value": bench["value"],
        "diff": diff,
        "evaluation": evaluation,
    }


def compare(ratios_data, period=None):
    """ratios_data: calc_ratios.py の出力全体。period省略時は最新期を使う。"""
    period_names = ratios_data["periods_order"]
    target_period = period or period_names[-1]
    period_ratios = ratios_data["ratios"][target_period]

    comparison = {}
    for indicator_name, indicator_data in period_ratios.items():
        result = evaluate(indicator_name, indicator_data["value"])
        if result is not None:
            comparison[indicator_name] = result

    return {
        "period": target_period,
        "benchmark_source": BENCHMARK_SOURCE,
        "comparison": comparison,
    }


def main():
    parser = argparse.ArgumentParser(description="ratios.jsonをベンチマークと突合する")
    parser.add_argument("ratios_json", help="calc_ratios.py が出力した ratios.json")
    parser.add_argument("-p", "--period", default=None, help="対象期間（省略時は最新期）")
    parser.add_argument("-o", "--output", default=None, help="出力先（省略時は標準出力）")
    args = parser.parse_args()

    ratios_data = json.loads(Path(args.ratios_json).read_text(encoding="utf-8"))

    try:
        result = compare(ratios_data, args.period)
    except KeyError as e:
        print(f"エラー: 期間 {e} が ratios.json に存在しません", file=sys.stderr)
        sys.exit(1)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"ベンチマーク突合結果を {args.output} に出力しました", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
