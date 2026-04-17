KabuSys — README
===============

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なワークフロー群です。本リポジトリには、取引実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築ユーティリティ、研究用ファクター計算、OpenAI を用いたニュース NLP / レジーム判定などが含まれます。データ永続化には主に SQLite（監視・発注ログ）と DuckDB（時系列・ファクター計算）を使用します。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使い、本番 DB と分離された paper_trading DB に記録
  - 起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）と OrderManager による発注フロー
- Monitoring（run_monitoring.py / MonitoringEngine）
  - System / Trade / Risk の各監視を定期実行し、monitoring DB（SQLite）へログ記録
  - KillSwitch（条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止を誘発）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボードで監視情報を可視化
- Portfolio ユーティリティ
  - 候補選定、重み計算（等配分・スコア加重）、ポジションサイズ計算（単元丸めと aggregate cap）
  - セクター制約・レジーム乗数の適用
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- AI
  - OpenAI を使ったニュースセンチメント（ai/news_nlp.py）と市場レジーム判定（ai/regime_detector.py）
  - API 呼び出しはリトライ・バリデーション・フェイルセーフ実装

前提・依存
-----------
主な依存ライブラリ（抜粋）:
- Python >= 3.10（型ヒントや | 演算子を使用）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）

環境に応じて requirements.txt を用意しているなら pip install -r requirements.txt を使用してください。無ければ上記パッケージを個別にインストールしてください。

セットアップ手順
---------------
1. リポジトリをチェックアウト:
   - git clone ... && cd <repo>

2. 仮想環境と依存インストール（例）:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install pip --upgrade
   - pip install duckdb psutil requests openai streamlit

3. 環境変数 (.env)
   - プロジェクトルートに .env（または .env.local）を置くことで自動読み込みされます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading モード用 DB、デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant|partial|never|reject、デフォルト instant）
     - LOG_LEVEL（DEBUG/INFO/...）
   - .env が存在しない場合 config.Settings._require を通じて必須項目が未設定だと起動時に ValueError が発生します。 .env.example を参照してください（リポジトリにあれば）。

ファイル・フラグ関連
- data/execution.pid: ExecutionEngine が起動時に書き込む PID（監視側でプロセス存在チェックに使用）
- data/stop_requested.flag: run_monitoring/run_execution の外部停止用フラグ（存在を検知するとループを止める）
- data/kill.flag: KillSwitch が書き込む停止要求（ExecutionEngine に対して停止シグナルを送る）

使い方
------

1) 監視ループを起動（Monitoring）
- デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（1秒以上）。
- コマンド（プロジェクトルートから）:
  - python -m kabusys.run_monitoring
- run_monitoring は Settings から sqlite_path を読み取り、監視用 DB に接続して SystemMonitor のポーリングを行います（KABUSYS_ENV に関係なく本番 sqlite_path を使用）。

2) ExecutionEngine を起動（取引実行）
- KABUSYS_ENV によって挙動が変わります:
  - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と完全分離）
  - live / development: 通常のブローカークライアントを使用（KABU_API_PASSWORD 等が必要）
- コマンド:
  - python -m kabusys.run_execution
- 実行中は data/execution.pid が書き込まれ、監視側でプロセスが生存しているか判定されます。data/stop_requested.flag の存在で安全に停止します。

3) Streamlit ダッシュボード
- 監視 DB を読み取り専用で開いてダッシュボードを提供します（MonitoringEngine を先に起動してデータを生成しておく必要があります）。
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
- paper_trading 用 DB から検証レポートを生成します。
- 例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別パス指定可能（優先順: --db > PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

5) AI 系機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY が必要です。環境変数か引数で渡してください。
- ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
- 実行時は DuckDB 接続（prices_daily / raw_news 等のテーブルが必要）を渡して使います。
- API 呼び出しはリトライ・バリデーション・スコアクリップが組み込まれています。API 失敗時はフェイルセーフにより部分的にスキップまたはデフォルト値（例 macro_sentiment=0.0）で続行します。

重要な設定と振る舞い
------------------
- 自動 .env ロード:
  - OS 環境変数 > .env.local > .env の順で読み込み（ただし既存 OS 環境変数は保護される）。
  - _find_project_root() により .git または pyproject.toml を基準にプロジェクトルートを検出。配布後も動作するように設計。
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒で指定。1 未満や不正値はデフォルト 60 秒にフォールバック。
- PAPER_TRADING:
  - paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使い、本番DBと分離。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御（instant, partial, never, reject）。
- プロセス優先度:
  - run_monitoring/run_execution 起動時に set_process_priority("high") を呼ぶ（psutil を使い OS に依存した設定を試みる。権限不足等で失敗しても警告でスキップ）。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py (パッケージ定義, __version__)
- config.py (Settings: 環境変数 & .env ロードロジック)
- run_monitoring.py (監視ループ起動スクリプト)
- run_execution.py (ExecutionEngine 起動スクリプト)

サブパッケージ・主要ファイル:
- monitoring/
  - monitoring_db.py (SQLite テーブル初期化・読み書き: MonitoringDB)
  - system_monitor.py (SystemMonitor)
  - trade_monitor.py (TradeMonitor)
  - risk_monitor.py (RiskMonitor)
  - kill_switch.py (KillSwitch)
  - alert_manager.py (LINE 通知)
  - monitoring_engine.py (MonitoringEngine)
  - streamlit_dashboard.py (可視化)
- execution/
  - execution_engine.py (エンジン本体; 起動スクリプトから利用)
  - order_manager.py (OrderManager)
  - order_repository.py (SQLite ベースの発注 DB)
  - reconciler.py (起動時の再同期)
  - broker_factory.py / broker_api.py (ブローカークライアント抽象)
- portfolio/
  - portfolio_builder.py (候補選定・重み)
  - position_sizing.py (株数決定)
  - risk_adjustment.py (セクター上限・レジーム乗数)
- research/
  - factor_research.py (ファクター計算: momentum/volatility/value)
  - feature_exploration.py (将来リターン・IC・統計)
- ai/
  - news_nlp.py (ニュースのセンチメントスコアリング)
  - regime_detector.py (市場レジーム判定)
- tools/
  - paper_verification_report.py (paper_trading 検証レポート)
- utils/
  - process_priority.py (優先度・CPU affinity ユーティリティ)
- data/ (想定されるデータファイル・フラグ)
  - monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, stop_requested.flag, kill.flag, ...

運用上の注意
------------
- 本リポジトリ内のコードは取引システムの基盤を提供しますが、本番運用前に十分なテスト（特にブローカークライアント周り・リスク制御）を行ってください。
- AI モジュールは外部 API（OpenAI）に依存します。API 呼び出しにはレート制限やエラーが発生するため、ログとリトライ挙動を確認した上で運用してください。
- データファイル（SQLite / DuckDB）は適切な権限のあるディレクトリに置き、運用時はバックアップやローテーションを検討してください。
- kill.flag / stop_requested.flag を用いた外部停止や再起動運用のプロセスを確立してください。kill.flag は KillSwitch により作成され、ExecutionEngine 側で停止をトリガーします。

貢献 / 開発
-----------
- パッチや改善提案は Pull Request を歓迎します。ユニットテスト、型注釈の整備、CI の追加を推奨します。
- 新しい外部依存を追加する際は requirements.txt を更新してください。

ライセンス
---------
- このリポジトリに明示的なライセンスファイルがある場合はそちらに従ってください（ここでは明記していません）。

最後に
-----
この README はコードベースの主要構成・起動手順・運用上のポイントを簡潔にまとめたものです。疑問点や具体的な実行例が必要であれば、どのコンポーネントについて詳しく知りたいか教えてください。