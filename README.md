# KabuSys

日本株向け自動売買システムのコードベース。  
このリポジトリは取引ロジック、ポートフォリオ構築、監視・アラート、研究用ファクター計算、そして一部 AI ベースのニュース解析を含むモジュール群で構成されています。

主な目的
- 日次のシグナルに基づく自動発注（ExecutionEngine）
- 実行状況・システム状態・リスクの監視（Monitoring）
- Paper Trading 用検証ツール（検証レポート生成）
- DuckDB を用いたファクター計算・研究モジュール
- OpenAI を利用したニュースセンチメント / レジーム判定（オプション）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 初期設定（.env ウィザード）
  - 設定検証
  - 実行エンジン起動
  - 監視ループ起動
  - Paper Trading 検証レポート
  - AI モジュール（ニュース／レジーム）
- 環境変数（主要項目）
- ファイル・ディレクトリ構成

---

プロジェクト概要
- 名前: KabuSys
- バージョン: 0.1.0（src/kabusys/__init__.py）
- 日本株自動売買のためのモジュール群。実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定。
- SQLite（監視用）と DuckDB（分析用）を併用するアーキテクチャ。

---

機能一覧
- ExecutionEngine（発注実行、リスク管理、注文管理、Reconciler 等）
  - paper_trading モード時は MockBrokerClient を使用し、本番 DB と分離（デフォルト data/paper_trading.db）。
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
  - システム稼働監視、データ鮮度チェック、滞留注文検出、ドローダウン監視、Kill Switch（flag ファイル）など。
- 設定管理ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証ツール（validate_config.py）
- 研究・ファクター計算（research）
  - モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上で計算
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、セクター制限、ポジションサイズ算出（単元丸め含む）
- AI モジュール（ai）
  - ニュースセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（ETF MA + マクロニュース + LLM）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ログ設定ユーティリティ（utils/logging_setup.py）
- プロセス優先度設定（utils/process_priority.py）

---

セットアップ手順（ローカル）
1. リポジトリをクローン／配置（パッケージは src/ 配下）
2. Python 3.9+ を用意
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - OpenAI クライアント（openai）を利用（AI 機能を使う場合）
   - PyYAML は config 検証で YAML パースを行う場合に必要
4. データ・ログディレクトリを作成（任意。コードは不足時に自動作成する箇所あり）
   - data/ （デフォルト DB・PID・フラグ保管）
   - logs/ （デフォルトログ出力）
5. 環境変数設定
   - .env を作成するか、環境変数を設定してください。
   - 自動ロードは既定で有効（プロジェクトルートで .env / .env.local を読み込み）
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨インストール例:
- pip install duckdb psutil openai PyYAML

---

使い方

1) 初期設定ウィザード（.env を対話形式で作成）
- コマンド:
  - python -m kabusys.config_setup
- 概要: J-Quants トークン、kabu API パスワード、DB パス、ログレベル等を対話式で入力し .env を生成します。
- 生成後は .env に機密情報が含まれるため Git 管理から除外してください。

2) 設定検証
- コマンド:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
- 機能: 必須環境変数、DB パスの親ディレクトリ、config/*.yaml の存在・パース等をチェックします。

3) 実行エンジン起動（ExecutionEngine）
- コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い paper_trading 用専用 SQLite（PAPER_TRADING_SQLITE_PATH で指定、デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に同フラグを作成すると安全に停止します。
  - 実行中は PID を data/execution.pid に書きます（設定で上書き可能）。

4) 監視ループ起動（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 挙動:
  - Monitoring は常に（KABUSYS_ENV に関係なく）本番 sqlite_path（デフォルト data/monitoring.db）を参照して監視ログを残します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒単位、デフォルト 60）
    - MONITOR_POLL_INTERVAL が不正な値（<=0 や非整数）の場合は 60 秒にフォールバック
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt（Ctrl+C）

5) Paper Trading 検証レポート生成
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で SQLite ファイルを明示するか、環境変数 PAPER_TRADING_SQLITE_PATH を利用
- 出力: 稼働率、注文成功率、送信率、レイテンシ等を標準出力に出力し PASS/FAIL 判定を行います。

6) AI モジュール（ニュースセンチメント / レジーム判定）
- 関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - OpenAI API キーが必要（api_key 引数 or OPENAI_API_KEY 環境変数）
  - API 呼び出しはリトライ/フェイルセーフ設計（失敗時は部分スキップやフォールバックを行う）
  - レスポンスの検証やスコアのクリップ（±1.0）等の安全対策あり

---

主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN:（必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD:（必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading のフィルモード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアする（0/1、本番は 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

例（.env の主要項目）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

※ .env.example を参考に .env を作成してください（config_setup で生成可能）。

---

運用に関するファイル / フラグ
- data/stop_requested.flag: これを作成すると run_monitoring/run_execution が安全に停止します。
- data/kill.flag: Kill Switch が発動した際に書き込まれるファイル。ExecutionEngine に停止シグナルを送るために使用。
- data/execution.pid（または Settings.pid_file_path で指定されたパス）: 実行エンジンの PID を書くファイル。
- logs/: ログファイルはデフォルト logs/<app_name>.log に日次ローテーションで保存。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み・Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite schema + DB ラッパー
    - system_monitor.py
    - trade_monitor.py       — （trade 監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（上記は主なファイル群。細かな実装は各モジュール参照）

---

開発・テストメモ
- DuckDB は分析用に使用。prices_daily / raw_financials / raw_news 等のテーブルを用意することで research / ai モジュールを動かせます。
- monitoring_db.init_monitoring_db() は冪等で SQLite に監視テーブルとインデックスを作成します。既存スキーマに対する簡易マイグレーション（列追加）ロジックも備えています。
- AI 関連は OpenAI のチャット API を利用するため API キーが必須。失敗時にはフォールバックが行われる設計ですが、API 利用コスト・レート制限に注意してください。
- process_priority.set_process_priority() はプラットフォーム差を吸収しますが、権限不足で失敗する場合は警告ログに留まります。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に探索します。プロジェクト配布後も正しく動作するよう設計されています。

---

トラブルシューティング（よくある点）
- .env の必須項目未設定で起動時に例外が出る場合は python -m kabusys.config_setup で .env を再生成し、python -m kabusys.validate_config で確認してください。
- Monitoring は常に本番用 monitoring.db を参照します（監視ログの一貫性確保のため）。
- Paper Trading と本番 DB は分離（PAPER_TRADING_SQLITE_PATH）されます。テスト時は paper_trading を利用してください。
- ログディレクトリ作成失敗時はコンソール（stdout）のみの出力になります。ディスクパーミッションを確認してください。

---

ライセンス・貢献
- 本 README ではライセンス情報を含めていません。実運用・配布時は LICENSE をリポジトリに追加してください。

---

以上。必要であれば README に含める実行例（環境変数を指定した systemd ユニット例 / Dockerfile / docker-compose.yml）や各モジュールの詳細 API リファレンスを追加できます。どの情報を追加しますか？