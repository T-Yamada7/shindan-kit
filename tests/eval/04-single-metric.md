---
id: 04-single-metric
target_skill: zaimu-shindan
---

## prompt

（examples/sample-sme の決算書を提示した上で）粗利率いくつ？

## pass_criteria

- 単一指標だけのシンプルな質問であっても `scripts/calc_ratios.py` を実行しており、暗算・目算で答えていない
- 売上高総利益率（粗利率）の値を `ratios.json` の `value` フィールドからそのまま引用している（FY2023なら25.58%）
- サブエージェント（zaimu-analyst/fact-checker）の起動は必須ではないが、起動する場合も過剰な長文レポートにならず質問に対して簡潔に答えている
- 3期分のトレンド（30.0%→29.17%→25.58%の悪化）があれば触れられるとなお良い（必須ではない）
