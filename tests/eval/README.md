# zaimu-shindan eval プロンプト集

skill-creator の評価ループ（draft → テストプロンプト実行 → eval-viewerで人間レビュー → 改善 → 再実行）で使うプロンプト集。
Phase 1完了時に description 最適化（skill-creatorの `run_loop.py`）にも使用する。

各ファイルは1つのテストケース。`prompt` がユーザー発話、`pass_criteria` が合否判定の観点。

| ファイル | 狙い |
|---|---|
| `01-full-analysis.md` | 基本ワークフロー全体（validate→calc→benchmark→所見→fact-check）が正しく起動するか |
| `02-implicit-trigger.md` | 「診断」と明言しない質問でもスキルがundertriggerせず起動するか |
| `03-investor-lens.md` | investorレンズ（Phase 2未実装）を要求された時に、実装状況を正直に伝え、smeレンズでの代替や今後の予定を案内できるか |
| `04-single-metric.md` | 単一指標だけの質問でも暗算せずスクリプト経由で答えるか |
