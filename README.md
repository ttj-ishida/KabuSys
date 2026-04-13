# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python コードベースです。本リポジトリは以下の主要機能を含みます: 注文の発行・管理、実行エンジンの起動・再同期処理、ポートフォリオ構築ユーティリティ、ファクター計算、AI（ニュース NLP / レジーム判定）連携、監視・アラート機能、Paper Trading 用の検証ツールなど。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の README.md です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- 重要な環境変数（抜粋）
- ディレクトリ構成

---

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコンポーネント群です。主要な設計方針は以下の通りです。

- 実取引と Paper Trading を明確に分離（DB 等を分ける）
- DuckDB を使った時系列データ / ファクター計算
- SQLite を使った監視ログ保存・簡易 OrdersDB
- OpenAI を使ったニュースのセンチメント解析や市場レジーム判定（任意）
- 監視（MonitoringEngine）と実行（ExecutionEngine）を分離
- 再起動後のリコンシリエーション（Reconciler）で安全に復旧

機能一覧
---------
主な機能・モジュールの概要:

- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV による Paper Trading サポート）
  - reconciler.py: 再起動時の注文・ポジション照合（自動リコンシリエーション）
  - order_manager / order_repository / order_record: 注文ステートマシンと永続化
  - risk_manager: 発注時のリスク制御ロジック

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
  - monitoring_engine.py: System / Trade / Risk Monitor を束ねるポーリングエンジン
  - system_monitor.py: CPU・メモリ・ディスク・データ鮮度・PID チェック
  - trade_monitor.py: 滞留注文・約定異常の検出
  - risk_monitor.py: ドローダウン、ポジション上限の監視
  - monitoring_db.py: SQLite を使った監視ログの永続化
  - alert_manager.py: LINE Push によるアラート（オプション）
  - streamlit_dashboard.py: 監視用 Streamlit ダッシュボード

- ポートフォリオ / 資金配分
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 株数算出（lot 単位丸め、aggregate cap）
  - portfolio.risk_adjustment: セクターキャップ、レジーム乗数

- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン・IC・統計サマリ

- AI（任意）
  - ai.news_nlp: raw_news を LLM（OpenAI）でセンチメント化して ai_scores に書き込み
  - ai.regime_detector: ETF の MA とマクロニュースを LLM で評価し market_regime を算出

- ユーティリティ
  - config.py: 環境変数 / .env 自動ロードと Settings クラス
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------

1. Python と依存パッケージのインストール
   - 推奨: Python 3.10+
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボードを使う場合)
   - 例（pip）:
     - pip install duckdb psutil openai requests streamlit

   ※requirements.txt / pyproject.toml があればそちらを利用してください。

2. リポジトリルートでの実行環境
   - 開発中は src ディレクトリを PYTHONPATH に追加して実行するか、パッケージをインストール(開発モード)してください:
     - export PYTHONPATH=src
     - または: pip install -e .

3. .env ファイル（任意）
   - config.py はプロジェクトルートの .env / .env.local を自動でロードします（OS 環境変数を上書きしない）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 最低限必要な環境変数（利用する機能による）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須：kabu ステーション連携用）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信する場合）

4. データディレクトリ
   - デフォルトの DB パスは data/ 以下（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）です。必要に応じてディレクトリを作成してください。

使い方
------

実行エンジン（Execution）
- 本番または Paper Trading を選んで起動します。
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading は専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用します。
    - PAPER_FILL_MODE（instant|partial|never|reject）でモックブローカーの約定挙動を制御できます。
  - 本番/開発:
    - python -m kabusys.run_execution
    - Settings により KABUSYS_ENV=live/development を切り替えます。

監視（Monitoring）
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視ログは本番 DB を参照）。

Paper Trading 検証レポート
- SQLite の Paper Trading DB から期間指定でレポートを生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db PATH で DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

監視ダッシュボード（Streamlit）
- 起動例（プロジェクトルートから）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開いて表示します。MonitoringEngine が DB を作成していることが前提。

AI 機能
- OpenAI API を用いる機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
- ai.score_news / ai.regime_detector.score_regime は DuckDB 接続を受け取り、ai_scores / market_regime へ書き込みます。
- API 呼び出しでの一時エラーはリトライロジックを含み、失敗時はフェイルセーフで処理を継続する設計です。

プロセス優先度 / PID / kill.flag
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。
- ExecutionEngine の PID を pid_file (Settings.pid_file_path, デフォルト data/execution.pid) に書き出し、Monitoring は PID ファイルの存在/生存をチェックします。
- KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側で kill.flag を確認して安全停止する設計です。

重要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能を使う場合に必要
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- PID_FILE_PATH: pid ファイルのパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...、デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用

ディレクトリ構成
----------------
（src 配下を想定）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (Settings / .env 自動ロード)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP → ai_scores)
    - regime_detector.py (市場レジーム判定)

  - monitoring/
    - __init__.py
    - monitoring_db.py (SQLite テーブル作成・CRUD)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py (LINE Push)
    - kill_switch.py
    - streamlit_dashboard.py

  - execution/
    - order_manager.py
    - reconciler.py
    - その他（broker_factory 等: ブローカークライアント抽象化）

  - portfolio/
    - portfolio_builder.py (候補選定, 重み)
    - position_sizing.py (株数計算)
    - risk_adjustment.py (セクター上限、レジーム乗数)
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - monitoring scripts / tools
    - tools/
      - __init__.py
      - paper_verification_report.py

  - utils/
    - process_priority.py
    - __init__.py

運用上の注意
------------
- 監視（Monitoring）は KABUSYS_ENV に依存せず Settings.sqlite_path（本番監視 DB）を参照します。Paper Trading を監視対象にしたい場合は環境や設定を調整してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。CI / テストで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使う機能は呼び出し毎に API キーが必要です。API コールはレート制限や一時エラーに対しリトライを持ちますが、長時間の処理やコストに注意してください。
- SQLite と DuckDB のファイルは適切なバックアップを行ってください。監視ログは永続化されます。

ライセンス / 貢献
-----------------
（ここにライセンス・貢献ガイドラインを追記してください）

---

必要であれば、README にサンプル .env.example、起動スクリプトの systemd サービス定義例、依存パッケージの固定バージョン、テスト実行方法などを追加できます。追加希望があれば教えてください。