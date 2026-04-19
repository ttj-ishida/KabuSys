KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムの参照実装（ライブラリ＋起動スクリプト群）です。  
主な機能はシグナル生成・ポートフォリオ構築・発注（実取引／ペーパートレード切替可）・監視・レポーティング・ニュース AI を使ったセンチメント評価などです。  
設計方針として、DuckDB を分析用 DB、SQLite を監視／注文履歴用 DB として使い、CLI で設定ウィザード・設定検証・ツール実行が可能です。

主な特徴（機能一覧）
-------------------
- Execution（ExecutionEngine）
  - 実際のブローカークライアントと接続して発注を行う（KABUSYS_ENV により Mock を使用可能）
  - Paper Trading（ペーパートレード）モードでは専用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離
  - リスク管理（Rate limit、最大ポジション比率、サーキットブレーカー等）
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard 等の永続化（SQLite）
  - Kill Switch（閾値超過時に data/kill.flag を書き込み ExecutionEngine 停止）
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重、リスク調整（セクター上限）、銘柄あたりの株数計算（単元丸め等）
- Research（研究用モジュール）
  - DuckDB を用いたファクター計算（モメンタム / ボラ / バリュー）
  - 将来リターン・IC（情報係数）計算、特徴量サマリ
- AI モジュール
  - ニュース記事を OpenAI（gpt-4o-mini など）でセンチメント評価し ai_scores に保存
  - 市場レジーム判定（ma200 とマクロニュースの LLM スコアを合成）
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- ユーティリティ
  - 環境設定ウィザード（.env の対話的生成）
  - 設定検証 CLI（.env と config/*.yaml の検査）
  - 統一的なログ設定（日次ローテート）／プロセス優先度設定

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必須パッケージをインストール
   - 必要な外部依存の例（プロジェクトの requirements.txt がある場合はそちらを使用してください）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML 検査を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env の作成（推奨: 対話式ウィザード）
   - 対話式で作る:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルート）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能を使う場合に必要）
   - 注意: .env は機密情報を含むため Git にコミットしないでください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. データディレクトリの準備
   - デフォルトの DB / PID / フラグファイルは data/ 配下に作られます。起動時に自動作成されますが、アクセス権やディスク容量は事前に確認してください。

使い方（起動／コマンド）
-----------------------

- ExecutionEngine（発注エンジン）起動
  - 本番 or ペーパーは KABUSYS_ENV によって切替
  - 実行:
    - python -m kabusys.run_execution
  - ペーパーのとき:
    - KABUSYS_ENV=paper_trading を .env に設定すると MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ保存します。

- Monitoring（監視）起動
  - ポーリングループを開始（デフォルト 60 秒間隔）
  - 実行:
    - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 停止 / Kill
  - 監視側または手動で Kill Switch を発動すると Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 起動中に停止します。
  - 停止要求（強制終了）ファイル: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します（プロセスに優雅に停止させるためのフラグ）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間や DB を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 依存する設定ファイル（config/*.yaml）を検証するためには PyYAML が必要です（インストール推奨）。

重要な環境変数
---------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
- 実行／運用関連
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading: Mock ブローカーを使用し本番 DB と分離
    - live: 本番
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector 等）で必要
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に data/kill.flag を自動クリアするか（0/1、本番は 0 推奨）

ログ / ファイル
---------------
- ログディレクトリ
  - デフォルト: logs/
  - 各アプリ（monitoring, execution 等）は logs/<app_name>.log に日次ローテートで出力（30日保持）
- PID / フラグ
  - data/execution.pid — ExecutionEngine の PID（デフォルトパス）
  - data/kill.flag — Kill Switch 発動時に理由を保存
  - data/stop_requested.flag — ループ停止要求（手動で作成すると run_* スクリプトが停止）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと説明（抜粋）:

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - config_setup.py — .env の対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- kabusys/execution/  — 発注エンジン関連（broker_factory, execution_engine, order_manager 等）
- kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル定義 / 永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — kill.flag を書くロジック
  - alert_manager.py — （アラート送信のラッピング）
- kabusys/portfolio/ — 候補選定・重み付け・ポジションサイズ計算・リスク調整
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/ — DuckDB を使ったファクター計算・統計解析
  - factor_research.py, feature_exploration.py
- kabusys/ai/
  - news_nlp.py — ニュースの LLM ベースセンチメントスコア算出と ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（ma200 + LLM マクロセンチメント）
- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール
- kabusys/utils/
  - logging_setup.py — 共通ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
-------------
- KABUSYS_ENV による DB 分離を必ず理解して運用してください。paper_trading は専用 DB に記録され、本番データと混ざりません。
- 本番（live）では LINE 通知用の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch の扱い（KILL_FLAG_CLEAR_ON_START=0 推奨）を慎重に確認してください（validate_config の live 向けチェック参照）。
- OpenAI API を用いる機能は API 負荷・コスト・レート制限に注意してください。API キーは安全に管理してください。
- SQLite / DuckDB のファイル権限、ディスク容量、ログローテーション先の容量を監視してください。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）や kill.flag を検知して優雅に停止する仕組みがあります。自動化スクリプトからの停止にはこれらを活用してください。

開発者向けメモ
---------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB の簡易マイグレーション（列追加）ロジックを含みます。
- AI 関連の API 呼び出し部分はリトライ・バックオフ・レスポンス検証を備え、失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: 0.1.0（kabusys.__version__）
- ライセンス情報等はリポジトリルートの LICENSE を参照してください（無ければプロジェクトの方針に従って追加してください）。

問題・拡張
---------
- 要望や不具合は Issue を立ててください。AI モジュールのモデル変更やトークン使用の最適化、銘柄別単元対応、より柔軟な手数料モデルなど拡張余地があります。

以上がこのコードベースの利用開始ガイドと主要説明です。必要に応じて README に含める実運用例（systemd ユニット例、Dockerfile、CI 設定など）を追記できます。追加で欲しい情報があれば教えてください。