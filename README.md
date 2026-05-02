# KabuSys — README

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアスクリプトとレポート生成モジュール群を含みます。  
以下はプロジェクトの概要、主な機能、セットアップ手順、利用方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の要素を持つ自動売買システムです。

- 夜間バッチでシグナル生成 → 翌営業日に自動執行するフローを想定
- 実行エンジン（ExecutionEngine）、監視（SystemMonitor）、複数の CLI レポート／診断ツールを備える
- DuckDB（分析用）とSQLite（監視・履歴用）を利用
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を環境変数で切替可能
- レポートは CLI で表示、JSON/Markdown で保存可能（artifacts 配下）

このリポジトリには、起動スクリプト、設定管理、各種レポート生成ロジック、運用診断ツールが含まれています。

---

## 機能一覧

主な機能（抜粋）:

- Execution 起動スクリプト（run_execution）
  - 本番/ペーパートレードのブローカー切替、起動時リコンシリエーション、ExecutionEngine の起動
  - 起動時に Execution Startup Summary を生成・保存可能
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離

- Monitoring（run_monitoring）
  - SystemMonitor のポーリングループを実行。監視データを SQLite に記録
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - stop フラグ（data/stop_requested.flag）で安全停止

- CLI レポート群
  - Pre-Market Report（run_pre_market_report）: 朝の運用開始準備チェック（READY / WARN / BLOCKED）
  - Market Close Summary（run_market_close_report）: 引け後チェック（OK / BLOCKED）
  - Night Batch Report（operations/night_batch_report）: 夜間バッチの総合判定
  - Signal Queue Confirmation（run_signal_queue_report / operations/signal_queue_report）
  - Position Reconciliation（run_position_reconciliation_report）
  - Performance Report（run_performance_report）: 日次/週次/月次の成績レポート
  - Intraday Monitor（run_intraday_monitor）: ザラ場中リアルタイム監視表示

- 設定管理・検証ツール
  - 環境設定ウィザード（config_setup）で .env の初期作成・更新を対話式に支援
  - validate_config による .env / config/*.yaml の事前検証

- 開発/運用ユーティリティ
  - Paper Trading 検証レポート（tools/paper_verification_report）など

---

## 前提・準備（Prerequisites）

- Python 3.9+（実行環境の仕様に合わせてください）
- 必要なパッケージ（代表例）
  - duckdb
  - PyYAML
- DuckDB / SQLite を使います。デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper-trading SQLite: data/paper_trading.db

パッケージはプロジェクトの requirements.txt / pyproject.toml があればそちらを使用してください。

---

## 環境変数・設定

主に使う環境変数（一部抜粋）:

- JQUANTS_REFRESH_TOKEN（必須）
- JQUANTS_BULK_API_KEY（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABU_TRADE_PASSWORD（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとプロジェクト起動時の .env 自動ロードを無効化できます

設定の自動読み込み:
- プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。.env に機密情報を含めて Git 管理しないでください。

Settings クラス（config.py）で各種設定へのアクセスを提供しています。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または pip install duckdb pyyaml
4. 環境変数の設定
   - 対話形式で .env を作る（推奨）:
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 失敗や警告が出たら .env や config/*.yaml を確認
5. 必要に応じてデータディレクトリを用意
   - data/（monitoring.db, kabusys.duckdb, paper_trading.db など）
   - artifacts/（レポートの保存先、実行時に自動作成される）

注意:
- config/risk_config.yaml などの YAML 設定ファイルが必要です。validate_config で存在確認・パース確認を行えます。

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

---

## リスク設定（重要）

Execution 起動時に読み込まれる `config/risk_config.yaml` の主要設定項目（例）:

- risk.max_position_pct: 1 を最大とする割合（0 < v <= 1）
- risk.max_utilization: 0 < v <= 1（max_position_pct ≤ max_utilization を推奨）
- risk.rate_limit_per_sec: 1 以上の整数（API レート制限）
- risk.circuit_breaker_errors: 1 以上の整数
- risk.circuit_breaker_window_sec: 1 以上の整数
- risk.max_drawdown: 0 < v <= 1

不正な値や欠落は起動時にエラーとなります。

---

## ディレクトリ構成

主要なソースファイル / モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / Settings
    - config_setup.py                # .env 対話ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # Execution 起動スクリプト
    - run_monitoring.py              # Monitoring ポーリングループ起動
    - run_intraday_monitor.py        # ザラ場中監視 CLI
    - run_signal_queue_report.py     # Signal Queue レポート CLI
    - run_position_reconciliation_report.py
    - run_performance_report.py
    - run_pre_market_report.py
    - run_market_close_report.py
    - run_monitoring.py
    - run_position_reconciliation_report.py
    - operations/
      - signal_queue_report.py
      - execution_startup_report.py
      - pre_market_report.py
      - market_close_report.py
      - night_batch_report.py
      - performance_report.py
      - performance_collector.py
      - pre_market_collector.py (参照される実装)
      - intraday_collector.py (参照される実装)
      - position_reconciliation_report.py (参照)
    - execution/
      - execution_engine.py (参照)
      - order_manager.py (参照)
      - order_repository.py (参照)
      - reconciler.py (参照)
      - broker_factory.py (参照)
      - risk_manager.py (参照)
    - monitoring/
      - system_monitor.py (参照)
      - monitoring_db.py (参照)
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py (参照)
      - process_priority.py (参照)
- config/
  - risk_config.yaml (等の YAML 設定ファイル)
- data/
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
  - paper_trading.db (ペーパートレード用)
  - stop_requested.flag, *.pid（実行時生成）
- artifacts/
  - signal_queue/
  - pre_market/
  - market_close/
  - performance/
  - execution_startup/
  - night_batch/

各モジュールの実装（execution/、monitoring/、operations/）はアプリケーション固有のロジックを含みます。README に載せきれない詳細はソースコードの docstring を参照してください。

---

## 運用上の注意事項

- 本番環境（KABUSYS_ENV=live）では特に LINE 通知などの設定を確認してください（validate_config で警告を確認できます）。
- .env に機密情報（API トークン、パスワード）を保存する場合は絶対に Git にコミットしないでください。
- 停止はなるべくデータベースや PID/フラグを通じて安全に行ってください（data/stop_requested.flag を利用）。
- ペーパートレードは本番 DB と分離しており、デフォルトで data/paper_trading.db を使用します。

---

## トラブルシューティング

- 設定チェックでエラーが出る:
  - python -m kabusys.validate_config を実行し、エラー／警告メッセージに従って .env や config/*.yaml を修正してください
- DB に接続できない:
  - DUCKDB_PATH / SQLITE_PATH のパスやファイルの有無、アクセス権を確認してください
- 監視が停止した:
  - data/*.pid を確認し、stop flag（data/stop_requested.flag）や監視プロセスのログを確認してください

---

必要であれば、各 CLI やモジュールの詳しい説明（引数、出力フォーマット、保存先パスなど）を追記します。どの部分を詳しく書くか指定してください。