README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のコアライブラリです。  
このコードベースは以下の主要機能を提供します。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live切替対応）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（停止フラグによる安全停止）
- リスク監視（ドローダウン・ポジション上限など）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー）と特徴量解析
- ニュース NLP を使った AI スコアリング（OpenAI API 利用、部分失敗耐性あり）
- ペーパートレード用検証レポート出力ツール
- .env 対話式セットアップウィザードと設定検証ツール

主要な設計方針として、
- ルックアヘッドバイアスを避ける（date/datetime の扱いに注意）
- DB は DuckDB（分析）と SQLite（監視 / 発注履歴）を併用
- 本番 / ペーパートレード用 DB を分離
- OpenAI 呼び出しはフェイルセーフ（リトライ/フォールバック）で実装
があります。

主な機能一覧
--------------
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用し data/paper_trading.db に記録）
  - run_monitoring.py: SystemMonitor ポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI
  - Settings クラス: 環境変数の取得 / 検証（デフォルト値や整合性チェック）
- モニタリング
  - MonitoringEngine: 各 Monitor（System/Trade/Risk）を束ねる
  - SystemMonitor / TradeMonitor / RiskMonitor: 状態チェックと monitoring DB への永続化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - monitoring_db: SQLite スキーマ初期化と読み書きユーティリティ
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment: 候補選定・重み付け・株数算出・セクター制限 等
- リサーチ
  - research.factor_research: Momentum/Value/Volatility 等のファクター計算（DuckDB 使用）
  - research.feature_exploration: 将来リターン・IC・統計サマリー等
- AI 関連
  - ai.news_nlp: ニュースを集約して OpenAI に投げ、銘柄ごとにスコアを ai_scores に書き込む
  - ai.regime_detector: MA200 とマクロニュースで市場レジーム判定を行い market_regime に書き込む
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを出力

セットアップ手順
----------------
前提:
- Python 3.10 以上（| 型注釈などを使用）
- git リポジトリ（プロジェクトルートを自動検出するため .git または pyproject.toml があると便利）

1. 仮想環境と依存関係のインストール（例: pip）
   - 必須パッケージ（例）:
     - duckdb
     - psutil
     - openai
   - 任意（検証時に便利）:
     - PyYAML（config/*.yaml の内容検証に使用）
   例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai PyYAML

2. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example（存在する場合）を参照して .env を作成してください。

3. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

4. データディレクトリの準備（任意）
   - デフォルトで data/ や logs/ は起動時に自動作成されますが、パーミッション等を事前に確認してください。

主な環境変数（抜粋）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境 / 動作
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1、デフォルト: 0)

- DB 関連
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）

- AI / OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector が利用）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト: instant）

- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH: デフォルトは data/execution.pid / data/kill.flag

使い方（よく使うコマンド）
-------------------------
- 実行エンジンを起動（通常はサービス化して起動）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV に応じて paper_trading / live の挙動が変わります。paper_trading の場合は別 DB に記録します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書きできます（例: MONITOR_POLL_INTERVAL=30）

- .env を対話的に作成 / 更新
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ペーパートレード検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - ai.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止 / Kill Switch
------------------
- 実行エンジンの停止：
  - data/stop_requested.flag（run_execution/run_monitoring が監視している停止フラグ）を書き込むと安全に停止処理が行われます（ファイルの存在を確認して停止）。
- Kill Switch（自動停止）:
  - リスク条件（ドローダウン超過やポジション上限超過）を満たした場合、kill.flag（デフォルト: data/kill.flag）を生成して ExecutionEngine に停止シグナルを送ります。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- コンソール出力は stdout に出力されます。ログレベルは LOG_LEVEL で制御可能です。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要なモジュール構成の抜粋です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                # Settings / .env 自動読み込み
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - ... (trade_monitor, alert_manager 等)
  - execution/               # ExecutionEngine, OrderManager, BrokerFactory 等（省略）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項 / 運用上のヒント
-----------------------
- Settings は .env 自動読み込み機能を持ちます。テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は「監視専用 DB パス」を使用します（環境に関わらず Settings.sqlite_path を参照）。run_execution は paper_trading の場合に別 DB を使用します。
- process_priority の設定は psutil を使っており、権限不足により設定が失敗することがあります。その場合は警告が出てスキップされます。
- OpenAI を利用する関数は API 呼び出しの障害に対してリトライ／フォールバックを行いますが、API キーの管理には注意してください（環境変数 OPENAI_API_KEY を使用）。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定されています。

支援が必要な場合
----------------
- 初期セットアップや .env 設定で不明点があれば、validate_config を実行して出力されるエラー/警告を確認してください。  
- OpenAI 関連で問題が出る場合は OPENAI_API_KEY の有無とネットワーク接続を確認してください。

以上。必要があれば README に含めたい追加項目（例: systemd サービス定義例、docker-compose 例、より詳細な運用手順など）を教えてください。