README — KabuSys（日本株自動売買システム）
======================================

概要
----
KabuSys は日本株向けの自動売買／調査／監視用ライブラリ群と実行エンジンです。本コードベースは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- Paper Trading 環境の分離（専用 SQLite DB）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限）
- 研究用モジュール（ファクター計算・将来リターン・IC 計算など）
- ニュース NLP を使った銘柄センチメント（OpenAI を利用）
- Streamlit ダッシュボード、検証レポート生成ツール 等

特徴一覧
---------
主な機能（抜粋）:

- Execution
  - Broker 抽象化（実取引 / モック切替）
  - Order state machine、重複検出、再起動時リコンシリエーション
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring
  - 定期的にシステム／注文状態を記録しアラート生成
  - KillSwitch によるフラグファイル方式の緊急停止
  - LINE Push を使った通知（AlertManager）
  - SQLite に永続化（monitoring.db）
  - Streamlit ダッシュボードで可視化
- Portfolio
  - シグナルをもとに候補選定、等重・スコア重み・リスクベースの発注株数算出
  - セクター集中制限・レジーム乗数
- Research
  - DuckDB を利用したファクター算出（momentum / value / volatility）
  - 将来リターン、IC 計算、特徴量サマリ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini 等）でスコアリングし ai_scores に保存
  - 市場レジーム判定（ETF MA + マクロニュースに基づく合成スコア）

セットアップ手順
----------------

前提
- Python 3.10+（型ヒントに対応したバージョンを推奨）
- SQLite は標準ライブラリで利用可能
- システムにより追加の OS パッケージが必要になる場合があります（例: Linux での psutil 用のビルドツール等）

必須 Python パッケージ（例）
- duckdb
- psutil
- requests
- openai (AI 機能を使う場合)
- streamlit (ダッシュボード使用時)

インストール例（仮の requirements がない場合の手動インストール例）:
- pip install duckdb psutil requests openai streamlit

データディレクトリ作成:
- プロジェクトルートに data/ ディレクトリを作成します（DB やフラグファイルがここに作られます）。
  - mkdir -p data

環境変数 / .env
- 環境変数から設定を読み込みます。プロジェクトルートに .env / .env.local を置けます（自動ロードされます）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須：該当機能使用時）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須：実取引時）
  - OPENAI_API_KEY — OpenAI（AI 機能使用時）
  - KABUSYS_ENV — 動作環境（development / paper_trading / live）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（paper_trading 時に使用）
  - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止関連）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

初期 DB 作成
- 監視テーブルは run_monitoring / run_execution 起動時に自動で init_monitoring_db が実行され、必要テーブルが作成されます。

使い方
------

起動コマンド（モジュール実行）
- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でループの待ち時間(秒)を上書きできます（デフォルト 60s）。
  - 監視は KABUSYS_ENV に依らず production の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループは次回チェック時に終了します。

- ExecutionEngine を起動（取引エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db） に記録します（本番 DB と完全分離）。
  - 実行中にプロジェクトルート/data/stop_requested.flag を作成するとエンジンは停止します。
  - ExecutionEngine の PID は data/execution.pid（デフォルト）に書き込まれます。SystemMonitor はこの PID を確認してプロセス生存を監視します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開き、Positions / Orders / System / Overview を可視化します。

ツール
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を表示し PASS/FAIL 判定を行います。

AI / レジーム判定
- ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、target_date のニュースウィンドウに基づき ai_scores テーブルへ書き込みます。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で与えます。
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込みます。

監視・停止フロー（概念）
- Monitoring が system_status を定期記録。
- TradeMonitor / RiskMonitor が問題を検出すると risk_logs に記録し、KillSwitch の評価により data/kill.flag を作成する場合があります（Execution 停止を要求）。
- KillSwitch の書き込みは冪等です（既に存在する場合は上書きしません）。
- ExecutionEngine 起動時には kill.flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START）があります。

重要な実装ノート（運用時の注意）
- Settings は .env / .env.local / OS 環境変数を自動で読み込みます（プロジェクトルートを .git または pyproject.toml で検出）。
- Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用します。Execution は paper_trading では別 DB を使用します。
- process priority / CPU affinity は psutil を通じて設定されます。権限不足で失敗する場合は警告で続行します。
- OpenAI を使う処理は API 呼び出し時にエラーハンドリングと指数バックオフが組み込まれており、失敗時は安全側のフォールバック（0 相当）で継続します。

ディレクトリ構成
----------------
（主要なファイルと説明。src/kabusys/ 以下を中心に記述）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み、検証）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine（取引エンジン）起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — マーケットレジーム判定とテーブル書き込み
  - monitoring/
    - monitoring_db.py — SQLite 接続／テーブル初期化・読み書きラッパ
    - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / PID チェック
    - trade_monitor.py — 滞留注文 / 約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知実装
    - monitoring_engine.py — 各 Monitor を束ねてポーリング
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注の外向け API（OrderState 管理）
    - reconciler.py — 起動時のブローカー照合・ポジション照合
    - （他：broker_factory, execution_engine, order_repository 等が想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility などのファクター算出
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - data/ （実行時に生成されることが多い）
    - monitoring.db（デフォルト）
    - kabusys.duckdb（デフォルト）
    - paper_trading.db（paper_trading 用）
    - stop_requested.flag / kill.flag / execution.pid など

運用例（簡易）
--------------
1. data ディレクトリ作成:
   - mkdir -p data

2. .env を準備（最低限必要な値は Settings のプロパティ参照）
   - 例: .env に KABUSYS_ENV=development を書く

3. 監視を起動（バックグラウンドや systemd を利用して常時実行）
   - python -m kabusys.run_monitoring &

4. Execution を起動（別プロセスで）
   - python -m kabusys.run_execution &

5. Streamlit ダッシュボード（任意）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

トラブルシューティング（よくある点）
-----------------------------------
- .env が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートが .git または pyproject.toml で特定できないと自動ロードはスキップされます
- OpenAI API エラー:
  - OPENAI_API_KEY が正しく設定されているか、レート制限がかかっていないか確認
- psutil による優先度・affinity 設定で権限エラーが出る:
  - 無視して続行されるので、必要なら実行権限（sudo 等）で起動するか該当機能を使わないでください

ライセンス / 貢献
-----------------
- 本 README 内ではライセンス表記は省略しています。実プロジェクトで利用する場合は適切に LICENSE を配置してください。
- コード改善やテスト追加などの貢献は歓迎します。まずは Issue を立ててください。

付録：よく使う設定（サンプル .env）
---------------------------------
例（プロジェクトルート/.env）:
- KABUSYS_ENV=development
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- LOG_LEVEL=INFO
- MONITOR_POLL_INTERVAL=60

以上。セットアップや実行に関して不明点があれば、使用したい機能（例：Paper Trading レポート、AI スコアリング、Streamlit ダッシュボード等）を教えてください。具体的な実行例や .env のテンプレートを追加で提供します。