KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。  
取引実行エンジン、監視・アラート、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI（ニュースセンチメント / レジーム判定）などを含みます。  
本リポジトリはビジネスロジックやユーティリティをモジュール毎に整理しており、実運用（live）／ペーパー取引（paper_trading）／開発（development）で挙動を切り替えられます。

主な機能
--------
- ExecutionEngine（発注・リスク管理・オーダー同期）
- Reconciler（再起動時の発注リコンシリエーション）
- OrderManager / OrderRepository（注文管理・永続化）
- Monitoring（システム状態・注文滞留・リスク監視、kill flag）
- AlertManager（LINE へプッシュ通知）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 向け検証レポート生成スクリプト
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・セクター制限）
- Research（ファクター計算、将来リターン・IC 計算、統計サマリ）
- AI：ニュースセンチメント（OpenAI）および市場レジーム判定（OpenAI + MA200）

前提条件（例）
--------------
- Python 3.9+ を想定
- 必要パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリ）
- OS によりプロセス優先度設定に管理者権限が必要な場合あり

セットアップ手順
----------------
1. リポジトリをクローン、ワークディレクトリへ移動:
   - git clone ... && cd <repo>

2. 仮想環境（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai requests streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数設定:
   - プロジェクトルートに .env / .env.local を配置して自動読み込み可能
   - 自動ロードを無効にしたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数とデフォルト
----------------------------
- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト data/kabusys.duckdb
- SQLITE_PATH: Monitoring DB パス — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — デフォルト data/paper_trading.db
- PID_FILE_PATH: ExecutionEngine の PID ファイル — デフォルト data/execution.pid
- KILL_FLAG_PATH: kill flag ファイル — デフォルト data/kill.flag
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動 ("instant" | "partial" | "never" | "reject"), デフォルト "instant"
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — デフォルト 60。無効値や 0 以下は 60 にフォールバック
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...） — デフォルト INFO

使い方（実行例）
----------------

1) 監視ループを起動
- 監視（SystemMonitor）単体の起動スクリプト:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能（秒）
  - 監視は Settings に関わらず sqlite_path（本番パス）を利用します

2) 実行エンジンを起動（ExecutionEngine）
- 本番 / 開発 / ペーパーを切り替える:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- paper_trading の場合は MockBrokerClient が使われ、出力 DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）で本番 DB と分離されます

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- データベースは読み取り専用 URI で開く（監視プロセスと共存可能）

4) Paper Trading 検証レポート
- 生成:
  - python -m kabusys.tools.paper_verification_report
  - 指定期間例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを --db で指定可能（優先度: --db > 環境変数 > デフォルト）

5) AI 機能
- ニュースセンチメント: kabusys.ai.score_news を呼ぶ（OpenAI API キー必要）
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ（OpenAI API キー必要）
- API 失敗時は安全にフォールバック（多くのケースで 0.0 を使用して継続）

監視・停止制御（kill flag / PID）
--------------------------------
- ExecutionEngine は起動時に PID を data/execution.pid に書き込みます（Settings.pid_file_path）
- Monitoring は stale PID（PID ファイル存在だがプロセス不在）を検出するとファイルを削除しアラートを記録
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを伝達（存在チェックで判定）
- Settings.kill_flag_clear_on_start を 1 にすると ExecutionEngine 起動時に kill.flag をクリア

ディレクトリ構成（要旨）
-----------------------
（src/kabusys 以下の主要ファイル / モジュール）
- src/kabusys/__init__.py
- src/kabusys/config.py                    — 環境変数/.env 読み込みと Settings
- src/kabusys/run_execution.py             — ExecutionEngine 起動スクリプト
- src/kabusys/run_monitoring.py            — SystemMonitor 起動スクリプト

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...（発注関連）
- src/kabusys/monitoring/
  - monitoring_db.py, system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, alert_manager.py, kill_switch.py
  - streamlit_dashboard.py
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- src/kabusys/research/
  - factor_research.py, feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py, regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py
- src/kabusys/utils/
  - process_priority.py
- その他: data/ 以下に DB ファイル（デフォルト）を置くことを想定

注意事項 / 開発メモ
------------------
- Settings はプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします。テストなどで自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MonitoringDB の初期化関数 init_monitoring_db は冪等であり、既存 DB に対するマイグレーション（カラム追加）ロジックを含みます。
- psutil によるプロセス優先度や CPU affinity の設定は権限により失敗することがあります（失敗時は警告ログを出してスキップ）。
- OpenAI 呼び出しは外部 API でありレート制限等が発生します。news_nlp / regime_detector はリトライ・フォールバックロジックを備えていますが、APIキーの配慮とレート管理を推奨します。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離するため、検証時に誤って本番 DB を更新しないよう注意してください。

貢献・拡張
----------
- 新しいブローカー実装は broker_factory を通じて追加可能
- ポートフォリオロジックや position sizing は純粋関数群として実装されているので、ユニットテストしやすく拡張しやすい設計です
- AI 関連の呼び出し部分はテスト容易性を考慮して分離されており、モック化が可能です

お問い合わせ
------------
コード内コメントや関数 docstring に設計意図・利用上の注意を詳述しています。具体的な使い方や拡張については該当モジュールの docstring を参照してください。

以上。必要であれば README にインストール用の requirements.txt サンプルや具体的な .env.example を追加できます。どの情報を追記したいか教えてください。