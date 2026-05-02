# KabuSys

日本株向けの自動売買システムの一部（実行/監視/レポート生成ツール群）です。本リポジトリは CLI エントリポイント群、レポート生成ロジック、設定管理ユーティリティなどを含みます。

## プロジェクト概要
- 起動スクリプト（Execution / Monitoring / レポート系 CLI）
- 設定管理（`.env` 自動読み込み、設定ウィザード）
- 各種レポート生成モジュール（Pre-Market / Market Close / Performance / Signal Queue / Execution Startup / Night Batch 等）
- Paper Trading（ペーパートレード）用の分離された DB をサポート
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB として利用

主な目的は「夜間バッチ → 翌営業日のシグナル生成 → 実行エンジン起動 → 監視 / レポート出力」を支援することです。

## 主な機能一覧
- Execution 起動（実注文またはペーパートレード）
  - コマンド: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは `data/paper_trading.db` に保存（本番 DB と分離）
  - 起動時にリコンシリエーションを行い、Execution Startup Summary を生成
- Monitoring（継続実行用ポーリング）
  - コマンド: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能
  - Monitoring は環境にかかわらず本番の `sqlite_path` を使用
  - PID ファイル: `data/monitoring.pid`
  - 停止フラグ: `data/stop_requested.flag` を検知して安全停止
- ザラ場中監視 CLI（リアルタイム監視）
  - コマンド: python -m kabusys.run_intraday_monitor [--watch] [--interval N]
- レポート生成 CLI
  - Pre-Market Report: python -m kabusys.run_pre_market_report [--save] [--json]
  - Market Close Summary: python -m kabusys.run_market_close_report [--date YYYY-MM-DD] [--save] [--json]
  - Position Reconciliation View: python -m kabusys.run_position_reconciliation_report [--date] [--save] [--json] [--watch]
  - Signal Queue Confirmation: python -m kabusys.run_signal_queue_report [--date] [--save] [--json]
  - Performance Report (daily/weekly/monthly): python -m kabusys.run_performance_report --type daily|weekly|monthly [--env live|paper_trading] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--save]
  - Paper Trading 検証レポート（ツール）: python -m kabusys.tools.paper_verification_report [--from] [--to] [--db PATH]
- 設定関連
  - 対話式 `.env` ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

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
  └─ 21:00  ポートフォリオ構築 scripts/run_portfolio_construction.py
  ↓
21:30  夜間バッチ結果確認（Signal Queue / 異常チェック）
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

features・ai_scores・market_regime を統合してスコアを算出し、各種フィルタ（セクター・ギャップリスク・
breadth_stop・最低保有日数など）を適用して BUY/SELL シグナルを `signals` テーブルに書き込みます。

**ポートフォリオ構築**（21:00 実行）

```
python scripts/run_portfolio_construction.py
```

シグナルからポジションサイズを計算し、リスク制御を適用して `signal_queue` に翌日の発注キューを生成します。  
このテーブルが Execution エンジンの入力になります。

---

### 夜間バッチ結果確認

**Signal Queue 確認**（21:30 頃・任意）  
翌営業日の発注予定を確認し、READY / BLOCKED / READY_WITH_WARNINGS を判定します。

```
python -m kabusys.run_signal_queue_report
python -m kabusys.run_signal_queue_report --date 2026-04-28 --save --json
```

---

### Execution（自動執行エンジン）

**目的:** `signal_queue` の発注キューを読み込み、市場開始後に実際の注文を送信します。  
約定確認・ポジション更新・リコンシリエーションを担います。

```
python -m kabusys.run_execution
```

- `KABUSYS_ENV=paper_trading` にすると MockBroker を使用し `data/paper_trading.db` に記録（本番 DB は汚染されません）
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

## 設定（主な環境変数とデフォルト）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY: J-Quants API 用（必須）
- KABU_API_PASSWORD, KABU_API_BASE_URL, KABU_TRADE_PASSWORD: kabuステーション API 関連
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant/partial/never/reject）

注意: `.env` 自動読み込みの順序は OS 環境変数 > .env.local > .env です。OS 環境変数は保護され、.env から上書きされません。

## レポートの保存先（デフォルト）
- artifacts/pre_market/{YYYY-MM-DD}/
- artifacts/market_close/{YYYY-MM-DD}/
- artifacts/performance/{env}/{type}/{period}/
- artifacts/signal_queue/{YYYY-MM-DD}/
- artifacts/execution_startup/{YYYY-MM-DD}/
- artifacts/night_batch/{YYYY-MM-DD}/

保存時は JSON、Markdown、警告リストなどが出力されます。

## 停止・制御ファイル
- data/stop_requested.flag: これが存在すると実行ループ（Execution / Monitoring 等）が安全に終了します
- data/kill.flag: 設定により Kill Switch（外部からの強制停止）に利用
- data/*.pid: 起動プロセスの PID を記録（例: data/execution.pid, data/monitoring.pid）

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env 読み込み等）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — Execution 起動スクリプト（メイン実行エンジン）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動
  - run_intraday_monitor.py  — ザラ場監視 CLI
  - run_pre_market_report.py — Pre-Market Report CLI
  - run_market_close_report.py — Market Close Summary CLI
  - run_position_reconciliation_report.py — Position Reconciliation CLI
  - run_signal_queue_report.py — Signal Queue Confirmation CLI
  - run_performance_report.py — Performance レポート CLI
  - operations/               — レポート生成や集計ロジック（pure functions）
    - pre_market_report.py
    - market_close_report.py
    - performance_collector.py
    - performance_report.py
    - signal_queue_report.py
    - execution_startup_report.py
    - night_batch_report.py
    - notifier.py              — LINE 通知基盤
  - execution/                — Execution エンジン周り（BrokerFactory, OrderManager 等）
  - monitoring/               — 監視関連（DB 初期化、SystemMonitor 等）
  - tools/                    — 補助ツール（paper_verification_report 等）
  - utils/                    — ロギング設定やプロセス優先度設定などユーティリティ
- scripts/
  - setup_db.py              — DB 初期化スクリプト（DuckDB + SQLite）
  - run_data_update.py       — データ更新（夜間バッチ）
  - run_feature_gen.py       — 特徴量生成（夜間バッチ）
  - run_ai_analysis.py       — AI 分析（夜間バッチ）
  - run_strategy_signal.py   — シグナル生成（夜間バッチ）
  - run_portfolio_construction.py — ポートフォリオ構築（夜間バッチ）
  - setup_task_scheduler.ps1 — Windows タスクスケジューラ登録
  - start_system.py          — システム起動スクリプト
  - stop_system.py           — システム停止スクリプト

## 開発時のヒント / 注意点
- validate_config で設定エラーや警告を事前に確認してください:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります
- Paper Trading は本番 DB と分離されます。KABUSYS_ENV=paper_trading にすると `paper_sqlite_path` が使用されます
- monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を参照します（監視系は常に本番 DB を対象にするため）
- `.env` に秘匿値（API トークン等）を含めるため、Git 管理しないでください
- long-running プロセス（Execution / Monitoring）は PID ファイルと stop flag を利用して制御します
