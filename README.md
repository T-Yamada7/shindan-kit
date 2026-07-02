# shindan-kit

[![tests](https://github.com/T-Yamada7/shindan-kit/actions/workflows/tests.yml/badge.svg)](https://github.com/T-Yamada7/shindan-kit/actions/workflows/tests.yml)

> LLMは数字を計算しません。解釈するだけです。

中小企業診断士の実務フレーム（財務分析・SWOT/3C・業務フロー分析・AI適用診断）で企業を診断する Claude Code skill パック。決算書とヒアリングメモを入れると、実務フレームに沿った経営診断レポートが出てくる。

**現在のステータス: Phase 1 (MVP) — `zaimu-shindan`（財務診断）skillのみ実装済み。**

## 3つの勝ち筋

1. **数値ハルシネーションゼロ設計**: 財務指標の計算は全てPythonスクリプトで決定論的に実行する。LLMは計算結果JSONのみを根拠に所見を書く。さらにHaikuサブエージェント（`fact-checker`）が最終レポートの全数値を計算JSONと突合する
2. **診断士2次試験フレーム準拠**: 事例I〜IVの構造に合わせた分析の「型」。診断士受験生コミュニティが第2ユーザー層
3. **株価を一切扱わない企業診断**: 既存の投資系OSS（DCF・スクリーニング等）は「いくらで買うか」を答える。本ツールは「そもそも良い会社か（事業の質）」を答える。競合ではなく併用ポジション

## やらないこと

- 株価予測、Valuation、売買推奨 → 既存OSSの領域
- データ取得基盤の自作 → EDINET DB等の既存MCPを上流として使う分析レイヤーに徹する
- 税務申告 → 既存OSSの領域

## インストール

```bash
git clone https://github.com/T-Yamada7/shindan-kit.git
mkdir -p ~/.claude/skills && cp -r shindan-kit/skills/zaimu-shindan ~/.claude/skills/
cp -r shindan-kit/agents/* ~/.claude/agents/   # サブエージェントも使う場合
```

Claude Codeのプロジェクト単位で使いたい場合は、上記の代わりにプロジェクト直下に `.claude/skills/zaimu-shindan` として配置してもよい（`~/.claude/` はユーザー単位でどのプロジェクトでも有効）。marketplace経由のインストールは `.claude-plugin/plugin.json` を参照。

## 使い方（Phase 1: zaimu-shindan）

```
決算書CSV（examples/sample-sme/kessan.csv を参照）を用意し、
Claude Codeに「この決算書を財務分析して」のように依頼する。
```

内部では以下が決定論的に走る:

```bash
python skills/zaimu-shindan/scripts/calc_ratios.py <input.csv> -o workspace/ratios.json
python skills/zaimu-shindan/scripts/benchmark.py workspace/ratios.json -o workspace/benchmark.json
```

収益性・安全性・効率性・成長性の16指標を算出し、`zaimu-analyst`（sonnet）が所見を執筆、`fact-checker`（haiku）が全数値を機械的に突合する。詳細は `skills/zaimu-shindan/SKILL.md` を参照。

## ターゲット3層と「レンズ」アーキテクチャ（ロードマップ）

計算コアは1つ、比較ベンチマークとレポート様式（=レンズ）を切り替えて3層に届ける構想。

| レンズ | 対象ユーザー | 出力 | 状態 |
|---|---|---|---|
| `sme`（中小企業） | 診断士・コンサル・情シス・経営者 | 経営診断報告書 | **Phase 1で実装済み** |
| `investor`（投資家） | 個人投資家 | 銘柄診断カルテ | Phase 2予定 |
| `shukatsu`（就活） | 就活生 | 企業研究シート | Phase 4予定 |

`investor`レンズは実装時、出力に必ず「投資助言ではない」免責を自動挿入し、売買推奨につながる文言（買い/売り/割安/割高）を`fact-checker`が禁止語として検出する設計。

## リポジトリ構成

```
shindan-kit/
├── .github/workflows/      # CI（pytest）
├── skills/zaimu-shindan/   # Phase 1: 財務診断skill
│   ├── SKILL.md
│   ├── scripts/            # calc_ratios.py / validate_input.py / benchmark.py
│   ├── references/         # 指標定義・ベンチマーク（json+md）・入力仕様
│   └── assets/             # 入力テンプレートCSV
├── agents/                 # zaimu-analyst（sonnet）/ fact-checker（haiku）
├── examples/sample-sme/    # 架空中小製造業3期分（業績悪化シナリオ）
└── tests/                  # pytest golden test + eval プロンプト集
```

## リスクと対処

- **士業境界**: 経営診断は独占業務ではないが、「専門家の判断を代替しない」ことを明記する。ポジショニングは「診断士・コンサル・投資家の下書き部隊」
- **投資助言規制への配慮**: `investor`レンズは事実と診断士フレームの整理に徹し、売買判断に踏み込まない
- **ベンチマークデータの出典**: 公的統計のみ使用予定。**現状 `references/sme-benchmarks.json`（唯一の情報源）はMVP用の暫定値であり、正式な公的統計への差し替えが必要**（詳細は `references/sme-benchmarks.md` 参照）
- **勘定科目マッピングの誤り**: 推測禁止・エラー列挙方式で対処（`references/input-format.md`参照）

## 開発時の約束事

- 言語: Python 3.11+、標準ライブラリ優先
- 全スクリプトは単体実行可能（`python scripts/calc_ratios.py input.csv` で動く。LLMなしでも使えるCLIであることが信頼の担保）
- 実行環境はSonnetメイン。機械的な検品・整形はHaikuに落とす

---

## English summary

shindan-kit is a Claude Code skill pack that produces management diagnosis reports using the practical frameworks of Japan's SME management consultant (Chusho Kigyo Shindanshi) qualification — financial ratio analysis, SWOT/3C, workflow analysis, and AI-adoption assessment.

Design principle: **all numeric computation is deterministic Python, never LLM arithmetic.** The LLM only interprets pre-computed JSON output, and a low-cost Haiku sub-agent (`fact-checker`) cross-checks every number in the final report against that JSON. This is a diagnosis tool for business quality, not a stock-valuation tool — it deliberately stays out of price prediction and buy/sell recommendations.

Phase 1 (MVP), implemented in this repository, covers the `zaimu-shindan` (financial diagnosis) skill: 16 profitability/safety/efficiency/growth ratios computed from a 2-3 period financial statement CSV, benchmarked against SME reference values, with findings written by a sub-agent and verified by a fact-checking sub-agent.
