# KabuSys

KabuSys は日本株向けの自動売買 / 監視フレームワークです。本リポジトリは取引エンジン、監視サブシステム、ポートフォリオ構築・サイズ計算、リサーチ用ファクター計算、AI を使ったニュース解析などを含みます。

以下はコードベースから自動生成した README です。開発者向けの起動方法・環境変数・ディレクトリ構成をまとめています。

---

## プロジェクト概要

- 目的: 日本株自動売買システム（KabuSys）のコアライブラリと運用ユーティリティ群
- 主な機能:
  - ExecutionEngine: シグナルに基づく発注・注文管理・リスク管理
  - Monitoring: システム状態・注文滞留・ドローダウン等の監視とアラート
  - Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約
  - Research: DuckDB を用いたファクター計算・将来リターン・IC 計算
  - AI モジュール: OpenAI を利用したニュースセンチメント（ai/news_nlp）、市場レジーム判定（ai/regime_detector）
  - 運用ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード
- 永続化:
  - SQLite（監視ログ / orders / paper trading DB）
  - DuckDB（時系列価格・ファクター計算用）

---

## 機能一覧（主要コンポーネント）

- run_execution.py
  - ExecutionEngine を起動するスクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の DB に記録（本番 DB と完全分離）
  - 停止フラグ（data/stop_requested.flag）を検知すると安全に停止
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視ログは sqlite（monitoring.db）へ永続化
- monitoring/*
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
  - MonitoringDB: SQLite テーブルの初期化・読み書き（init_monitoring_db）
  - streamlit_dashboard.py: Streamlit を使った監視ダッシュボード
- execution/*
  - OrderManager, Reconciler（再起動時の自動復旧）, OrderRepository, RiskManager など
- portfolio/*
  - 候補選定 (select_candidates)、重み計算 (calc_equal_weights / calc_score_weights)
  - リスク調整（apply_sector_cap、calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）
- research/*
  - calc_momentum / calc_volatility / calc_value（DuckDB ベース）
  - ファクター探索・IC 計算・統計サマリー
- ai/*
  - news_nlp.score_news: raw_news を LLM（OpenAI）でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ma200 とマクロニュースセンチメントを合成して market_regime を更新
- tools/paper_verification_report.py
  - Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシなど）
- utils/process_priority.py
  - プラットフォーム抽象化したプロセス優先度・CPU affinity 設定（psutil）

---

## セットアップ手順

推奨 Python バージョン: 3.8+

1. リポジトリをクローンし、作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（概略）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - sqlite3 は標準ライブラリで提供されます。
   - 実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化）。
   - 必要な主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants API のトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
     - KABUSYS_ENV — 実行環境（development / paper_trading / live）
     - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（paper_trading 時）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）

   - 例 .env（簡易）
     ```
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     JQUANTS_REFRESH_TOKEN=...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方

基本的な起動コマンド例と操作方法を示します。

- ExecutionEngine を起動（通常モード）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に data/execution.pid が作成されます（Settings.pid_file_path）。
  - 停止は外部から data/stop_requested.flag を作成することで安全停止されます（スクリプトも同ファイルを監視します）。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて発注をローカル DB（PAPER_TRADING_SQLITE_PATH）に記録します：
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は MONITOR_POLL_INTERVAL で指定（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（environment に依存しない）。
  - 監視ループは data/stop_requested.flag を検知すると終了します。

- Streamlit ダッシュボード（監視 DB の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - DB を読み取り専用で開くため、監視プロセスが稼働中のままでも参照できます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db` でパスを指定可能。

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または引数で指定）。
  - 例（Python REPL 等から）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,10), api_key="sk-...")
    ```
  - regime_detector.score_regime も同様に呼び出せます。

- 停止フラグ / キルスイッチ
  - KillSwitch は監視の中で条件を満たすと data/kill.flag を書き込みます（ExecutionEngine 起動時に読むことで停止指示に使える）。
  - 手動で停止する場合は data/stop_requested.flag を作成してください（run_*.py が監視しているファイル）。
  - kill.flag をクリアするには KillSwitch.clear() を呼ぶか、ファイルを手動で削除してください。

---

## 主要な環境変数（Settings に基づく）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: Execution PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）

Settings モジュールは .env / .env.local をプロジェクトルートから自動読み込みします（ただし OS の環境変数が優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 注意点 / 運用メモ

- ExecutionEngine と Monitoring はファイルベースのフラグ（data/stop_requested.flag / data/kill.flag / data/execution.pid）でプロセス間通信を行います。これらファイルの扱いに注意してください。
- psutil を使ったプロセス優先度設定は権限や OS に依存します（失敗時は警告ログでスキップされます）。
- AI モジュールは API 通信のリトライやフェイルセーフを組み込んでいますが、API キーと利用料に注意してください。
- DuckDB / SQLite のスキーマは init_monitoring_db() によって自動作成・マイグレーションされます（monitoring 側）。
- Paper Trading モードは本番 DB と分離される設計です。運用時は必ず KABUSYS_ENV を確認してください。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイルと役割の簡易ツリーです（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（Settings）
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py            — 実行エンジン（EngineConfig 等）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ...
  - monitoring/
    - monitoring_db.py               — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/                            — デフォルトの DB / PID / flag を置く想定ディレクトリ（リポジトリ外に作成）
  - utils/
    - process_priority.py
    - __init__.py

---

## よくある操作例

- 監視だけ立ち上げる（本番 DB を使用）
  ```
  python -m kabusys.run_monitoring
  ```

- Execution を paper_trading で起動（本番 DB へ影響なし）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Paper Trading レポート（特定期間）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード（ローカル）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

README に記載した例やデフォルトパスはコード内の Settings 実装・スクリプトに従っています。運用環境に合わせて .env を用意し、必要な外部 API キーやパスを設定してください。必要ならば README を環境固有の手順（サービス化、systemd ユニット、コンテナ化など）に合わせて拡張してください。