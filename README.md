# KabuSys — README

このリポジトリは日本株向けの自動売買・研究・監視システム「KabuSys」の一部実装です。コードは純粋関数や DB 操作、ExecutionEngine / Monitoring の起動スクリプト、研究用ファクター計算、AI ベースのニュースセンチメント評価などで構成されています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 主要環境変数と設定
- 運用上の注意点

---

## プロジェクト概要

KabuSys は主に以下の機能を持つモジュール群から構成されます。

- Execution（発注エンジン）: ブローカー API と連携して注文作成・送信・状態遷移管理を行う。
- Monitoring（監視）: システム稼働状態、データ鮮度、注文の滞留・約定異常、リスク（ドローダウンや保有上限）を定期チェックしてログ・アラート・停止フラグを管理する。
- Portfolio（ポートフォリオ構築）: 候補選定・重み計算・単元丸め・リスク調整を行う純粋関数群。
- Research（研究）: DuckDB 上の価格・財務データからファクター計算や統計解析を行う。
- AI（ニュース NLP / レジーム判定）: OpenAI API を使いニュースのセンチメント評価や市場レジーム判定を行う。
- Tools: ペーパートレーディング検証レポート生成や Streamlit ダッシュボードなどのユーティリティ。

設計方針の一部:
- 研究/AI モジュールは本番資金やブローカー API にアクセスしない（DuckDB・SQLite のデータのみ参照／書込）。
- Paper Trading 用 DB は本番 DB と分離（環境 `paper_trading` を使用）。
- 環境変数は .env / .env.local を自動ロード（プロジェクトルートが特定できる場合）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可。

---

## 機能一覧

主要コンポーネントと概略:

- run_execution.py
  - ExecutionEngine の起動エントリポイント。
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: `data/paper_trading.db`）へ記録。
  - プロセス優先度を設定し、必要なコンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立て実行する。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視用 DB は環境に関わらず本番 sqlite_path（`Settings.sqlite_path`）を使用する。

- monitoring/*
  - MonitoringDB: SQLite に対する永続化 API（system_status, trade_logs, positions, risk_logs, dashboard 等のテーブル管理・マイグレーション含む）。
  - SystemMonitor / TradeMonitor / RiskMonitor: 各種チェックとリスクロギング。
  - KillSwitch: フラグファイル（デフォルト `data/kill.flag`）を書き込んで ExecutionEngine に停止シグナルを送る。
  - AlertManager: LINE push による通知（channel token / user id が必要）。
  - streamlit_dashboard.py: Streamlit を使った監視ダッシュボード（read-only で SQLite を開く）。

- portfolio/*
  - 候補選定、重み付け（等配分・スコア比率）、セクター上限適用、ポジションサイズ計算（単元丸め、aggregate cap など）。

- research/*
  - ファクター計算（Momentum, Volatility, Value）、将来リターン計算、IC 計算、統計サマリー。

- ai/*
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores に書き込む。冪等性・バッチ処理・リトライ・レスポンス検証を備える。
  - regime_detector: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成し market_regime を更新。

- tools/paper_verification_report.py
  - Paper Trading DB（デフォルト `data/paper_trading.db`）を読み、稼働率・注文成功率・送信率・レイテンシ等の検証レポートを標準出力に出す。

- utils/process_priority.py
  - psutil を用いてプラットフォームに依存しないプロセス優先度設定・CPU affinity 設定。

---

## セットアップ手順

前提: Python 3.9+（ソースでは typing の Union | を使用しているため 3.10 以上が望ましい）、およびシステムに sqlite3 が利用可能であること。

1. リポジトリをクローン / ソースを配置:
   - 本 README 前提ではパッケージが `src/kabusys` 以下にある構成です。

2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install --upgrade pip
   - 必要な主要パッケージ（代表例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに requirements.txt がある場合はそれを使用してください。

4. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くことで Settings が自動読込します（ただし OS 環境変数が優先）。
   - 必須になる可能性のある変数（使用機能により異なる）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知を有効にする場合）

5. データディレクトリ作成:
   - data フォルダ等を作成して DB を配置してください（自動生成・マイグレーション処理あり）。

---

## 使い方

以下は一般的な起動例とツールの使い方です。

- ExecutionEngine を起動（本番/ペーパートレード切替は KABUSYS_ENV）:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録します。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - export MONITOR_POLL_INTERVAL=120
    - python -m kabusys.run_monitoring
  - 注意: Monitoring は Settings.sqlite_path（監視用本番 DB）を使用します（KABUSYS_ENV に依らず本番 path を読む設計）。

- Streamlit ダッシュボード（監視画面）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 起動時に監視 DB を read-only で開きます。MonitoringEngine が DB を作成/更新していることを確認してください。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 系バッチ処理（例: ニューススコア付与／レジーム判定）
  - これらはモジュール関数として提供されています。スクリプトを直接用意して以下を呼ぶ想定です:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数か関数引数で指定します。

---

## 主要環境変数と Settings

Settings クラス（kabusys.config.Settings）がアプリケーション設定を表します。主な環境変数:

- KABUSYS_ENV: 起動環境（development | paper_trading | live） — デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須とされる箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須とされる箇所あり）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の mock 注文の約定挙動（instant, partial, never, reject）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

また Settings は自動で .env / .env.local をプロジェクトルートから読み込みます（既存の OS 環境変数は保護）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - alert_manager.py
      - kill_switch.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py (参照されるが省略)
      - execution_engine.py (参照されるが省略)
      - reconciler.py
      - broker_factory.py (参照されるが省略)
      - broker_api.py (参照されるが省略)
      - order_record.py (参照されるが省略)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/
      - pipeline.py (参照されるが省略)

（上記のうち一部モジュールの実装ファイルは抜粋されています。全体は src/kabusys 以下にまとまっています。）

---

## 運用上の注意点

- Monitoring は監視用 SQLite（Settings.sqlite_path）を使用します。Monitoring を複数プロセスで同一ファイルに同時書込することは避けてください（SQLite の特性上ロックやパフォーマンスに注意）。
- run_execution はプロセス優先度を上げます（psutil を利用）。OS の権限によっては設定に失敗することがあります（ログで警告が出ます）。
- KillSwitch はファイルベースのフラグで ExecutionEngine を停止させます。`KILL_FLAG_CLEAR_ON_START` 設定により起動時にフラグをクリアするか制御できます。
- AI 機能は OpenAI API に課金が発生します。API エラー / レート制限に対するリトライロジックは実装されていますが、呼び出し頻度・バッチサイズは注意して運用してください。
- Paper Trading と本番 DB は分離されています。Paper Trading 環境を使う場合は `KABUSYS_ENV=paper_trading` を必ず設定してください。

---

必要に応じて README を拡張できます（例: インストール可能なパッケージ一覧を requirements.txt にまとめる、起動スクリプトの systemd ユニット例を追加する、テスト手順を追記する等）。必要なら追加で作成します。