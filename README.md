KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株自動売買システム（KabuSys）のコアライブラリ群です。
この README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は日本株の自動売買エンジン（ExecutionEngine）とそれを支える監視・リスク管理・リサーチ・ポートフォリオ構築・AI（ニュース NLP / レジーム判定）モジュールを含むパッケージです。  
設計方針の一例：
- 本番用とペーパートレード（paper_trading）を分離（専用 SQLite を使用）。
- DuckDB を分析用 DB として利用。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / レジーム判定機能を提供（API キーは任意）。
- 監視コンポーネントはプロセス監視・データ鮮度確認・リスク（ドローダウン・ポジション数）監視・アラートに対応。

主な機能一覧
-----------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを環境変数で切替え
  - Broker クライアント抽象化（MockBrokerClient により paper_trading を完全分離）
  - Execution 用 PID ファイル管理、停止フラグ監視
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度監視）
  - TradeMonitor（発注ログ監視、滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション制限監視）
  - KillSwitch（条件により data/kill.flag を書いて ExecutionEngine を停止）
  - Monitoring DB 層（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
- Portfolio（portfolio パッケージ）
  - 候補選定、等重・スコア加重配分、ポジションサイジング、セクター上限適用、レジーム乗数
- Research（research パッケージ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）
- AI（ai パッケージ）
  - news_nlp: raw_news を集約して OpenAI でセンチメント評価 → ai_scores に保存
  - regime_detector: ETF MA 乖離とマクロニュースで市場レジームを判定し DB に保存
- ユーティリティ
  - ログ設定ユーティリティ（logging_setup）
  - プロセス優先度 / CPU affinity 設定（process_priority）
  - 環境設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------
1. Python 環境
   - Python 3.9+ を想定（使用ライブラリの互換性に注意）。
2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml
   - その他標準ライブラリ（sqlite3, logging 等）は不要
   - 実際のプロジェクトでは requirements.txt があればそれを使用してください。
3. .env の準備（環境変数）
   - 対話式ウィザード: python -m kabusys.config_setup
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
     - LOG_LEVEL など
   - ウィザードで .env を保存したら、設定検証を実行:
     - python -m kabusys.validate_config
     - --strict をつけると警告も失敗扱いになります
4. ディレクトリ作成（必要に応じて）
   - data/ （DB、フラグファイル、PID ファイル等を配置）
   - logs/ （ログ出力先。logging_setup が自動作成を試みますが権限等で失敗する場合があります）
5. OpenAI を利用する機能を使う場合
   - OPENAI_API_KEY を .env に設定するか、score_* 関数の引数で渡してください。

使い方（起動・ユーティリティ）
----------------------------
- ExecutionEngine 起動（デフォルト）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は専用ペーパーデータベース（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient が使われます。
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします（安全措置）。
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は設定値にかかわらず本番用 sqlite_path を使用して監視ログを永続化します（monitoring は運用側で集約するため）。
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラーとして扱う
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI / バッチ的な処理（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して呼び出す
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはスケジューラ（cron 等）から呼ぶ想定です。CLI ラッパーは用意されていませんが、必要なら簡単に作成できます。
- 停止 / Kill Switch
  - Monitoring の KillSwitch は監視条件（ドローダウン等）を満たすと data/kill.flag を書き込みます。ExecutionEngine 側は flag を検出して安全停止する仕様です。
  - 手動停止フラグ（実行スクリプト停止）: data/stop_requested.flag を作成すると run_execution / run_monitoring のループを抜けます。
  - PID ファイル: data/execution.pid にプロセス PID を書く仕組みがあります（実行時に確認されます）。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI を使う機能で必要（任意）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL, LOG_DIR など

注意点 / 運用上のヒント
---------------------
- .env は絶対にリポジトリにコミットしないでください（API キー・シークレットが含まれます）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch を自動クリアしない）。
- Monitoring は監視ログ保存のために常に本番 sqlite_path を用いる設計です（環境が paper_trading でも production monitoring DB を使う設計になっている点に注意）。
- OpenAI 等の外部 API 呼び出しはフェイルセーフ実装になっており、API エラー時はフォールバック動作（スコア 0.0 など）を行う場合があります。API 使用時はレート制限やコスト管理に注意してください。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定管理（自動 .env ロード）
- config_setup.py           — 対話式 .env ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

サブパッケージ（主な内容）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）によるセンチメント評価
  - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化 / DB API
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py        — trade_logs ベースの監視（滞留注文等）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py        — （アラート送信：LINE 等 - 実装依存）
- execution/
  - execution_engine.py     — 実際の発注セッションロジック（Engine）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/
  - pipeline.py             — データ取得/加工ユーティリティ（DuckDB連携）
  - stats.py                — z-score 等の統計ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

補足
----
- ソースには詳細なドキュメント文字列とログ出力が豊富に含まれており、関数毎に目的・引数・戻り値・フォールバック動作が説明されています。まずは config_setup → validate_config → run_monitoring / run_execution の順で環境を整え、ローカルで paper_trading モードでの動作確認を行うことを推奨します。
- 追加で CLI や systemd / supervisor / Docker 等の運用ラッパーを作ると運用が安定します。

必要であれば、README にサンプル .env のテンプレート（.env.example）や systemd ユニット例、Dockerfile / docker-compose の雛形、各コマンドの具体的なログ出力例などを追記します。どの情報を追加したいか教えてください。