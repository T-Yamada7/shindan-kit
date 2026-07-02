#!/usr/bin/env python3
"""決算書CSVの勘定科目名を正規化し、必須科目の充足を検証する。

勘定科目名のゆらぎ（「売上高」「売上収益」「営業収益」等）を対応表で正規化する。
対応表にない科目名は推測せず、エラーとして列挙してユーザーに確認させる。
単体実行例: python validate_input.py input.csv -o workspace/normalized.json
"""
import argparse
import csv
import json
import sys
from pathlib import Path

# 正規科目名 -> 別名リスト（正式名自体も別名リストに含める）
ACCOUNT_ALIASES = {
    "売上高": ["売上高", "売上収益", "営業収益", "売上高合計"],
    "売上原価": ["売上原価"],
    "販売費及び一般管理費": ["販売費及び一般管理費", "販管費"],
    "営業利益": ["営業利益"],
    "営業外収益": ["営業外収益"],
    "営業外費用": ["営業外費用"],
    "経常利益": ["経常利益"],
    "当期純利益": ["当期純利益", "当期純利益金額", "親会社株主に帰属する当期純利益"],
    "現金及び預金": ["現金及び預金", "現金預金"],
    "売上債権": ["売上債権", "受取手形及び売掛金", "売掛金"],
    "棚卸資産": ["棚卸資産", "商品及び製品", "商品"],
    "流動資産合計": ["流動資産合計", "流動資産"],
    "有形固定資産": ["有形固定資産"],
    "固定資産合計": ["固定資産合計", "固定資産"],
    "資産合計": ["資産合計", "総資産"],
    "流動負債合計": ["流動負債合計", "流動負債"],
    "固定負債合計": ["固定負債合計", "固定負債"],
    "負債合計": ["負債合計", "負債"],
    "純資産合計": ["純資産合計", "純資産", "自己資本"],
}

REQUIRED_ACCOUNTS = list(ACCOUNT_ALIASES.keys())


def _build_alias_lookup():
    lookup = {}
    for canonical, aliases in ACCOUNT_ALIASES.items():
        for alias in aliases:
            lookup[alias] = canonical
    return lookup


ALIAS_LOOKUP = _build_alias_lookup()


class ValidationError(Exception):
    pass


def normalize_csv(path):
    """CSV(period,item,value)を読み込み、{period: {正規科目名: 値}} を返す。

    マッピング不能な科目や必須科目の不足があれば ValidationError を送出する。
    """
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    unmapped = set()
    periods = {}
    for row in rows:
        period = row["period"].strip()
        item = row["item"].strip()
        raw_value = row["value"].strip()
        canonical = ALIAS_LOOKUP.get(item)
        if canonical is None:
            unmapped.add(item)
            continue
        try:
            value = float(raw_value)
        except ValueError:
            raise ValidationError(
                f"期間 {period} の科目「{item}」の値「{raw_value}」が数値ではありません"
            )
        periods.setdefault(period, {})[canonical] = value

    if unmapped:
        raise ValidationError(
            "以下の科目名を正規科目にマッピングできませんでした。"
            "推測はできないため、references/input-format.md の対応表を確認し、"
            "元の科目名を正規科目名（またはその別名）に修正して再実行してください:\n"
            + "\n".join(f"  - {item}" for item in sorted(unmapped))
        )

    missing_report = {}
    for period, accounts in periods.items():
        missing = [a for a in REQUIRED_ACCOUNTS if a not in accounts]
        if missing:
            missing_report[period] = missing

    if missing_report:
        lines = [f"  {period}: " + ", ".join(missing) for period, missing in missing_report.items()]
        raise ValidationError("以下の期間で必須科目が不足しています:\n" + "\n".join(lines))

    return periods


def main():
    parser = argparse.ArgumentParser(description="決算書CSVの勘定科目を正規化・検証する")
    parser.add_argument("input_csv", help="入力CSV（period,item,value形式）")
    parser.add_argument("-o", "--output", help="正規化済みJSONの出力先（省略時は標準出力）")
    args = parser.parse_args()

    try:
        periods = normalize_csv(args.input_csv)
    except ValidationError as e:
        print(f"検証エラー:\n{e}", file=sys.stderr)
        sys.exit(1)

    output_json = json.dumps(periods, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"正規化済みデータを {args.output} に出力しました", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
