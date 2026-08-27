# W1_08 Paper Trading 4週間検証 Runbook

- 対象: W1_08 の本番投入前 Paper Trading 検証
- 実施方式: Day 0 の Pure Mock スモーク後、検証環境（Sandbox E2E）を4週間実施
- 判断方針: 必須証跡の欠測、注文0件、スリッページ標本0件は `PASS` にせず `INCONCLUSIVE`
- 起点: [GitHub Issue #398](https://github.com/ttj-ishida/KabuSys/issues/398)

---

## 1. 目的と完了条件

この Runbook は、W1_08 のシグナル生成、`signal_queue` から注文までのフロー、
Sandbox API 経由の約定、監視・レポートを、同一のコードと設定で継続検証する手順を定義する。

検証期間は、次の両方を満たすまで延長する。

- 開始日から28暦日以上
- JPX の有効な営業日を20日以上記録

Day 0 のダミーシグナル、休場日、必須ジョブまたは証跡が欠けた日は20日に含めない。
4週間経過時点で BUY シグナルが10件未満の場合は `FAIL` ではなく `INCONCLUSIVE` とし、
同じコード・設定のまま10件に達するまで継続する。

判定は次の3種類とする。

| 判定 | 意味 |
|---|---|
| `PASS` | 全必須基準を満たし、必要な証跡が揃っている |
| `FAIL` | ハード基準に違反した。原因修正後、影響範囲に応じて新しい4週間検証を開始する |
| `INCONCLUSIVE` | 期間・件数・標本・証跡が不足しており、合否をまだ判断できない |

> Sandbox E2E は API・注文フローを本番に近い経路で検証するが、実市場の流動性を完全には再現しない。
> `PASS` 後も、本番は Issue #398 の方針どおり少額で開始する。

---

## 2. 根拠と検証対象

| 根拠 | Runbook への反映 |
|---|---|
| Issue #396 | OOS 検証が `completed` であることを開始条件にする |
| Issue #397 | 収益集中リスク評価が `completed` であり、リスクを受容済みであることを開始条件にする |
| Issue #398 | 20営業日、BUY 10件、注文エラー率0%、スリッページ乖離±0.3%を必須基準にする |
| PR #404 / `run_paper_trading_verification.py` | W1_08 の累積件数・注文・スリッページ集計を使用する |
| PR #369 / `paper_verification_report.py` | `Created` / `Sent` / `Filled`、稼働率、送信率、約定率、P95レイテンシを使用する |
| PR #371 | Execution が本番スキーマの `signal_queue` を一次ソースとして読むことを前提にする |
| [C_1WeekPaperChecklist.md](../WebManual/C_1WeekPaperChecklist.md) | 完了済みの Paper Trading 日次確認を4週間向けに拡張する |
| [C_PaperTrading.md](../WebManual/C_PaperTrading.md) | Pure Mock と Sandbox E2E の設定・状態復元・DB分離を使用する |

固定する W1_08 の主要パラメータは次のとおり。

| 分類 | パラメータ | 値 |
|---|---|---:|
| エントリー | `entry_3d_max_abs_return` | `0.08` |
| エントリー | `quality_score_min` | `-0.30` |
| エグジット | `score_drop_atr_gate` | `1.0` |
| ポジション | `max_positions` | `7` |
| ポジション | `max_utilization` | `0.40` |
| ポジション | `max_position_pct` | `0.22` |
| バックテスト想定 | `slippage` | `0.001`（0.1%） |

検証中にシグナル、ポジションサイズ、リスク、注文、Broker、DB スキーマへ影響する変更を入れた場合、
その時点の Run は `FAIL` とし、新しい `RUN_ID` で再開始する。ログ・レポート表示だけの変更は、
取引判断と保存データに影響しないことを確認し、変更前後の Git SHA と理由を incident に記録する。

---

## 3. 証跡の保存単位

検証開始時に `RUN_ID=W1_08_PT_YYYYMMDD` を採番し、次の配下へ保存する。

| 保存先 | 内容 |
|---|---|
| `artifacts/paper_trading_verification/<RUN_ID>/baseline/` | 開始時マニフェスト、設定、ハッシュ、DBベースライン、Day 0 結果 |
| `artifacts/paper_trading_verification/<RUN_ID>/daily/<DATE>/` | 日次レポート、累積レポート、チェック結果 |
| `artifacts/paper_trading_verification/<RUN_ID>/incidents/` | エラー、警告、再起動、手動操作、設定差分 |
| `artifacts/paper_trading_verification/<RUN_ID>/final/` | 最終レポートと Go / No-Go 判断 |

ログは削除・上書きせず、既存の実行単位ログ `logs/<app>_YYYYMMDD_HHMMSS_<PID>.log` を参照する。
証跡の共有前に、kabu ステーション API トークン、パスワード、その他の秘密値がログへ
出力されていないことを確認する。証跡一式は取引・口座情報を含む機密データとして扱う。

---

## 4. Day 0: Pure Mock スモーク

Day 0 は計測期間の前日に実施し、ダミー注文が本番評価へ混入しないようにする。

1. Execution と Monitoring を停止する。
2. 既存の `paper_trading.db` を `baseline/` へバックアップする。
3. `python scripts/setup_db.py --paper-reset` で Paper DB を初期化する。
4. `KABUSYS_ENV=paper_trading`、`KABU_USE_SANDBOX=false`、`PAPER_FILL_MODE=instant` を設定する。
5. [C_PaperTrading.md](../WebManual/C_PaperTrading.md) の手順で当日用ダミー BUY を1件注入する。
6. Execution と Monitoring を起動し、`Created`、`Sent`、`Filled` が同じ注文に記録されることを確認する。
7. 次のレポートを保存する。

```powershell
python -m kabusys.tools.paper_verification_report `
  --from <SMOKE_DATE> --to <SMOKE_DATE> `
  --db data/paper_trading.db --monitoring-db data/monitoring.db
```

Day 0 の合格条件:

- `Created >= 1`、`Sent >= 1`、`Filled >= 1`
- 注文・約定が `paper_trading.db` に保存される
- `trade_logs` に注文イベントとレイテンシが保存される
- 再起動後に Paper の残高・ポジションが復元される
- `ERROR` / `CRITICAL`、重複注文、リコンシリエーション差分がない

スモーク完了後は再び停止し、スモーク結果を保存してから `--paper-reset` を実行する。
一時的な送信時間上書きを解除し、`KABU_USE_SANDBOX=true` へ切り替える。
計測開始日は Day 0 の翌営業日以降とする。

---

## 5. 計測開始時に記録するもの

最初の計測日の前に `run_manifest.md` を作り、次を記録する。パスワード、API トークン、
`.env` 全文は保存しない。

| 項目 | 記録内容 |
|---|---|
| 識別 | `RUN_ID`、担当者、開始承認者、Issue #398 URL |
| 期間 | 開始日、予定終了日、対象 JPX 営業日一覧、タイムゾーン `Asia/Tokyo` |
| レポート境界 | `<REPORT_FROM_UTC_DATE>`、最終レポート実行時刻、UTC/JST の切り替わり |
| ソース | `git rev-parse HEAD`、ブランチ、`git status --short` が空であること |
| 実行環境 | Windows バージョン、Python バージョン、依存パッケージ一覧 |
| モード | `KABUSYS_ENV=paper_trading`、`KABU_USE_SANDBOX=true`、検証用ポート `18081` |
| 時間窓 | Execution 起動 `08:30`、`KABUSYS_SIGNAL_SEND_START=08:50`、`KABUSYS_SIGNAL_SEND_END=09:10`、終了 `15:30` |
| W1_08 | 上表の固定パラメータと `run_strategy_signal.py` のハッシュ |
| リスク・注文 | `risk_config.yaml`、`execution_config.yaml` のハッシュと注文方式 |
| DB | DuckDB、Paper SQLite、Monitoring SQLite の絶対パス、サイズ、ハッシュ |
| 初期状態 | Paper 初期資金、Paper/Sandbox のポジション、注文件数、未約定件数 |
| スケジューラ | `KabuSys_*` のタスク名、トリガー、状態、直近結果 |
| Addon | `ENABLE_YAHOONEWS`、`ENABLE_AI_SENTIMENT`、`ENABLE_TDNET` の値 |
| スリッページ | バックテスト想定 `0.1%` と、実測値の計算式 |
| Day 0 | スモーク実施日、Git SHA、レポートとログの保存先、結果 |

証跡採取例:

```powershell
$RunId = "W1_08_PT_YYYYMMDD"
$Baseline = "artifacts\paper_trading_verification\$RunId\baseline"
New-Item -ItemType Directory -Force -Path $Baseline

git rev-parse HEAD | Set-Content "$Baseline\git_head.txt"
git status --short | Set-Content "$Baseline\git_status.txt"
python --version 2>&1 | Set-Content "$Baseline\python_version.txt"
python -m pip freeze | Set-Content "$Baseline\pip_freeze.txt"

Get-FileHash scripts\run_strategy_signal.py,config\risk_config.yaml,config\execution_config.yaml |
  Export-Csv -NoTypeInformation "$Baseline\config_hashes.csv"

Get-Item data\kabusys.duckdb,data\paper_trading.db,data\monitoring.db |
  Select-Object FullName,Length,LastWriteTimeUtc |
  Export-Csv -NoTypeInformation "$Baseline\db_files.csv"

Get-FileHash data\kabusys.duckdb,data\paper_trading.db,data\monitoring.db |
  Export-Csv -NoTypeInformation "$Baseline\db_hashes.csv"

Get-ScheduledTask -TaskName "KabuSys_*" | Get-ScheduledTaskInfo |
  Export-Csv -NoTypeInformation "$Baseline\scheduled_tasks.csv"

Select-String -Path .env -Pattern '^(KABUSYS_ENV|KABU_USE_SANDBOX|PAPER_TRADING_SQLITE_PATH|PAPER_TRADING_INITIAL_CASH|ENABLE_YAHOONEWS|ENABLE_AI_SENTIMENT|ENABLE_TDNET|KABUSYS_SIGNAL_SEND_START|KABUSYS_SIGNAL_SEND_END|KABUSYS_MARKET_CLOSE)=' |
  ForEach-Object { $_.Line } | Set-Content "$Baseline\env_allowlist.txt"

python -m kabusys.validate_config *> "$Baseline\validate_config.txt"
```

`git_status.txt` に差分がある、設定ハッシュが承認値と異なる、Sandbox 接続を確認できない、
Paper DB が Day 0 の注文を含む場合は開始しない。

---

## 6. 毎営業日の手順

時刻は `scripts/setup_task_scheduler.ps1` と Execution の既定時間を正とする。

### 6.1 前営業日夜: 翌日分の生成

| 時刻 | 確認 | 日次合格条件 | 保存する証跡 |
|---|---|---|---|
| 17:30 | `data_update` | タスク結果0、価格・銘柄データ更新成功 | job run JSON、実行単位ログ |
| 18:30 | `feature_gen` | タスク結果0、特徴量生成成功 | job run JSON、実行単位ログ |
| 20:00 | `strategy_signal` | タスク結果0、W1_08 固定値で生成 | job run JSON、シグナル件数、ログ |
| 21:00 | `portfolio_construction` | タスク結果0、翌営業日の queue 作成 | job run JSON、queue 件数 |
| 21:15 | `night_batch_report` | `READY`、または影響なしと記録した warning のみ | `summary.json`、`report.md`、`warnings.json` |
| 21:30 | オペレーター確認 | 欠落ジョブ、データ鮮度エラー、説明不能な件数差がない | 日次チェック記録 |

シグナル0件は自動的に異常としない。ただし、全ジョブ成功と入力データの鮮度を確認して
`VALID_NO_SIGNAL` と記録し、ダミーシグナルは注入しない。ジョブ失敗やデータ欠落による0件は
`INVALID_DAY` とし、20営業日に算入しない。

### 6.2 当日朝から引け後

| 時刻 | 操作・確認 | 日次合格条件 | 保存する証跡 |
|---|---|---|---|
| 07:45 | PC、時刻同期、空き容量、検証版 kabu ステーション、ポート18081、タスク状態を確認 | タイムゾーンJST、時刻同期正常、必要容量あり、接続可、設定・Git SHAに差分なし | 時刻同期、ディスク、接続結果、タスク一覧 |
| 08:00 | Pre-Market Report | `BLOCKED` でない。例外は承認済み `VALID_NO_SIGNAL` のみ | `artifacts/pre_market/<DATE>/` |
| 08:02 | Signal Queue Report | 件数・銘柄・方向・数量が夜間結果と一致 | `artifacts/signal_queue/<DATE>/` |
| 08:30 | Execution 自動起動 | PID生成、Startup Report生成、起動エラーなし | PID、startup report、ログ |
| 08:35 | Position Reconciliation | 未解消差分0 | reconciliation report |
| 08:50-09:10 | 注文送信窓 | 処理時刻超過による skip、重複注文、技術エラーなし | `Created` / `Sent` / `Filled`、レイテンシ |
| 09:00-15:30 | Monitoring・ザラ場監視 | 意図しない Kill Switch、連続 API エラー、異常滞留なし | `system_status`、risk/trade logs |
| 15:30以降 | Market Close / Performance | レポート生成、未説明 pending 0、状態整合 | market close、daily performance |

引け後のコマンド:

```powershell
python -m kabusys.run_market_close_report --save
python -m kabusys.run_performance_report --type daily --env paper_trading --save

python -m kabusys.tools.paper_verification_report `
  --from <REPORT_FROM_UTC_DATE> --to <TODAY> `
  --db data/paper_trading.db --monitoring-db data/monitoring.db

python scripts/run_paper_trading_verification.py `
  --start-date <START_DATE> --end-date <TODAY> `
  --output-dir artifacts\paper_trading_verification\<RUN_ID>\daily\<TODAY>
```

`run_paper_trading_verification.py` は20日・10件へ到達する前は終了コード1になる。
途中日の終了コード1だけを障害扱いせず、各指標と保存された JSON を確認する。

`paper_verification_report` の `trade_logs` / `system_status` は UTC の ISO8601 時刻で保存され、
`--from` / `--to` は UTC 日付の `YYYY-MM-DD` で指定する。08:50 JST の初回注文を落とさないため、
通常は `<REPORT_FROM_UTC_DATE>` を `<START_DATE>` の前日にする。Day 0 のデータが同じ UTC 範囲へ
入らないよう、スモーク後に Paper DB を必ずリセットする。Monitoring DB の Day 0 poll が範囲に
入る場合は、開始時の `system_status.id` と UTC 時刻を記録し、最終判断で開始前行を除外する。

### 6.3 毎日記録する項目

| 分類 | 項目 |
|---|---|
| 日付 | JPX 営業日か、`VALID` / `VALID_NO_SIGNAL` / `INVALID_DAY`、担当者 |
| バッチ | 各ジョブの開始・終了・結果、Night Batch 判定、warning と承認理由 |
| シグナル | 総数、BUY/SELL数、`entry_3d_max_abs_return=0.08` 適用確認、quality filter の異常有無 |
| Queue | pending 数、実行対象数、リスク却下数と理由 |
| 注文 | Created、Sent、Filled、Partial、Cancelled、Rejected、Error、Failed |
| 対応関係 | 実行対象 queue → Created の追跡率、Created → Sent → Filled の欠落 |
| スリッページ | 標本数、基準価格、約定価格、符号付き実測、平均、最大、想定0.1%との差 |
| 安定性 | uptime、P95 latency、API/注文エラー、Kill Switch、再起動回数 |
| 整合性 | 未約定、position discrepancy、DB 読み取りエラー |
| 手動操作 | 再実行、停止、キャンセル、設定変更、理由、実施者、時刻 |
| 証跡 | 各 artifact、JSON、実行単位ログ、incident への相対パス |

スリッページは BUY について次で計算する。

```text
signed_slippage = (avg_fill_price - reference_price) / reference_price
deviation_from_assumption = signed_slippage - 0.001
```

`run_paper_trading_verification.py` は絶対スリッページを計算するため、日次記録では符号付き値も残す。
最終の想定差判定は `abs(deviation_from_assumption) <= 0.003` とする。

---

## 7. 週次レビュー

各週末に累積レポートを実行し、次を確認する。

- 有効営業日数、BUY シグナル数、注文数、スリッページ標本数が増えている
- queue、Created、Sent、Filled の対応に欠落がない
- uptime、送信率、約定率、P95 レイテンシが基準から悪化していない
- warning、再起動、手動操作が恒常化していない
- コード・設定・依存関係のハッシュが開始時と一致する
- `INVALID_DAY` と追加すべき延長日数が確定している

20日・10件へ到達する前の W1 verifier 終了コード1は想定内であり、週次障害には数えない。
各指標の内訳と JSON の生成有無で判断する。

週次レビューでハード基準違反が判明した場合、4週目まで待たずに Run を `FAIL` とする。

---

## 8. 最終 Pass / Fail 基準

全項目が必須である。`N/A`、標本0件、必要な artifact 不在は `PASS` ではなく `INCONCLUSIVE` とする。

| 項目 | `PASS` 基準 | 未達時 |
|---|---|---|
| 暦期間 | 28日以上 | `INCONCLUSIVE`、継続 |
| 有効営業日 | 20日以上 | `INCONCLUSIVE`、継続 |
| W1 verifier の取引日数 | 20日以上 | `INCONCLUSIVE`、継続 |
| BUY シグナル | 実シグナル10件以上 | `INCONCLUSIVE`、継続 |
| 注文データ | Created、総注文、スリッページ標本が各1件以上 | 0件/N/A は `INCONCLUSIVE` |
| Queue追跡 | 実行対象 queue → Created が100%追跡可能 | 欠落は `FAIL` |
| 注文エラー率 | `rejected` / `error` / `failed` が0件、エラー率0% | 1件でも `FAIL` |
| スリッページ | W1 JSON の `slippage_max_pct` が0.3%以下 | 超過は `FAIL` |
| 想定との差 | 符号付き実測と想定0.1%の差が±0.3 percentage point以内（絶対値 `<= 0.003`） | 超過は `FAIL` |
| 稼働率 | Generic report の `system_status.uptime_pct` が99%以上、標本あり | 未達は `FAIL`、N/A は `INCONCLUSIVE` |
| 送信率 | Generic report の `Sent / Created` が95%以上、Createdあり | 未達は `FAIL`、N/A は `INCONCLUSIVE` |
| 約定率 | Generic report の `Filled / Created` が90%以上、Createdあり | 未達は `FAIL`、N/A は `INCONCLUSIVE` |
| P95レイテンシ | Generic report の `trade_logs.latency_ms` P95が200ms以下、標本あり | 未達は `FAIL`、N/A は `INCONCLUSIVE` |
| Reconciliation | 最終未解消差分0、全差分に説明あり | 未解消は `FAIL` |
| ジョブ・証跡 | 算入した全営業日で必須ジョブ・日次証跡が揃う | 欠測日は無効、継続 |
| 変更管理 | 取引判断へ影響するコード・設定変更0件 | 変更時点で `FAIL`、再開始 |

リスクルールによる意図した却下は技術エラーと分け、`risk_logs` の理由と queue との対応を記録する。
Broker またはシステムが返した `rejected` / `error` / `failed` は技術エラーとして数える。
W1 固有のシグナル件数と自動スリッページは BUY を対象とするが、技術エラー率、送信率、約定率、
リコンシリエーションは BUY / SELL を含む全実行対象注文で判定する。

休場日、特別気配、上場廃止などが期間中に発生した場合は、対象銘柄、システム判断、注文有無、
ログを記録し、クラッシュ・重複・不正注文がないことを確認する。自然発生しなかった項目は
`NOT_OBSERVED` とし、既存の自動テストまたは別スモークの証跡を最終判断に添付する。

---

## 9. 現行レポートの厳格判定上の注意

現行の自動レポートだけで最終 `PASS` を決めない。次の差を Runbook の手動判定で補う。

| 現行動作 | この Runbook の扱い |
|---|---|
| W1 verifier は注文0件のエラー率を0%とする | 注文0件は `INCONCLUSIVE` |
| W1 verifier はスリッページ `N/A` を PASS とする | 標本0件は `INCONCLUSIVE` |
| W1 verifier の取引日数は `signals` に行がある日だけ数える | JPX 営業日台帳も別に管理し、両方20日以上を要求する |
| W1 verifier は `signal_queue.price > 0` の BUY だけを集計する | 成行など対象外注文を日次台帳で補完する |
| Generic report は P95 が `N/A` でも単独では失敗にしない | P95 `N/A` は `INCONCLUSIVE` |

---

## 10. 障害・中断時の扱い

異常時はデータを削除・修正して帳尻を合わせない。

1. `python scripts/stop_system.py` で安全停止する。
2. 実行単位ログ、対象 artifact、DB のバックアップを保存する。
3. incident に発生時刻、影響注文、原因、手動操作、復旧確認を記録する。
4. [FailureRecovery.md](./FailureRecovery.md) に従いリコンシリエーションする。
5. ハード基準違反または取引判断へ影響する修正なら現在の Run を `FAIL` とする。
6. 単なる証跡欠測なら対象日を `INVALID_DAY` とし、同一設定で営業日を追加する。

---

## 11. 最終判断

最終日に2つの累積レポートを実行し、出力と JSON を `final/` に保存する。

```powershell
python -m kabusys.tools.paper_verification_report `
  --from <REPORT_FROM_UTC_DATE> --to <END_DATE> `
  --db data/paper_trading.db --monitoring-db data/monitoring.db

python scripts/run_paper_trading_verification.py `
  --start-date <START_DATE> --end-date <END_DATE> `
  --output-dir artifacts\paper_trading_verification\<RUN_ID>\final
```

`final_decision.md` に次を残す。

- `RUN_ID`、開始・終了日、Git SHA、最終設定ハッシュ
- 20営業日の一覧と除外日・理由
- 全 Pass / Fail 基準の実測値、標本数、証跡パス
- incident 一覧と影響評価
- `PASS` / `FAIL` / `INCONCLUSIVE` の判断と承認者
- `PASS` の場合は本番少額開始の上限、監視期間、即時停止条件

Issue #398 は、最終判断と証跡へのリンクをコメントした後にのみ close する。
