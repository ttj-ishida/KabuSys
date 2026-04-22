KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買フレームワーク（KabuSys）の一部実装です。  
本READMEはコードベースの使い方・セットアップ手順・主要コンポーネント構成を日本語でまとめたものです。

概要
----
KabuSys は次の主要機能で構成された自動売買 / リサーチ基盤です：

- 実行エンジン（ExecutionEngine）: ブローカーへ発注・約定管理・リスク管理を行う。
- 監視 (Monitoring): システム状態・注文・リスクをポーリングしてログ記録・アラート・Kill Switch を制御。
- ポートフォリオ構築（選定・配分・株数決定・リスク調整）の純粋関数群。
- リサーチ (research): DuckDB 上の価格・財務データからファクター計算や特徴量評価を行う。
- AIモジュール: OpenAI を用いたニュースのセンチメント評価（news_nlp）と市場レジーム判定（regime_detector）。
- ユーティリティ: .env 設定ウィザード、設定検証 CLI、ログ設定ユーティリティ、プロセス優先度設定 等。
- 運用ツール: ペーパートレード検証レポート生成スクリプト等。

機能一覧
--------
- 環境設定ウィザード（対話式 .env 作成・更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検査）: python -m kabusys.validate_config
- Execution 起動スクリプト（本番 / ペーパートレードを分離）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
- Monitoring 起動スクリプト（ポーリングループ）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に依存しない）
- 監視/永続化層: SQLite を用いた monitoring DB（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio: 候補選定、等重・スコア重み、リスク制御（セクターキャップ、レジーム乗数）、株数計算（単位丸め・集計上限）
- Research: DuckDB 接続を受けてモメンタム／ボラティリティ／バリュー等のファクターを計算、IC・統計解析
- AI: OpenAI を使ったニュースセンチメント（score_news）・レジームスコア（score_regime）。API 呼び出しは冗長性とパース検証を重視
- 運用ツール: Paper Trading 検証レポート生成スクリプト（期間指定可）

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（typing の | 記法、forward annotation を使用）
- Git、（任意）仮想環境の使用を推奨

1. リポジトリのクローン
   - git clone <repository-url>
   - cd <repository>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージのインストール
   - 主な依存:
     - duckdb
     - psutil
     - openai (AI機能を使う場合)
     - PyYAML（config/*.yaml をバリデーションする場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使用してください。なければ上記パッケージをインストール。）

4. 環境変数の設定 (.env の作成)
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、.env を編集して必要な値を設定してください（J-Quants トークン、kabu API パスワード等）。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前に --strict モードで警告も FAIL 扱いにして確認することを推奨:
     - python -m kabusys.validate_config --strict

主要環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live、デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 起動時に参照。デフォルト 60）

使い方（起動・ツール）
----------------------

ログ設定
- すべての起動スクリプトは内部で kabusys.utils.logging_setup.setup_logging を呼び出します。
- デフォルトのログディレクトリ: logs/
- 日次ローテーション・30日分保持

Execution エンジン起動
- 標準起動:
  - python -m kabusys.run_execution
- 起動時の振る舞い:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading.db に記録し本番 DB と分離
  - 起動時に data/execution.pid を作成（pid_file のパスは Settings で上書き可能）
  - data/stop_requested.flag が存在すれば起動をキャンセル

Monitoring 起動
- 標準起動:
  - python -m kabusys.run_monitoring
- 振る舞い:
  - Process 優先度を高に設定
  - SQLite の monitoring DB を初期化（init_monitoring_db）
  - duckdb 接続も開く（解析用）
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒、デフォルト 60）
  - 停止フラグファイル data/stop_requested.flag を検知するとループ終了

設定ウィザード
- python -m kabusys.config_setup
  - 対話式に .env を作成／更新します

設定検証
- python -m kabusys.validate_config [--strict]
  - 必須環境変数や config/*.yaml の存在／パースをチェックします
  - --strict: 警告があると exit code 1 にする

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH を参照、期間指定でペーパー取引の運用指標（稼働率、約定率、レイテンシ等）を出力

AI / プログラム API（簡易）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と対象日を渡してニュースセンチメントを ai_scores テーブルへ書き込む
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を計算して market_regime テーブルへ書き込む

注意点 / 運用上のポイント
- 本番環境 (KABUSYS_ENV=live) では kill/stop に関する設定を慎重に（KILL_FLAG_CLEAR_ON_START は 0 推奨）。
- Logging は stdout とファイル両方に出力。ログディレクトリ作成に失敗しても stdout は動作します。
- プロセス優先度の設定は psutil を使用。権限により設定できない場合は警告が出ます。
- ペーパートレードは実データベースと分離されるため、本番 DB を汚す心配はありません。
- OpenAI を用いる機能は外部 API の可用性やコストに注意してください。応答の検証・リトライロジックを組み込んでいますが、APIキーの設定が必須です。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要ファイル/モジュール構成の概観です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス、自動 .env 読み込みロジック
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 初期化と永続化ラッパ
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（存在）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各モニタ束ねるエンジン
    - alert_manager.py        — アラート通知（存在）
  - execution/
    - execution_engine.py     — ExecutionEngine（存在）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py

（注）上記のうち一部ファイルはこの README の元コードから抜粋して説明しています。実際のリポジトリには追加の実装ファイルやスクリプトが存在する可能性があります。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（ここには含まれていません）。
- 変更・貢献する際は既存テスト・スタイルに従い Pull Request を送ってください。

補足（よくある質問）
-------------------
- Q: 監視ループの間隔を変えたい
  - A: 環境変数 MONITOR_POLL_INTERVAL を秒数で設定してから run_monitoring を起動してください（例: export MONITOR_POLL_INTERVAL=30）。

- Q: ペーパートレードの DB を明示的に指定したい
  - A: 環境変数 PAPER_TRADING_SQLITE_PATH を設定するか、該当スクリプトのコマンドライン引数（ツール）で指定してください。

- Q: OpenAI API の呼び出しをテストで無効化したい
  - A: AI 機能は api_key が必須なので未設定にすることで実行しない、もしくは該当モジュールをモックしてください。

必要であれば、README にサンプル .env テンプレートや典型的な運用手順（systemd / cron による起動・ログローテーションの設定例）を追加できます。どの追加情報が欲しいか教えてください。