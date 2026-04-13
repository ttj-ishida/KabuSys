KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群と運用用スクリプト群を含みます。
コードは Execution（発注）、Monitoring（監視）、Portfolio（銘柄選定・配分）、Research（ファクター計算・解析）、AI（ニュースセンチメント・レジーム判定）等の責務ごとに整理されています。

主な特徴
-------
- ExecutionEngine：ブローカーとの発注・状態遷移管理、リコンシリエーション機能（再起動後の同期）
- Monitoring：システム状態 / 注文滞留 / リスク（ドローダウン・ポジション上限）監視、LINE通知・kill flag機能、Streamlit ダッシュボード
- Portfolio construction：候補選定・重み付け・ポジションサイズ計算（等配分・スコア加重・リスクベース）
- Research：DuckDBを用いたファクター計算（Momentum / Volatility / Value）や特徴量解析ユーティリティ
- AI機能：OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）・市場レジーム判定（market_regime）
- Paper tradingモード：KABUSYS_ENV=paper_trading のときブローカー呼び出しをモック化し、paper_trading.db に記録して本番DBと分離
- 各種ユーティリティ：プロセス優先度設定・CPU affinity、環境変数読み込みロジック、DBマイグレーション（簡易）

動作要件
-------
- Python 3.10+（型注釈の union | 等を利用しているため）
- SQLite（組み込みモジュール）
- 推奨 Python パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- （任意）J-Quants / Kabuステーション の各種 API は実運用時に必要

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 代表的なインストール例:
     - pip install duckdb psutil requests openai streamlit
   - 実際は requirements.txt を用意している場合は pip install -r requirements.txt を使用してください。

3. 環境変数(.env) を用意
   - プロジェクトルート（.git や pyproject.toml がある階層）に .env または .env.local を置くと自動で読み込まれます（既存 OS 環境変数が優先）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須例（.env の最小例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...        # AI 機能を使う場合
     - KABUSYS_ENV=development  # development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
   - Settings クラス（kabusys.config.Settings）で参照するキーは上記のほかにもあります。未設定で必須の項目は起動時に例外になります。

4. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。事前に作成しておくと権限や場所の問題を回避できます。
   - 例: mkdir -p data

初期化（DB）
-------------
- Monitoring 用 SQLite DB のスキーマは起動時に自動で作成／マイグレーションされます（init_monitoring_db を実行）。
  - したがって明示的な初期化は不要です。最初の起動時に data/monitoring.db が生成されます（パスを変えた場合は環境変数で指定）。

実行方法（代表例）
-----------------
- ExecutionEngine（トレードエンジン）を起動
  - 簡易:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - 実運用（live）: KABUSYS_ENV=live python -m kabusys.run_execution
  - 備考:
    - paper_trading の場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録して本番 DB と分離されます。
    - Execution 起動時に pid ファイル（Settings.pid_file_path）が書き込まれます（monitoring はこれを検出してプロセス生存確認を行います）。
    - 起動時に set_process_priority("high") を試みます（psutil による優先度変更。権限不足時は警告で継続）。

- Monitoring（ポーリングループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 重要: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（意図的な設計）。

- Streamlit ダッシュボード（監視画面）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを蓄積してください。

- Paper Trading 検証レポート作成スクリプト
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB を指定できます（優先順: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）。

設定（主な環境変数）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: ブローカーはモック、DB は paper_sqlite_path（既定: data/paper_trading.db）
  - live: 本番ブローカークライアントを使う（要設定）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（上書き）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

設計上の注意点 / 運用メモ
------------------------
- Monitoring は常に本番 sqlite_path を参照する点に注意してください（意図的）。
- .env の読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行われます。テスト等で自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- init_monitoring_db() は冪等であり、必要なカラム追加（簡易マイグレーション）も含みます（例: dashboard.peak_value, trade_logs.latency_ms）。
- Process priority / CPU affinity の設定は psutil を使って行っています。プラットフォームや権限により設定できない場合は警告を出してスキップします。
- AI 系機能（news_nlp や regime_detector）は OpenAI を使います。API呼び出しの失敗時はフェイルセーフ（スコア0フォールバック、部分的にスキップ）となります。またルックアヘッドバイアスを防ぐ設計になっています（target_date を明示的に渡す等）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- run_execution.py — ExecutionEngine 起動スクリプト（CLIエントリ）
- run_monitoring.py — SystemMonitor 起動スクリプト（CLIエントリ）

サブパッケージ:
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...（発注・リコンシリエーション関連）
- monitoring/
  - monitoring_db.py — SQLite 永続化・ログAPI
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
  - monitoring_engine.py — 各モニタ統合ループ
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 書き込みロジック
  - streamlit_dashboard.py — 監視ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 銘柄選定・配分・リスク調整
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・解析
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + macro sentiment）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — paper trading 検証レポート生成スクリプト

テスト / 開発
--------------
- 各モジュールは依存を注入する設計（DuckDB 接続やブローカークライアント、OpenAI クライアントの注入）になっているため、ユニットテストでモックしやすい構造です。
- AI系の外部呼び出しは _call_openai_api 等を patch して置き換えることを想定しています。

よくある運用コマンド例
--------------------
- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（デフォルト 60s ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
-----------------
- 本 README はコードベースの主要機能と運用方法のサマリです。実装変更や拡張を行う場合は関連モジュール（特に execution/monitoring/ai）を参照してください。
- バグ報告・機能提案は Issue を立ててください。

以上。運用や導入で不明点があれば、どの点を詳しく知りたいか教えてください。必要であればサンプル .env.example を生成します。