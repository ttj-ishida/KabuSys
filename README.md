# KabuSys — README (日本語)

注意: このREADMEはリポジトリ内の src/kabusys 以下の実装に基づき作成しています。

概要
----
KabuSys は日本株の自動売買システムのコアライブラリ群です。  
価格データ集計・ファクター演算・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
および AI を用いたニュースセン定義など、アルゴリズム売買に必要な主要機能をモジュール化しています。

主な機能
--------
- Execution（発注）
  - 発注状態管理、OrderManager、リコンシリエーション（Reconciler）
  - Paper Trading モード（MockBrokerClient）による本番分離
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視ログ保存 (monitoring_db)
  - LINE へのアラート送信（AlertManager）
  - kill.flag による外部停止シグナル
  - Streamlit ダッシュボード表示スクリプト
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（調査・特徴量計算）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB 使用）
  - 将来リターン、IC（Information Coefficient）計算や統計サマリー
- AI（LLM を用いた処理）
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - 環境設定読み込み（.env 自動読込）、プロセス優先度設定、CPU affinity、等

要件（想定）
-------------
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード用）
- SQLite（組み込み）
- ネットワーク（OpenAI / LINE 通知 を使う場合）

セットアップ手順
----------------
1. リポジトリをチェックアウトし、ソースルート（src）を PYTHONPATH に通すかパッケージとしてインストールします。
   - 開発時の例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -U pip
     - pip install duckdb psutil requests openai streamlit
     - PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
   - またはパッケージ化されていれば `pip install -e .` を利用

2. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意（例）
     - OPENAI_API_KEY（AI 機能使用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
   - Paper Trading 用:
     - KABUSYS_ENV=paper_trading（paper_trading モードを有効化）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（デフォルト）

3. データベースパス（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db

使い方
------

共通
- KABUSYS_ENV 値:
  - development / paper_trading / live
  - Settings クラスで検証され、不正な値は例外になる

環境読み込みについて
- .env/.env.local の自動読み込みは Settings モジュール起動時に行われます。
- .env の読み込み順序: OS env > .env.local > .env（.env.local は上書き）

起動スクリプト例
- ExecutionEngine を起動（本番もしくは紙取引）
  - PYTHONPATH=src KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - production/live:
    - PYTHONPATH=src KABUSYS_ENV=live python -m kabusys.run_execution
  - run_execution はプロセス優先度を高く設定し（set_process_priority("high")）、DB を開いて ExecutionEngine を起動します
  - paper_trading モードでは MockBroker を使用し、paper 用 SQLite（data/paper_trading.db）に記録され本番 DB と分離されます

- Monitoring を起動
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に変更可能（デフォルト 60秒）
  - 監視は Settings.env に関係なく本番 sqlite_path を使用して監視ログを永続化します
  - 起動時にプロセス優先度を High に設定します

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db path/to/db.sqlite または環境変数 PAPER_TRADING_SQLITE_PATH

AI 機能
- OpenAI を呼ぶ機能（news_nlp.score_news, regime_detector.score_regime）は OPENAI_API_KEY が必要
- API 呼び出しはリトライ・バックオフやレスポンス検証が組み込まれています（失敗時はフォールバック）

監視・安全策
- kill.flag による外部停止
  - KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由文字列を書き込みます
  - ExecutionEngine 側で flag の存在を検出して安全停止させる設計
- RiskMonitor がドローダウン・ポジション上限を検知して risk_logs に記録・kill フラグのトリガーを投げる

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db） — Monitoring は常にこの本番パスを使用
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信に使用
- PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject、デフォルト instant）

ディレクトリ構成（主要ファイル）
----------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化と簡易 DAO (MonitoringDB)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

補足 / 実運用上の注意
-------------------
- Monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します。paper_trading と監視 DB は分離されません（監視は本番志向）。
- Paper Trading は run_execution 側で paper 用 DB に分離されています（settings.is_paper を参照）。
- .env のパース処理はシェルライクな quoting と簡易コメント処理をサポートしますが、複雑なケースでは注意してください。
- OpenAI / LINE など外部 API を使用する機能は、API キーやトークンが不正・未設定の場合にフェイルセーフの動作（ログ出力・スキップ）を行う箇所がありますが、本番導入時は十分な監視とテストを行ってください。

ライセンス・バージョン
--------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: "0.1.0"）。

お問い合わせ / 開発
------------------
- 開発環境では PYTHONPATH=src を付けて実行するか、pip install -e . で編集可能インストールを行ってください。
- 単体モジュールのテストはモジュール設計が純粋関数ベースに配慮されているため行いやすく、OpenAI などネットワークを伴う処理はモックで置き換え可能です（コード内で _call_openai_api を patch する設計がされています）。

以上。必要であれば README に追記したい点（セットアップの詳細、example .env、docker 化手順など）を教えてください。