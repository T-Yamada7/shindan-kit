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
import unicodedata
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

# 損益整合性チェックの許容誤差（丸め誤差を吸収するための最小限の許容幅）
_CONSISTENCY_ABS_TOLERANCE = 1.0
_CONSISTENCY_REL_TOLERANCE = 0.0005


class ValidationError(Exception):
    pass


def _parse_value(raw_value):
    """全角数字・カンマ区切りを許容して数値に変換する。変換できなければ None を返す。"""
    normalized = unicodedata.normalize("NFKC", raw_value).replace(",", "").strip()
    try:
        return float(normalized)
    except ValueError:
        return None


def _within_tolerance(actual, expected):
    tolerance = max(_CONSISTENCY_ABS_TOLERANCE, abs(expected) * _CONSISTENCY_REL_TOLERANCE)
    return abs(actual - expected) <= tolerance


def _check_pl_consistency(periods):
    """販管費・営業外収益・営業外費用を用いて営業利益・経常利益の入力値の整合性を検証する。

    これらの科目は他の指標計算には使われないため、入力データの検算にのみ使う。
    不整合は推測で無視せず、必須科目不足と同様にエラーとして列挙する。
    """
    issues = []
    for period, acc in sorted(periods.items()):
        gross_profit = acc["売上高"] - acc["売上原価"]
        expected_operating = gross_profit - acc["販売費及び一般管理費"]
        if not _within_tolerance(acc["営業利益"], expected_operating):
            issues.append(
                f"  {period}: 営業利益の入力値({acc['営業利益']:g})が"
                f"(売上高-売上原価-販管費)の計算値({expected_operating:g})と一致しません"
            )

        expected_ordinary = acc["営業利益"] + acc["営業外収益"] - acc["営業外費用"]
        if not _within_tolerance(acc["経常利益"], expected_ordinary):
            issues.append(
                f"  {period}: 経常利益の入力値({acc['経常利益']:g})が"
                f"(営業利益+営業外収益-営業外費用)の計算値({expected_ordinary:g})と一致しません"
            )
    return issues


def normalize_csv(path):
    """CSV(period,item,value)を読み込み、{period: {正規科目名: 値}} を返す。

    マッピング不能な科目、必須科目の不足、同一科目への重複マッピング、
    損益項目間の整合性エラーがあれば ValidationError を送出する。
    """
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    unmapped = set()
    periods = {}
    duplicate_sources = {}  # (period, canonical) -> [item, ...]（衝突検出用）
    for row in rows:
        period = row["period"].strip()
        item = row["item"].strip()
        raw_value = row["value"].strip()
        canonical = ALIAS_LOOKUP.get(item)
        if canonical is None:
            unmapped.add(item)
            continue
        value = _parse_value(raw_value)
        if value is None:
            raise ValidationError(
                f"期間 {period} の科目「{item}」の値「{raw_value}」が数値ではありません"
            )

        key = (period, canonical)
        duplicate_sources.setdefault(key, []).append(item)
        periods.setdefault(period, {})[canonical] = value

    if unmapped:
        raise ValidationError(
            "以下の科目名を正規科目にマッピングできませんでした。"
            "推測はできないため、references/input-format.md の対応表を確認し、"
            "元の科目名を正規科目名（またはその別名）に修正して再実行してください:\n"
            + "\n".join(f"  - {item}" for item in sorted(unmapped))
        )

    duplicates = {k: v for k, v in duplicate_sources.items() if len(v) > 1}
    if duplicates:
        lines = [
            f"  {period}: 「{canonical}」に複数の科目行がマッピングされています ({', '.join(items)})"
            for (period, canonical), items in sorted(duplicates.items())
        ]
        raise ValidationError(
            "同一期間・同一正規科目に複数の入力行が対応しています。"
            "どちらが正しいかを推測できないため、重複行を削除・統合してから再実行してください:\n"
            + "\n".join(lines)
        )

    missing_report = {}
    for period, accounts in periods.items():
        missing = [a for a in REQUIRED_ACCOUNTS if a not in accounts]
        if missing:
            missing_report[period] = missing

    if missing_report:
        lines = [f"  {period}: " + ", ".join(missing) for period, missing in missing_report.items()]
        raise ValidationError("以下の期間で必須科目が不足しています:\n" + "\n".join(lines))

    consistency_issues = _check_pl_consistency(periods)
    if consistency_issues:
        raise ValidationError(
            "損益項目間の整合性が取れていません。入力ミスの可能性があるため確認してください:\n"
            + "\n".join(consistency_issues)
        )

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
