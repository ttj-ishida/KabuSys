KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買／研究／監視ツール群（KabuSys）の一部実装です。
README はコードベースから読み取れる主要な機能・使い方・セットアップ手順をまとめたものです。

重要な設計方針（要点）
- 環境依存の設定は .env ファイル／環境変数で管理（config モジュールが自動ロード）。
- 本番（live）とペーパートレード（paper_trading）で振る舞いを分離。paper_tradingでは MockBrokerClient を使い、専用 DB に記録する。
- DuckDB を分析用途に、SQLite を監視・発注履歴用途に利用。
- ロギングは共通ユーティリティで設定（日次ローテーション + コンソール出力）。
- OpenAI（LLM）を使ったニュース NLP / レジーム判定モジュールを含む（APIキー必須）。

主な機能一覧
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV により paper_trading 用の MockBroker を使用可能。
- 監視（モニタリング）
  - run_monitoring.py: SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL で間隔変更可能（デフォルト 60 秒）。
  - monitoring/*: system/trade/risk の各モニタ、監視 DB（SQLite）の永続化ロジック、Kill Switch（kill.flag）等。
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み計算、セクター制約、ポジションサイズ計算（単元丸め・リスク制限等）。
- 研究（Research）
  - research/*: ファクター計算（momentum/value/volatility 等）、将来リターン・IC 計算、統計サマリ。
- AI（LLM）関連
  - ai/news_nlp.py: raw_news を LLM（OpenAI）でスコアリングして ai_scores に書き込む。
  - ai/regime_detector.py: market_regime を LLM と ETF MA 乖離で判定して保存。
- ユーティリティ
  - utils/logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ローテート）。
  - utils/process_priority.py: プラットフォーム依存を吸収したプロセス優先度設定。
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート（稼働率、約定率、レイテンシなど）。
- 設定ヘルパー
  - config_setup.py: 対話式 .env 作成ウィザード。
  - validate_config.py: .env / config/*.yaml の事前検証 CLI。

セットアップ手順（開発者向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 環境の準備（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai
   - （オプション）PyYAML を入れると validate_config が YAML パース検証を行います:
     - pip install pyyaml

   （開発用に package を editable でインストールする場合）
   - pip install -e .

4. .env の初期作成
   - python -m kabusys.config_setup
     - 対話式に必要な環境変数を入力し .env を生成します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

5. DB / ディレクトリ
   - デフォルトの DB/ログディレクトリは project_root/data と project_root/logs。
   - 必要なディレクトリは自動作成される場合がありますが、権限に注意してください。

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 SQLite、Monitoring は常に本番 sqlite_path を参照）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- ログ / 動作
  - LOG_LEVEL: DEBUG/INFO/...
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY: ai.news_nlp / ai.regime_detector で使用
- Paper トレード挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）

使い方（コマンド例）
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録されます。
    - 起動時に data/stop_requested.flag（stop フラグ）があれば起動を行いません。
    - 実行中は data/execution.pid 等の PID ファイルを使用します。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒、デフォルト 60）。
    - 監視は Settings.sqlite_path（本番用）を使ってログを書き込みます。
    - 停止は data/stop_requested.flag を作成することで検出・終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 処理（コード呼び出し）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - target_date: date オブジェクト
    - api_key: None にすると環境変数 OPENAI_API_KEY を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

Kill Switch / 停止フロー
- KillSwitch は監視ロジックが DRAWDOWN やポジション上限等に達した場合 data/kill.flag を書き出します。ExecutionEngine はこのファイルを見て安全停止します。
- 手動停止（グレースフル）を要する場合は data/stop_requested.flag を作成してください（run_* スクリプトが検知して停止します）。

ログ
- setup_logging(app_name) を起動時に実行して、stdout と logs/<app_name>.log（日次ローテーション）へ出力します。
- ログ出力先は LOG_DIR または setup_logging の引数で変更可能。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照実装あり)
  - execution/                — Execution エンジン関連（BrokerFactory, OrderManager 等）
  - portfolio/                — portfolio_builder, risk_adjustment, position_sizing
  - research/                 — factor_research, feature_exploration
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 注意事項
- .env は絶対に Git にコミットしないでください（config_setup の出力にも注意書きあり）。
- Monitoring はコード内で「監視 DB は環境にかかわらず本番 sqlite_path を使用する」設計です。ペーパートレードの監視ログを分離したい場合は設定を見直してください。
- OpenAI を呼び出す処理は API エラーや JSON パース失敗に対してフェイルセーフな設計になっていますが、API キー管理や API 利用上限には注意してください。
- 実際の発注ロジック（ExecutionEngine / BrokerClient）を運用環境で使う場合は十分なテストとガード（Kill Switch、リスク設定、LINE 通知等）を設定してください。

問い合わせ・貢献
- 実装や CLI の改善提案、バグ修正、テスト追加等は Pull Request を送ってください。
- 大きな設計変更を行う場合は Issue で事前に議論をお願いします。

以上がこのコードベースの概要と主要な使い方です。必要であれば、特定モジュールの API 仕様や実行例（サンプル .env、CLI 実行ログ例、DuckDB / SQLite のスキーマ参照等）をさらに詳しく作成します。どの部分を深掘りしますか？