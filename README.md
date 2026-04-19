KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株の自動売買／運用支援を目的とした Python ベースのプロジェクトです。本リポジトリは下記の主要機能を持つモジュール群で構成されています：

- 実行エンジン（ExecutionEngine）: ブローカー接続、注文管理、リスク管理を行う。
- 監視（Monitoring）: システム稼働、注文状態、リスク（ドローダウン・ポジション上限）を定期監視してアラート／Kill Switch を発動。
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム補正など。
- 研究（Research）: ファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC 計算、統計サマリー。
- AI 支援（AI）: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）。
- ツール: ペーパートレードの検証レポート生成など。
- 設定サポート: .env 対話式ウィザード、設定検証 CLI。
- ユーティリティ: ロギング設定、プロセス優先度設定など。

主な設計方針
- 本番／ペーパートレードは DB を分離（実行は KABUSYS_ENV に応じて切替）。
- ルックアヘッドバイアス対策として日付取得を明示的パラメタ化している箇所がある（研究・AI モジュール）。
- フェイルセーフ：外部 API 失敗時は逸脱しないようフォールバックする設計。

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話式生成
- 設定検証: python -m kabusys.validate_config（--strict で警告も失敗扱い）
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔変更（デフォルト 60 秒）
  - 監視は本番の sqlite_path を使用（環境に依らず）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
  - --from / --to / --db オプションで期間と DB を指定可
- ポートフォリオ構築関数群:
  - 候補選定 (select_candidates)、等金額 / スコア重み (calc_equal_weights / calc_score_weights)
  - ポジションサイズ計算 (calc_position_sizes)
  - セクター上限適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)
- 研究用ファクター計算:
  - calc_momentum, calc_volatility, calc_value
  - 将来リターン calc_forward_returns、IC 計算 calc_ic、統計要約 factor_summary
- AI:
  - ニュース NLP スコアリング (news_nlp.score_news)
  - レジーム判定 (ai.regime_detector.score_regime)
- 監視永続化層（SQLite）: monitoring_db モジュール（system_status / trade_logs / positions / risk_logs / dashboard）
- ロギング設定ユーティリティ（stdout + 日次ローテートファイル）
- プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
1. リポジトリをクローンし、ワークディレクトリへ移動
   - （本 README はパッケージを src/ 配下に置く想定のコードベースに対応）

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須例（プロジェクトで利用されている外部ライブラリ）:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（config 検証で YAML をパースする場合）
   - インストール例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を利用してください（本コード例では明示的な requirements.txt は含まれていません）。

4. .env を作成
   - 対話式: python -m kabusys.config_setup
   - または .env.example を参照して手動作成
   - 主要環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR など

   - 自動 env ロードは kabusys.config 内で .env / .env.local を自動読み込みします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

基本的な使い方
--------------
1. 実行エンジン起動（本番／ペーパー切替）
   - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
   - ペーパートレード（DB 分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - （PAPER_TRADING_SQLITE_PATH を指定している場合はその DB に記録される）

   補足:
   - 実行エンジンは data/execution.pid に PID を書きます（Settings.pid_file_path で変更可）。
   - data/stop_requested.flag が存在すると起動せず、実行中に作成されると停止します。
   - Kill Switch（kill.flag）は監視モジュールからのシグナルでエンジン停止を誘発します（詳しくは下記 Kill Switch 参照）。

2. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で間隔秒を指定可能（例: MONITOR_POLL_INTERVAL=30）
   - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境にかかわらず本番 DB を参照する設計）。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

4. AI 機能
   - NEWS スコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - OpenAI API キーは OPENAI_API_KEY または引数で指定
   - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - API 呼び出しはリトライ・バックオフ処理を実装しているが、API キー未設定時はエラーとなる

5. Kill Switch / フラグファイル
   - kill.flag (デフォルト: data/kill.flag): 監視ロジックがリスク超過等を検出したときに記述され、ExecutionEngine の停止トリガーとして用いることを想定
   - stop_requested.flag (data/stop_requested.flag): 手動でプロセスを停止させたい場合に配置（run_monitoring / run_execution がチェック）
   - .env の KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアする（本番環境での設定は注意）

主要コマンドまとめ
-----------------
- .env の作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールと説明（抜粋）です：

- src/kabusys/
  - __init__.py                       — パッケージ定義（__version__）
  - config.py                         — 環境変数/.env の自動ロードと Settings クラス
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py    — ペーパートレード検証レポート
  - utils/
    - logging_setup.py                — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py             — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py                — SQLite 永続化層（system_status 等）
    - system_monitor.py               — システム状態 / データ鮮度監視
    - trade_monitor.py                — （注文監視ロジック: 省略: 実装あり想定）
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - kill_switch.py                  — フラグファイルによる停止処理
    - alert_manager.py                — （アラート通知: 省略: 実装あり想定）
    - monitoring_engine.py            — 各 Monitor をまとめてポーリング
  - execution/
    - execution_engine.py             — 実行エンジン本体（EngineConfig, run_session 等）
    - broker_factory.py               — ブローカークライアント生成（Mock/実ブローカー）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実装群
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                      — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py               — レジーム判定（MA + マクロセンチメント合成）
  - data/ (runtime に生成)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid などファイル

注意事項 / 運用上のヒント
------------------------
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知等の設定を整えてください。validate_config は live の注意喚起を行います。
- .env は決してコミットしないでください（README / .env.example のみを共有してください）。
- OpenAI を利用する機能は API キーの管理とコストに注意してください（呼び出し回数・モデル）。
- 監視は MONITOR_POLL_INTERVAL で間隔を制御します。0 や負の値は無効で、デフォルト 60 秒にフォールバックします。
- run_monitoring は監視用 DB（monitoring.db）を使用します。データベースのバックアップやローテーションを検討してください。
- paper_trading モードは「完全に」本番 DB と分離されています（paper_sqlite_path を使用）。ペーパートレード運用時の誤発注リスクは低減されますが、設定を十分確認してください。

補足（開発者向け）
-----------------
- ロギング: kabusys.utils.logging_setup.setup_logging(app_name="execution") を呼ぶと logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数や引数で変更可。
- プロセス優先度: 実行開始直後に set_process_priority("high") を呼ぶことで優先度を上げる処理が入っています。環境によっては権限不足で警告が出る場合があります。
- monitoring_db.init_monitoring_db は冪等マイグレーションを含みます（新カラム追加チェック等）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑制できます。

お問い合わせ・貢献
-----------------
バグ報告・機能改善・プルリクエストはリポジトリの Issue / PR を通してください。ドキュメントの追加やテストコードの整備は歓迎します。

以上。必要であれば README に含めるコマンド例や .env.example のテンプレートを追記します。どの項目を詳細化したいか教えてください。