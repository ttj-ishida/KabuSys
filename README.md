# KabuSys — README (日本語)

このリポジトリは、日本株向けの自動売買運用ツール群（KabuSys）の一部です。  
ここに含まれるスクリプトは、監視・実行・レポート生成など運用に必要なコマンドラインエントリポイントを提供します。

以下は、このコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は自動売買システムの運用周り（Execution、Monitoring、各種レポート生成、設定ウィザード、検証ツールなど）を含むモジュール群です。  
主に以下の役割を持つコンポーネントがあります。

- 実際の発注ループ（ExecutionEngine）
- システム状態・リソース監視（SystemMonitor）
- 各種運用レポート（Pre-Market、Market Close、Performance、Signal Queue、Position Reconciliation 等）
- 設定のウィザードおよび検証ツール（.env 作成・検証）
- ペーパートレード用の検証スクリプト

設定は環境変数（.env）で行い、DuckDB / SQLite をデータ参照先として使用します。

---

## 主な機能一覧

- 実行エンジン起動: `python -m kabusys.run_execution`
  - KABUSYS_ENV によって本番 / paper_trading を切り替え
  - Paper Trading の場合、専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し Mock Broker を利用
  - 起動時にリコンシリエーションを実施し Execution Startup Summary を生成・保存可能
  - PID ファイル: `data/execution.pid`
  - 停止フラグ: `data/stop_requested.flag` を検知して安全停止

- 監視プロセス起動: `python -m kabusys.run_monitoring`
  - SystemMonitor のポーリングループを実行（デフォルト 60 秒）
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔を上書き可能
  - Monitoring は環境にかかわらず本番の `sqlite_path` を使用
  - PID ファイル: `data/monitoring.pid`
  - 停止フラグ: `data/stop_requested.flag` を検知して安全停止

- ザラ場監視 CLI: `python -m kabusys.run_intraday_monitor`
  - 単発または監視モード（`--watch`）で実行状態 / リスク / システム指標を表示

- Streamlit 監視ダッシュボード: `streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db`
  - 10ページ構成（Home / Initial Setup / Pre-Market / Execution Startup / Intraday Monitor / Signal Queue / Performance / Failure Recovery / WebManual / Strategy Lab）
  - Home: Kill Switch・Execution / Monitoring プロセス状態・エラーログ（SQLite）
  - Initial Setup / Pre-Market / Execution Startup / Intraday Monitor / Failure Recovery: 運用フロー確認ページ（SQLite `monitoring.db`、`operations_data.py` 経由）
  - Performance > Paper Verification タブ: SQLite `paper_trading.db`（read-only）
  - Signal Queue / Performance（Paper Verification 以外）/ Strategy Lab: DuckDB（`kabusys.duckdb`）を読み取り専用で参照

- 各種レポート生成:
  - Pre-Market Report: `python -m kabusys.run_pre_market_report`（--save / --json）
  - Market Close Summary: `python -m kabusys.run_market_close_report`（--date / --save / --json）
  - Position Reconciliation Report: `python -m kabusys.run_position_reconciliation_report`（--date / --save / --json / --watch）
  - Signal Queue Confirmation View: `python -m kabusys.run_signal_queue_report`（--date / --save / --json）
  - Performance Report（daily/weekly/monthly）: `python -m kabusys.run_performance_report --type daily`（--env / --from / --to / --save）
  - Execution Startup Summary の生成は Execution 起動時にも実行される

- 設定周り:
  - 対話式 .env 作成: `python -m kabusys.config_setup`
  - 設定検証ツール: `python -m kabusys.validate_config`（`--strict` で警告を FAIL 扱い）

- ペーパートレード検証ツール:
  - `python -m kabusys.tools.paper_verification_report`（期間指定可）  
    - paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）に対して稼働率・注文成功率・レイテンシ等の検証を実行

---

## 必須環境変数（代表）

主要な必須/重要な環境変数例（.env に設定）:

- JQUANTS_REFRESH_TOKEN（必須）
- JQUANTS_BULK_API_KEY（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（`development` / `paper_trading` / `live`、デフォルト `development`）
- DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH（paper_trading の場合の専用 DB、デフォルト `data/paper_trading.db`）
- LOG_LEVEL（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意; アラート用）
- ENABLE_AI_SENTIMENT（`true` で AI ニュースセンチメント分析を有効化; デフォルト `false`）
- OPENAI_API_KEY（ENABLE_AI_SENTIMENT=true 時に必須）
- ENABLE_TDNET（`true` で TDnet 適時開示収集を有効化; デフォルト `false`）
- ENABLE_EDINET（`true` で EDINET 法定開示収集を有効化; デフォルト `false`）
- EDINET_API_KEY（ENABLE_EDINET=true 時に必須; EDINET API サブスクリプションキー）
- ENABLE_YAHOONEWS（`true` で Yahoo News RSS 収集を有効化; デフォルト `false`）

その他:
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒; デフォルト 60）
- PAPER_FILL_MODE（paper_trading の fill 動作: `instant`/`partial`/`never`/`reject`）
- PAPER_TRADING_INITIAL_CASH（MockBrokerClient の初期仮想資金（円）; デフォルト `10000000`）
- KABU_USE_SANDBOX（`true` でポート 18081 のkabu検証環境に接続; `paper_trading` 時のみ有効; デフォルト `false`）
- KABU_SANDBOX_API_PASSWORD（kabu検証環境用 API パスワード; 未設定時は `KABU_API_PASSWORD` を使用）

設定作成は `python -m kabusys.config_setup` を推奨し、作成後に `python -m kabusys.validate_config` で検証してください。

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. 仮想環境を作成してアクティベート

   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール

   ```
   pip install -r requirements.txt
   ```

4. 環境変数の設定（.env ウィザード）

   対話形式で `.env` を作成します:

   ```
   python -m kabusys.config_setup
   ```

   必須項目: `JQUANTS_REFRESH_TOKEN`, `JQUANTS_BULK_API_KEY`, `KABU_API_PASSWORD`

5. 設定の検証

   ```
   python -m kabusys.validate_config
   ```

   エラーや警告が出た場合は `.env` および `config/*.yaml` を修正してください。  
   `config/risk_config.yaml` が存在することも確認してください（サンプルは `config/` 以下を参照）。

6. DB の初期化（DuckDB + SQLite）

   DuckDB（分析用）と SQLite（監視用）のスキーマを作成します:

   ```
   python scripts/setup_db.py
   ```

   ペーパートレード用 DB（`data/paper_trading.db`）も同時に初期化する場合:

   ```
   python scripts/setup_db.py --paper
   ```

   パスは `.env` の `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` で変更できます。

7. J-Quants Bootstrap（初期データ一括取得）

   J-Quants Bulk Download API から過去の株価・財務・銘柄マスタ・カレンダーを DuckDB に投入します:

   ```
   # まずドライランで取得件数を確認
   python -m kabusys.data.bootstrap --dry-run

   # 全エンドポイントを一括取得（初回は数分〜数十分かかります）
   python -m kabusys.data.bootstrap

   # 特定エンドポイントのみ取得する場合
   python -m kabusys.data.bootstrap --endpoint /equities/bars/daily
   ```

   取得対象エンドポイント: `prices_daily`, `master`, `financials`, `market_calendar`, `dividend`, `topix`

8. 夜間バッチの初回手動実行（データ確認）

   Bootstrap 後、特徴量生成・レジーム判定などを一度手動実行してデータが正しく処理されるか確認します:

   ```
   python scripts/run_feature_gen.py
   python scripts/run_ai_analysis.py
   python scripts/run_strategy_signal.py
   python scripts/run_portfolio_construction.py
   ```

9. システム起動確認（ペーパートレード）

   本番前にペーパートレードモードで Execution と Monitoring を起動します:

   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   # 別ターミナル
   python -m kabusys.run_monitoring
   ```

10. Windows タスクスケジューラへの登録（本番運用時）

    夜間バッチの自動実行を設定します:

    ```
    powershell -ExecutionPolicy Bypass -File scripts/setup_task_scheduler.ps1
    ```

注意:
- `KABUSYS_ENV=live` に変更するのはペーパートレードで十分な検証が済んだ後にしてください。
- `.env` にトークンやパスワードを保存する場合は絶対に Git にコミットしないでください。

---

## 使い方（主要スクリプト）

各スクリプトは Python モジュールとして直接実行できます（プロジェクトルートで実行を推奨）。

> `config_setup`（.env ウィザード）と `validate_config`（設定検証）は初回セットアップ専用です。セットアップ手順のステップ 4・5 を参照してください。

---

### 1 日の運用フロー

KabuSys は**日足スイング戦略**専用の設計です。夜間バッチでシグナルを生成し、翌営業日の寄付きで執行します。ザラ場中はシグナル生成を行いません。

```
15:30  市場クローズ
  ↓
夜間バッチ（15:30〜21:00）
  ├─ 15:30  データ更新   scripts/run_data_update.py
  ├─ 16:00  特徴量生成   scripts/run_feature_gen.py
  ├─ 18:00  AI 分析      scripts/run_ai_analysis.py
  ├─ 20:00  シグナル生成 scripts/run_strategy_signal.py
  ├─ 21:00  ポートフォリオ構築 scripts/run_portfolio_construction.py
  └─ 21:15  バッチ結果レポート scripts/run_night_batch_report.py
  ↓
21:30  夜間バッチ結果確認（レポート参照）
  ↓
08:30  Execution 起動
09:00  市場オープン → 寄付き発注
  ↓
ザラ場中
  ├─ Execution ループ（発注・約定確認・ポジション更新）
  └─ Monitoring ループ（プロセス監視・ドローダウン監視・異常アラート）
  ↓
15:30  市場クローズ → Market Close レポート生成
```

---

### 夜間バッチスクリプト

夜間バッチは Windows タスクスケジューラで自動実行します（`scripts/setup_task_scheduler.ps1` 参照）。手動実行も可能です。

**データ更新**（15:30 実行）

```
python scripts/run_data_update.py
```

J-Quants から当日の株価・財務・銘柄マスタを取得し `prices_daily` 等を更新します。  
ニュース記事（Yahoo RSS）も収集します。翌日のすべての処理はこのデータを起点とします。

**特徴量生成**（16:00 実行）

```
python scripts/run_feature_gen.py
```

`prices_daily` をもとにモメンタム・ボラティリティ・出来高指標などを計算し `features` テーブルに保存します。  
シグナル生成の入力となる数値データを整備するステップです。

**AI 分析**（18:00 実行）

```
python scripts/run_ai_analysis.py
```

ニュースのセンチメント分析（GPT-4o-mini）と市場レジーム判定（ETF/LLM ハイブリッド）を実行します。  
各銘柄の `ai_scores` と当日の `market_regime`（bull/bear）を生成します。

**シグナル生成**（20:00 実行）

```
python scripts/run_strategy_signal.py
```

features とオプションの ai_scores を統合してスコアを算出し、各種フィルタ（セクター・ギャップリスク・
breadth_stop・最低保有日数など）を適用して BUY/SELL シグナルを `signals` テーブルに書き込みます。  
Bear レジーム判定は `RegimeProvider` プロトコル経由で行われ、`ENABLE_AI_SENTIMENT=false`（Core-only モード）のときは Bear フィルタが発動しません。

**ポートフォリオ構築**（21:00 実行）

```
python scripts/run_portfolio_construction.py
```

シグナルからポジションサイズを計算し、リスク制御を適用して `signal_queue` に翌日の発注キューを生成します。  
このテーブルが Execution エンジンの入力になります。

**バッチ結果レポート**（21:15 自動実行）

```
python scripts/run_night_batch_report.py
```

各ジョブの実行結果 (`artifacts/job_runs/{date}/`) を読み込み、DB からカウントを集計して READY / READY_WITH_WARNINGS / BLOCKED を判定します。  
`KabuSys_NightBatchReport` タスクが 21:15 に自動実行します。手動確認・再生成にも使用できます。

出力先: `artifacts/night_batch/{date}/summary.json`, `report.md`, `warnings.json`

---

### 夜間バッチ結果確認

**Night Batch レポート確認**（21:30 頃）  
21:15 に自動生成されたレポートを確認します。

```
python scripts/run_night_batch_report.py
```

判定結果:

- `READY` — 全必須ジョブ成功・`signal_queue` 作成済み → 翌日執行可
- `READY_WITH_WARNINGS` — 警告あり・準備は完了 → 内容確認の上で判断
- `BLOCKED` — 必須ジョブ失敗または `signal_queue` 空 → 自動執行を開始しない

---

### Execution（自動執行エンジン）

**目的:** `signal_queue` の発注キューを読み込み、市場開始後に実際の注文を送信します。  
約定確認・ポジション更新・リコンシリエーションを担います。

```
python -m kabusys.run_execution
```

- `KABUSYS_ENV=paper_trading` にすると MockBroker を使用し `data/paper_trading.db` に記録（本番 DB は汚染されません）
  - 起動時に `paper_trading.db` の約定履歴からポジション・現金残高を自動復元（日次再起動後も状態継続）
  - `KABU_USE_SANDBOX=true` を設定するとポート 18081 のkabu検証環境に実際に接続してテスト可能
- 起動時にブローカーとのポジション差分を自動チェック（リコンシリエーション）します
- `data/execution.pid` に PID を記録し、`data/stop_requested.flag` で安全停止します

```
# ペーパートレードモードで起動
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

---

### Monitoring（バックグラウンド監視）

**目的:** Execution プロセスとシステムリソースを定期ポーリングで監視します。  
ドローダウン超過・API 切断・プロセス停止を検知すると LINE アラートと Kill Switch を発動します。

```
python -m kabusys.run_monitoring
```

- ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で設定します
- 監視データは `KABUSYS_ENV` に関係なく常に本番 SQLite（`data/monitoring.db`）に記録されます
- `data/monitoring.pid` に PID を記録します

---

### Streamlit 監視ダッシュボード

**目的:** ブラウザでシステム状態・運用成績・シグナルを一覧監視するための GUI ツールです。  
`MonitoringEngine` とは独立して起動します。

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

| ページ | 主な確認内容 |
|---|---|
| **Home** | Kill Switch / Execution・Monitoring プロセス状態 / ドローダウン / 直近エラーイベント |
| **Initial Setup** | 環境変数・設定・DB・Task Scheduler の初期セットアップ確認 |
| **Pre-Market** | 朝の READY/BLOCKED 判定 / データ鮮度 / 停止フラグ確認 |
| **Execution Startup** | 起動直後のリコンシリエーション差分 / ポジション整合確認 |
| **Intraday Monitor** | ザラ場監視（自動更新）/ Kill Switch 状態 / 注文エラー / ドローダウン |
| **Signal Queue** | 翌営業日の発注キュー（pending 件数）/ ポートフォリオ目標 / 直近シグナル |
| **Performance** | エクイティカーブ / 保有ポジション / 取引履歴 / Paper Verification |
| **Failure Recovery** | 障害イベント集約 / 復旧ガイド |
| **WebManual** | 運用マニュアル閲覧ビュー |
| **Strategy Lab** | 市場レジームスコア / AI スコアランキング / シグナル推移 |

- Home は SQLite `monitoring.db`（read-only）。
- Initial Setup / Pre-Market / Execution Startup / Intraday Monitor / Failure Recovery は `operations_data.py` 経由で SQLite `monitoring.db`（read-only）。
- Performance > Paper Verification タブは SQLite `paper_trading.db`（read-only URI モード）。
- Signal Queue / Performance（Paper Verification 以外）/ Strategy Lab は DuckDB `kabusys.duckdb` を読み取り専用で参照します。

---

### ザラ場監視 CLI

**目的:** ザラ場中にターミナルからシステム状態をリアルタイム確認するためのツールです。  
CPU/メモリ・Execution プロセスの生死・ドローダウン・注文エラー件数などを表示します。

```
# 1 回だけ表示
python -m kabusys.run_intraday_monitor

# 30 秒ごとに自動更新（watch モード）
python -m kabusys.run_intraday_monitor --watch --interval 30
```

---

### レポート生成

各レポートは `--save` で `artifacts/` 以下に Markdown と JSON を保存します。

**Pre-Market Report**（08:30 頃）  
市場開始前に当日の執行準備が整っているか確認します。Signal Queue の状態・リスク上限・接続状況などを READY / BLOCKED で判定します。

```
python -m kabusys.run_pre_market_report --save
```

**Market Close Summary**（15:30 頃）  
引け後に当日の執行結果をまとめます。約定件数・実現損益・未約定の残注文などを確認します。

```
python -m kabusys.run_market_close_report --save
python -m kabusys.run_market_close_report --date 2026-04-28 --save --json
```

**Position Reconciliation**（任意・ザラ場中も利用可）  
ブローカー側のポジションとシステム内ポジションの差分を照合します。ズレがある場合に警告を出します。

```
python -m kabusys.run_position_reconciliation_report --save
# ザラ場中に 10 分ごと自動更新で監視
python -m kabusys.run_position_reconciliation_report --watch --interval 600
```

**Performance Report**（任意）  
日次・週次・月次の運用成績（損益・勝率・シャープ比など）を集計します。本番とペーパーを別々に確認できます。

```
python -m kabusys.run_performance_report --type daily --env live --save
python -m kabusys.run_performance_report --type monthly --env paper_trading --from 2026-01-01 --to 2026-04-30 --save
```

---

### バックテスト

**目的:** 過去の DB データを使って戦略のシミュレーションを行います。本番 DB を汚染せずインメモリで実行します。

```
python -m kabusys.backtest.run --db data/kabusys.duckdb --start 2025-01-01 --end 2025-12-31
```

特定銘柄のみを対象とするスコープ指定（manual_codes モード）:

```
python -m kabusys.backtest.run --db data/kabusys.duckdb --start 2025-01-01 --end 2025-12-31 \
  --scope-mode manual_codes --codes 7203 9984 6758
```

`--no-preserve-universe-filters`: 除外理由の表示を切り替える診断用フラグ（実際のフィルタ動作は変わりません）。

---

### Paper Trading 検証ツール

**目的:** ペーパートレード期間中の注文成功率・レイテンシ・稼働率などを集計し、本番移行の可否を判定します。

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

---

### 停止方法

Execution / Monitoring は `data/stop_requested.flag` ファイルを作成すると次のループで安全に終了します。

```
# Windows
type nul > data\stop_requested.flag

# macOS / Linux
touch data/stop_requested.flag
```

または `scripts/stop_system.py` を使うと 10 秒タイムアウト後に強制終了します。

---

注意: 多くのスクリプトは exit code で状態を表現します（BLOCKED → 1、READY → 0 など）。CI/監視連携時は戻り値を確認してください。

---

## レポートの保存場所（デフォルト）

各レポートは保存フラグを指定すると `artifacts/` 以下に保存されます（モジュールごとにパスは概ね固定）:

- Signal Queue: artifacts/signal_queue/YYYY-MM-DD/
  - summary.json, report.md, warnings.json
- Job Runs: artifacts/job_runs/YYYY-MM-DD/
  - {job_name}.json（各夜間バッチジョブの実行結果）
- Night Batch: artifacts/night_batch/YYYY-MM-DD/
  - summary.json, report.md, warnings.json
- Execution Startup: artifacts/execution_startup/YYYY-MM-DD/
- Pre-Market: artifacts/pre_market/YYYY-MM-DD/
- Market Close: artifacts/market_close/YYYY-MM-DD/
- Performance: artifacts/performance/{env}/{type}/{period}/

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なコード配置（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py               — 対話式 .env 作成ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_intraday_monitor.py       — ザラ場監視 CLI
  - run_pre_market_report.py      — Pre-Market レポートエントリ
  - run_market_close_report.py    — Market Close レポートエントリ
  - run_position_reconciliation_report.py — Position Reconciliation レポート
  - run_signal_queue_report.py    — Signal Queue レポート
  - run_performance_report.py     — Performance レポート
  - operations/                    — 各種レポート生成ロジック（pure function）
    - pre_market_report.py
    - night_batch_report.py
    - job_run_recorder.py          — 夜間バッチジョブ実行結果の書き出し・読み込み
    - market_close_report.py
    - performance_collector.py
    - performance_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - position_reconciliation_report.py
    - intraday_collector.py
    - notifier.py                  — LINE 通知基盤
  - execution/                     — Execution 関連（Broker クライアントファクトリ等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/                    — Monitoring 関連
    - monitoring_db.py             — SQLite 永続化層（MonitoringDB / init_monitoring_db）
    - monitoring_engine.py         — 各 Monitor を統括するポーリングエンジン
    - system_monitor.py            — CPU / メモリ / プロセス監視
    - streamlit_dashboard.py       — Streamlit Home ページ（SQLite 参照）
    - dashboard_data.py            — Core 運用ページ向けデータロード関数（DuckDB / SQLite）
    - operations_data.py           — 運用フローページ向けデータロード関数（SQLite / Streamlit 非依存）
    - strategy_lab_data.py         — Strategy Lab ページ（AI Addon）専用データロード関数（DuckDB）
    - pages/
      - 2_Initial_Setup.py         — 環境変数・設定・DB・Task Scheduler 確認
      - 3_Pre_Market.py            — 朝の READY/BLOCKED 判定・データ鮮度確認
      - 4_Execution_Startup.py     — 起動直後のリコンシリエーション差分確認
      - 5_Intraday_Monitor.py      — ザラ場監視（自動更新）・Kill Switch 確認
      - 6_Signal_Queue.py          — 発注キュー・シグナル確認
      - 7_Performance.py           — エクイティカーブ・ポジション・取引履歴・Paper Verification
      - 8_Failure_Recovery.py      — 障害イベント集約・復旧ガイド
      - 9_WebManual.py             — 運用マニュアル閲覧ビュー
      - 10_Strategy_Lab.py         — 市場レジーム・AI スコア・シグナル推移
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
- config/
  - risk_config.yaml（等の YAML 設定ファイル）
- data/
  - monitoring.db（デフォルト）
  - kabusys.duckdb（デフォルト: data/kabusys.duckdb）
  - paper_trading.db（ペーパートレード用）
  - stop_requested.flag, *.pid（実行時生成）
- artifacts/
  - signal_queue/
  - pre_market/
  - market_close/
  - performance/
  - execution_startup/
  - night_batch/

---

## ヒント・注意点

- .env の自動ロード:
  - `src/kabusys/config.py` はプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動読み込みします。必要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- DB パス:
  - Monitoring は「環境に関係なく」本番 `sqlite_path` を参照する実装になっています。paper_trading と本番 DB を完全に分離したい場合は注意してください（Execution は `settings.is_paper` の場合 `paper_sqlite_path` を使う）。
- risk_config.yaml:
  - `config/risk_config.yaml` が必要（Execution 側で読み込み）。欠落やパースエラーは起動失敗要因になります。
- Paper Trading:
  - Paper 環境でも動作検証ができるように mock ブローカーと別 DB が用意されています。`PAPER_FILL_MODE` の値は `instant`/`partial`/`never`/`reject` のいずれかに設定してください。
- ロギング:
  - 各スクリプトには `setup_logging` を呼ぶ仕組みがあります。`LOG_LEVEL` を `.env` で調整してください。
