---
name: zaimu-shindan
description: 財務諸表・決算書・試算表から経営診断を行うスキル。「財務分析して」「この会社の経営状態は」「決算書を見て」「銘柄を診断して」「粗利率は」「借入できそう？」「診断士っぽく分析して」など、企業の財務データの分析・診断・評価に関する依頼では、明示的に「診断」と言われなくても必ずこのスキルを使うこと。数値をLLMが暗算・推定することは禁止し、必ず本スキルのPythonスクリプトを実行して得たJSONのみを根拠に所見を書く。
---

# zaimu-shindan（財務診断）

中小企業診断士の実務フレーム（収益性・安全性・効率性・成長性）に沿って、決算書CSVから財務指標を算出し、経営診断の所見を作成するスキル。

**最重要原則**: 財務指標を自分で暗算・推定してはならない。必ず `scripts/calc_ratios.py` を実行し、その出力JSON（`ratios.json`）のみを数値の根拠とすること。単純な質問（「粗利率いくつ？」等）であってもスクリプトを経由せずに答えてはならない。

## いつ使うか

以下のような依頼が来たら、ユーザーが「診断」と明言していなくても本スキルを起動する:
- 決算書・財務諸表・試算表のCSV/データを渡されて分析を求められたとき
- 「この会社は儲かっているか」「借入は可能か」「経営状態は健全か」等の財務系の質問
- 個別指標だけを聞かれたとき（「ROEは？」「流動比率は？」等）でも、算出にはスクリプトを使う
- 上場銘柄のティッカー・企業名を挙げて「診断して」と言われたとき（investorレンズ、Phase 2以降）

## ワークフロー（sme レンズ / v0.1）

1. **入力確認**: ユーザーから決算書CSVを受け取る。形式不明な場合は `references/input-format.md` と `assets/input-template.csv` を提示する
2. **検証・正規化**: `python scripts/validate_input.py <input.csv> -o workspace/normalized.json` を実行
   - 勘定科目のマッピング不能エラーや必須科目不足エラーが出たら、**推測で埋めずに**ユーザーに確認する
3. **指標計算**: `python scripts/calc_ratios.py <input.csv> -o workspace/ratios.json` を実行
   - 内部で正規化も行うため、手順2を経なくても直接実行可能。ただし事前にエラーの有無を確認したい場合は手順2を先に単独実行してよい
4. **ベンチマーク突合**: `python scripts/benchmark.py workspace/ratios.json -o workspace/benchmark.json` を実行
   - 出力の `benchmark_source` が暫定値であることを示している点に注意（`references/sme-benchmarks.md` 参照）
5. **所見執筆**: `zaimu-analyst` サブエージェントを起動し、`workspace/ratios.json` と `workspace/benchmark.json` を読ませて `workspace/zaimu_findings.md` に所見を書かせる。メインスレッドには「ファイルパス＋3行要約」のみ返させる
6. **ファクトチェック**: `fact-checker` サブエージェントを起動し、`workspace/zaimu_findings.md` 中の全数値を `workspace/ratios.json` と突合させる
   - 不一致があれば `zaimu-analyst` に差し戻す（最大2回）。それでも解消しなければユーザーにエスカレーションする
7. **提示**: 検証済みの `workspace/zaimu_findings.md` の内容をユーザーに提示する

単純な単一指標の質問（例:「粗利率いくつ？」）でも、手順3（`calc_ratios.py`）は必ず実行し、その出力から値を引用する。手順5〜6のサブエージェント起動は省略してよい。

## 参照ファイル（progressive disclosure）

必要になったタイミングで読むこと。最初から全部読み込む必要はない。

- `references/input-format.md`: CSV形式・勘定科目マッピング対応表の詳細。ユーザーの入力形式が不明・エラーが出た時に参照
- `references/ratio-definitions.md`: 全16指標の定義式・診断士フレームでの位置づけ・解釈の目安。所見執筆時に参照
- `references/sme-benchmarks.md`: ベンチマーク値の出典状況と表。ベンチマーク突合結果を解釈する時に参照
- `assets/input-template.csv`: ユーザーに提示する入力テンプレート

## スクリプト一覧

| スクリプト | 役割 | 単体実行例 |
|---|---|---|
| `scripts/validate_input.py` | 勘定科目名の正規化・検証 | `python scripts/validate_input.py input.csv -o workspace/normalized.json` |
| `scripts/calc_ratios.py` | 16指標の計算（決定論的コア） | `python scripts/calc_ratios.py input.csv -o workspace/ratios.json` |
| `scripts/benchmark.py` | ベンチマークとの突合 | `python scripts/benchmark.py workspace/ratios.json -o workspace/benchmark.json` |

いずれも標準ライブラリのみで動作し、LLMなしでも単体実行できる（信頼性の担保）。

## サブエージェント

- `agents/zaimu-analyst.md`（model: sonnet）: `ratios.json`／`benchmark.json` から所見執筆
- `agents/fact-checker.md`（model: haiku）: 所見中の全数値の突合検証・禁止語検出

エージェントの起動条件・入出力契約は各エージェント定義ファイルを参照。

## スコープ外（v0.1時点）

- investor / shukatsu レンズ（Phase 2以降）
- SWOT/3C・業務フロー・AI適用診断（`kankyo-bunseki` 等、Phase 3）
- docx組版（`shindan-report`、Phase 2）
- PDF入力の直接サポート（実験的機能として将来対応予定）

## やってはいけないこと

- 財務指標をLLMが暗算・推定して答えること
- 勘定科目のマッピングを推測で埋めること（`validate_input.py` のエラーはユーザーに確認する）
- ベンチマーク値を公的統計からの正式引用であるかのように断定すること（現状は暫定値。`references/sme-benchmarks.md` 参照）
- 投資助言・売買推奨につながる断定（investorレンズ実装時の話。v0.1のsmeレンズでは該当なし）
