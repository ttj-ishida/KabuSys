# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README。  
この README はコードベース（src/kabusys 以下）から抜粋した仕様・使い方・セットアップ手順を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存ライブラリ
- セットアップ手順
- 環境変数（主なもの）
- 起動・操作方法（実行スクリプト）
- よく使うユーティリティ（設定ウィザード / バリデータ / レポート）
- 停止 / Kill Switch について
- ディレクトリ構成（主要ファイル説明）

---

プロジェクト概要
- KabuSys は日本株の自動売買システム（研究 / シグナル生成 / ポートフォリオ構築 / 発注 / 監視）を目的としたコード群です。
- DuckDB を用いた時系列ファクター計算、SQLite を用いた監視・発注ログ、OpenAI を使ったニュース NLP（センチメント）評価などのコンポーネントを含みます。
- モジュールは「execution」（注文実行）と「monitoring」（稼働監視）を独立して起動できる設計です。ペーパートレード用に本番 DB とは独立した SQLite を使用する機能もあります。

主な機能一覧
- ファクター計算（research.calc_momentum / calc_volatility / calc_value）
- 特徴量解析（IC 計算、統計サマリ）
- ポートフォリオ構築（銘柄選定、等配分 / スコア重み、リスク考慮のポジションサイジング）
- ExecutionEngine（発注管理、リスク管理、整合性チェック）
- Monitoring（SystemMonitor, TradeMonitor, RiskMonitor による継続監視）
- Kill Switch（閾値を超えた場合に flag ファイルを書き ExecutionEngine を停止）
- AI 連携：ニュースの NLP スコアリング（OpenAI）、市場レジーム判定
- ユーティリティ：.env 作成ウィザード、設定検証 CLI、ペーパートレード検証レポート

必要条件 / 依存ライブラリ（代表例）
- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml の検証に使用）

※ requirements.txt はこのリポジトリに添付されていない可能性があります。上記パッケージを環境にインストールしてください。

セットアップ手順（ローカル開発向け）
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （検証用に）pip install pyyaml

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成してください（.env は絶対に Git にコミットしないでください）。

4. データディレクトリ等を作成（必要に応じて）
   - デフォルトでは data/ 以下にログ・DB ファイル等を置きます。自動的に作成される箇所もありますが、手動で準備しておくと権限問題が起きにくくなります。
   - 例: mkdir -p data logs

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

環境変数（主なもの）
- 必須（少なくとも以下は設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
    - paper_trading: MockBroker を用い、data/paper_trading.db を使用（本番 DB とは分離）
- DB / パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai/news_nlp や regime_detector 等で使用）
- その他
  - MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒）（デフォルト: 60）
  - PAPER_FILL_MODE — ペーパートレード時の fill モード（instant/partial/never/reject）

起動・操作方法（主要な実行スクリプト）
- ExecutionEngine（実売買 or paper）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
    - 実行中は PID ファイル（data/execution.pid）を作成します。
    - 停止は stop flag（後述）や kill.flag によって制御されます。

- Monitoring（継続監視）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒）。デフォルト 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
    - 停止は data/stop_requested.flag の作成で行います（ループが検出して終了）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - 対話形式で .env を作成・更新できます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD（レポート期間）
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定します。

停止 / Kill Switch / フラグファイル
- stop_requested.flag
  - run_execution.py / run_monitoring.py がループ内で存在をチェックするファイルです。存在させることで当該プロセスを優雅に停止させます。
  - 場所: プロジェクトルートの data/stop_requested.flag（スクリプト内での参照箇所を確認してください）。
- kill.flag
  - KillSwitch（monitoring/kill_switch.py）が閾値超過時に書き込むフラグです。ExecutionEngine は起動時にこのフラグを確認し、存在すれば起動を抑止します。
  - flag の生成は冪等（既に存在すれば書き換えなし）。
  - clear() で削除可能（ExecutionEngine 起動前にクリアするオプション設定 KILL_FLAG_CLEAR_ON_START あり）。
- PID ファイル
  - ExecutionEngine は起動時に pid ファイル（デフォルト data/execution.pid）を書きます。

ログ設定
- 共通のロギング初期化関数: kabusys.utils.logging_setup.setup_logging(app_name="execution" or "monitoring")
  - stdout へ出力する StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定します。
  - LOG_DIR 環境変数でログ保存先を指定できます。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作します。

設計上の注意点 / 挙動
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を検出）から .env と .env.local を自動読み込みします（OS 環境変数が優先されます）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Paper trading 分離:
  - KABUSYS_ENV=paper_trading の場合、発注処理は MockBroker を用い、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ完全分離して記録します。
- AI モジュール:
  - ai/news_nlp.py や ai/regime_detector.py は OpenAI API を使います。API キーは OPENAI_API_KEY で指定してください。API 呼び出しは冪等・リトライやフェイルセーフ処理を備えています（失敗時は部分的にスキップして継続する設計）。
- DB 初期化:
  - monitoring/monitoring_db.init_monitoring_db は必要なテーブルとインデックスを冪等に作成します。起動スクリプトは適宜これを呼んでから監視や発注処理を開始します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数読み込み / Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース文章を LLM でスコアリングし ai_scores に書き込む処理
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定（OpenAI 連携）
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py — 候補選定、重み算出
    - position_sizing.py — 株数計算、利用可能現金とのスケール調整
    - risk_adjustment.py — セクター上限、レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化（テーブル定義・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py — （注文）取引監視ロジック
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート通知の抽象（LINE など）
  - execution/ (発注関連)
    - execution_engine.py — 実際の ExecutionEngine 実装
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py — 発注管理・リスク管理等
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ群
  - data/ （実行時に作成するファイルや DB が入る想定）
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（ペーパートレード用）
    - kabusys.duckdb（DuckDB）
    - kill.flag / stop_requested.flag / execution.pid など

補足（運用上のポイント）
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 時に追加チェックを行います。
- Kill Switch の設定値やリスク閾値は config/*.yaml の execution_config や risk_config にある想定です。config/*.yaml がない場合はスクリプト生成ツールで雛形を作成できます（README のスクリプト参照）。
- Logging は共通関数で統一されているため、ログ出力先・レベルは環境変数で一括制御できます。
- OpenAI 連携はコストとレイテンシに注意し、API キーの管理を慎重に行ってください。

以上がこのコードベースの README 相当の概要です。詳細や運用ルールはプロジェクトの設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）や config/*.yaml を参照してください。必要なら README をさらに長文化して「起動例」「運用チェックリスト」「よくあるトラブル対処」などを追記できます。どれを優先して追記しましょうか？