KabuSys — 日本株自動売買システム（簡易 README）
=====================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なシステム群です。  
主な機能は注文管理・実行エンジン、監視・アラート、ポートフォリオ構築ロジック、ファクター計算、ニュース NLP によるセンチメント評価などを備えます。  
コードはモジュール化されており、実稼働（live）、ペーパートレード（paper_trading）、開発（development）を環境変数で切り替え可能です。

主な特徴
--------
- ExecutionEngine：ブローカークライアント経由の発注・状態管理と再同期（Reconciler）
- モニタリング：システム状態・注文滞留・ドローダウン等の定期チェックとログ永続化（SQLite）
- Kill Switch：条件に応じて ExecutionEngine を安全に停止するフラグ機構
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ計算（等金額／スコア加重／リスクベース）
- 研究（research）：DuckDB を使ったファクター計算（Momentum/Value/Volatility）と特徴量評価
- AI（news_nlp / regime_detector）：OpenAI を使ったニュースセンチメントと市場レジーム判定
- ツール：Paper Trading の検証レポート生成、Streamlit ダッシュボード等
- ユーティリティ：プロセス優先度/CPU affinity 設定、環境変数ローディング等

動作要件（概略）
----------------
- Python 3.9+（typing 機能を利用）
- 外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワークアクセス（LINE通知 / OpenAI を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン／配置する。
2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）。
   - pip install duckdb psutil openai requests streamlit
   - （requirements.txt がある場合はそれを使用）
4. データディレクトリ準備：
   - data/ ディレクトリを作成。デフォルトで SQLite / DuckDB ファイルは data 以下に置かれます。
     - data/monitoring.db（監視ログ、デフォルト）
     - data/paper_trading.db（paper_trading 用、paper 環境で使用）
     - data/kabusys.duckdb（DuckDB）
5. 環境変数設定：
   - プロジェクトルートに .env / .env.local を置くことで自動ロード（デフォルト）されます。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
6. 必須の外部キー等（OpenAI 等）を設定：
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
   - JQUANTS_REFRESH_TOKEN: J-Quants API（研究用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（ブローカー接続）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）

主要な環境変数とデフォルト
--------------------------
- KABUSYS_ENV: 起動環境（development | paper_trading | live） デフォルト: development
- SQLITE_PATH: 監視 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）

使い方（主要スクリプト）
------------------------

1) 監視ループ（Monitoring）
- 目的: SystemMonitor を定期実行して system_status / risk_logs などに永続化
- 実行例:
  - python -m kabusys.run_monitoring
  - または python src/kabusys/run_monitoring.py
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
- 備考:
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視 DB は共通で運用）。

2) 実行エンジン（Execution）
- 目的: ブローカーへ発注を行う ExecutionEngine を起動
- 実行例:
  - python -m kabusys.run_execution
  - または python src/kabusys/run_execution.py
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を使用して本番 DB とは分離されます。
  - 起動時に stop flag（data/stop_requested.flag）があれば起動しません。
- 注意:
  - 実行中は data/execution.pid に PID を書き、停止は kill.flag や stop flag で制御します。

3) Streamlit ダッシュボード
- 目的: 監視 DB を可視化する簡易 UI
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードでは positions / recent orders / system status / risk logs 等を閲覧できます。

4) Paper Trading 検証レポート
- 目的: paper_trading DB のログから期間レポート（稼働率・注文成功率・レイテンシ等）を生成
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - 実行時オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH (PAPER_TRADING_SQLITE_PATH を代替)
- 出力: 標準出力に要約（PASS/FAIL 判定付き）

5) AI 関連（ニュース NLP / レジーム判定）
- 提供関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 必要: OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡すこと
- 動作: DuckDB の raw_news / news_symbols / prices_daily 等を参照してスコアを算出、結果をテーブルに書き込みます。
- 注意: API 呼び出しはリトライ・フェイルセーフ（失敗時はスコア 0 またはスキップ）を行いますが、API キーが必須です。

内部概要（コンポーネント）
-------------------------
- kabusys.config
  - .env 自動読み込み機構（.env / .env.local、OS環境変数を保護）
  - Settings クラス: 各種設定値の取得・バリデーション
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch
  - monitoring_db: SQLite スキーマ初期化・読み書き API（init_monitoring_db / MonitoringDB）
  - streamlit_dashboard: UI
- kabusys.execution
  - ExecutionEngine（起動・セッション管理）
  - OrderManager / OrderRepository / Reconciler / BrokerFactory 等（発注ロジックと再同期）
- kabusys.portfolio
  - portfolio_builder / position_sizing / risk_adjustment（候補選定・重み付け・株数決定・セクター制限）
- kabusys.research
  - factor_research: momentum / volatility / value のファクター計算（DuckDB 使用）
  - feature_exploration: 将来リターン計算、IC 計算など
- kabusys.ai
  - news_nlp: ニュース記事の集約→OpenAI でセンチメント計算→ai_scores へ書込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を判定
- kabusys.utils
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
- tools
  - paper_verification_report: Paper Trading の検証レポート生成

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                          — 環境変数 / Settings
- run_monitoring.py                  — SystemMonitor ポーリング起動スクリプト
- run_execution.py                   — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py              — 優先度 / affinity 設定
- monitoring/
  - monitoring_db.py                 — SQLite スキーマ + MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (他ファイル)
  - execution_engine.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- data/ (実行時に利用するファイル群・例)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid / kill.flag / stop_requested.flag
- tools/
  - paper_verification_report.py

運用上の注意
------------
- .env には機密情報（APIキー等）を含むため、リポジトリ管理下に置かないよう注意してください。
- 実稼働環境（live）での Execution 起動は十分なリスク管理を行ってください。RiskManager の設定（最大ポジション比率等）を確認してください。
- モジュールは外部 API（kabuステーション、OpenAI など）に依存します。これらの接続設定・キーの管理を適切に行ってください。
- monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（列追加等）を行いますが、重大なスキーマ変更は別途マイグレーションを設計してください。

トラブルシュート（簡易）
----------------------
- .env がロードされない / 設定が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。
  - プロジェクトルートの特定は .git または pyproject.toml を基準に行われます。
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY が正しく設定されているかを確認。
  - レート制限・一時エラーは内部でリトライしますが、失敗時はフォールバック挙動（スコア 0）があります。
- PID / stale PID:
  - system_monitor は execution.pid を参照してプロセス存在確認を行います。壊れた PID ファイルは自動削除されます。

ライセンス・貢献
----------------
- 本リポジトリにライセンス表記がある場合はそれに従ってください。貢献は PR ベースで受け付けます。

以上。必要に応じて README を拡張して、実際のインストール手順（requirements.txt / Dockerfile / systemd ユニット等）や詳細な設定例（.env.example）を追加することを推奨します。