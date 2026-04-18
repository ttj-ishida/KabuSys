KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。
トレーディング・監視・研究・AI スコアリング・ペーパートレード用ユーティリティを含みます。
以下はコードベース（src/kabusys 以下）に基づく README です。

要約
----
- 言語: Python
- 目的: 日本株の自動売買（ExecutionEngine）、監視（Monitoring）、ファクター計算・研究、ニュースNLP/レジーム判定などの機能を提供するライブラリ群
- 設計方針の一部:
  - 環境変数と .env による設定管理（kabusys.config）
  - DuckDB を分析用途（prices_daily, raw_financials 等）に使用
  - SQLite を監視／取引ログ（monitoring.db / paper_trading.db）に使用
  - 本番/ペーパーを明確に分離（KABUSYS_ENV）
  - OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定をサポート（API キー必要）
  - ログは console + 日次ローテートファイル（logs/）へ出力

主な機能
--------
- 実行（Execution）
  - ExecutionEngine（run_execution.py）: ブローカー接続、注文管理、リスク管理、実行ループ
  - Paper Trading 時は MockBrokerClient を利用し、本番 DB と分離して data/paper_trading.db に記録
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - system_status / trade_logs / risk_logs / dashboard 等の永続化（SQLite）
  - Kill Switch（data/kill.flag）による安全停止
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算（等金額・スコア重み）、セクター上限適用、ポジションサイズ計算
- リサーチ（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC、統計サマリ等
  - DuckDB を用いた SQL ベースの処理
- AI（news_nlp / regime_detector）
  - ニュース記事のセンチメントを LLM（OpenAI）で評価し ai_scores に保存
  - ETF の MA200 とマクロニュースを合成して市場レジーム（bull/neutral/bear）を判定
- ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話的に生成
  - 設定検証ツール（validate_config.py）
  - ログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils.process_priority）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - requirements.txt が提供されている場合: pip install -r requirements.txt
   - 主に利用するライブラリ:
     - duckdb
     - psutil
     - openai
     - sqlite3（標準ライブラリ）
     - PyYAML（設定ファイル検証時に推奨）
   - 例（最低限）:
     - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照）
   - 重要環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - PAPER_FILL_MODE（instant/partial/never/reject、デフォルト: instant）
     - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険: 0 を推奨）

5. 設定の検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いにできます

使い方（主要スクリプト）
------------------------

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成／更新します

- 設定検証
  - python -m kabusys.validate_config
  - 設定ミスやファイルの有無を検出します

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
  - 監視は .env の KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視情報を一元化します
  - 監視を停止するにはプロジェクトルート/data/stop_requested.flag を作るか SIGINT (Ctrl+C)

- 実行エンジン起動 (ExecutionEngine)
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（プロダクションDBと分離）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に停止したい場合は data/stop_requested.flag を作成すると安全に停止します
  - 実行中の PID は data/execution.pid に書き込まれます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム判定・ニューススコア
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ（OpenAI API キーが必要）
  - 直接 CLI エントリは本リポジトリにはありませんが、ライブラリとしてインポートして利用可能

運用上の注意
------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は外部から ExecutionEngine に停止シグナルを送るための仕組みです。KillSwitch は監視コンポーネントがトリガーして書き込みます。
- 停止フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して停止します。
- ログ: デフォルト logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイル／ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／.env のロードと Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB スキーマとアクセス
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 管理
    - ... (trade_monitor, alert_manager 等)
  - execution/
    - execution_engine.py    — 実行エンジン（注文フロー）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - ...（実装はコードベース参照）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み
    - position_sizing.py     — 株数計算・資金配分・rounding
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ 等
    - feature_exploration.py — IC, 将来リターン, summary
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力スクリプト

開発・拡張のヒント
------------------
- DuckDB と SQLite を併用しています。分析用途は DuckDB、監視/ログは SQLite に保持する設計です。
- AI 関連は OpenAI SDK に依存します。API 呼び出し時のリトライやレスポンス検証を行う実装になっています。
- 重要なファイル（.env、data/*.db、logs/）は運用環境で適切に配置・バックアップしてください。
- 本番稼働前に python -m kabusys.validate_config を必ず実行して設定を確認してください。
- 単体テストやモックを使って OpenAI 呼び出しやブローカークライアントを差し替えられる設計になっています（テスト時は環境変数で自動ロードを無効化するなど可能）。

ライセンス・その他
-----------------
- 本リポジトリにライセンスファイルが含まれていればそちらを参照してください。
- セキュリティ上の秘密情報（API トークン等）は .env に保存し、アクセスを制限してください。

以上がこのコードベースの README です。必要であれば具体的な起動例（環境変数の例、systemd / Supervisor のユニット例、Docker 化手順など）も追加します。どの情報を追記しますか？