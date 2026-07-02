---
id: 01-full-analysis
target_skill: zaimu-shindan
---

## prompt

examples/sample-sme の決算書を財務分析して

## pass_criteria

- `scripts/validate_input.py` または `scripts/calc_ratios.py` を実際に実行している（暗算していない）
- `workspace/ratios.json` が生成され、レポート中の数値がすべてそこから引用されている
- `scripts/benchmark.py` によるベンチマーク突合が行われ、暫定値である旨の断り書きがある
- `zaimu-analyst` サブエージェントに執筆を委譲し、メインスレッドはファイルパス＋要約のみ受け取っている（メインのコンテキストに長文所見が漏れていない）
- `fact-checker` サブエージェントによる突合が行われている（またはその実行ログが確認できる）
- 収益性・安全性・効率性・成長性の4カテゴリすべてに触れている
- 3期を通じた業績悪化トレンド（売上減・利益率悪化・自己資本比率低下）に言及している
