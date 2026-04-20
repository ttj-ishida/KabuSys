README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究ツール群です。本リポジトリは以下の機能群を持ち、実運用向けの設計（ログ・監視・Kill Switch・ペーパートレード分離など）を備えています。

主な特徴
- 実行エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- Paper Trading（テスト口座）を本番 DB と分離して安全にテスト可能
- DuckDB を用いた研究用データ操作（ファクター計算・特徴量解析）
- ニュースの LLM（OpenAI）による NLP スコアリングと市場レジーム判定
- .env 対話式ウィザード、起動前設定検証ツール
- 監視ログ（SQLite）と永続化層、Kill Switch による自動停止
- Paper Trading 検証レポート生成ツール

機能一覧
- execution: 発注ロジック、ブローカークライアント抽象化、リスク管理
- monitoring: システム稼働監視、注文滞留・約定異常監視、リスク監視、Kill Switch、アラート送信
- portfolio: 候補選定、重み計算、ポジションサイジング、セクター調整
- research: DuckDB を使ったファクター計算・IC 分析・統計サマリ
- ai: ニュース NLP（OpenAI）による銘柄別スコア、レジーム判定
- tools: Paper Trading 検証レポート等のユーティリティ
- utils: ログ設定、プロセス優先度/CPU affinity 設定など

必要条件（代表）
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証を行う場合、任意）

セットアップ手順（開発環境）
1. リポジトリをクローンし、ルートに移動（pyproject.toml が存在する想定）。
2. 仮想環境を作成・アクティブ化:
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
3. 依存パッケージをインストール（必要に応じて調整）:
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトがパッケージ化されていれば）pip install -e .

設定 (.env)
- .env ファイルをプロジェクトルートに作成します。対話式ウィザードを利用すると便利です:
  - python -m kabusys.config_setup
- 生成後、設定を検証:
  - python -m kabusys.validate_config
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABUSYS_ENV: execution 環境（development / paper_trading / live）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

重要ファイル・フラグ
- 停止フラグ（監視/実行を外部から停止するため）
  - data/stop_requested.flag （run_monitoring/run_execution がチェック）
- Kill Switch（監視が書き込むと ExecutionEngine を停止させる）
  - data/kill.flag （KillSwitch が作成）
- PID ファイル
  - data/execution.pid（ExecutionEngine が使用するデフォルトパス）
- ログディレクトリ
  - デフォルト: logs/（kabusys.utils.logging_setup に従う）

使い方（代表的なコマンド）
- 実行前に PYTHONPATH を設定（開発環境で src 配下をパスに追加する場合）:
  - Unix/macOS: export PYTHONPATH=src
  - Windows (PowerShell): $env:PYTHONPATH="src"
  - もしくはパッケージとしてインストールして利用
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用する点に注意
- .env 対話式セットアップ:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- AI 関連（プログラム内 API 呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

挙動上の注意
- Monitoring はデフォルトで本番の sqlite_path（Settings.sqlite_path）を使用します。paper_trading 環境でも監視 DB は分離されません（設計上の仕様）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。
- OpenAI を使った機能は OPENAI_API_KEY の設定が必須です。API エラーは安全側（スコア 0.0 など）にフォールバックする実装が多いですが、キー未設定だと例外を投げる関数があります。
- ログは標準出力（stdout）と日次ローテートされたファイル（logs/<app_name>.log）に出力されます。LOG_DIR 環境変数で変更可能。
- プロセス優先度は起動時に "high" に設定されます（プラットフォームと権限に依存）。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/設定管理
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 起動前設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - execution/                — 実行関連コンポーネント（broker, engine, order_manager…）
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

開発・デバッグのヒント
- ログ出力を DEBUG にして詳細を追う:
  - export LOG_LEVEL=DEBUG
- .env の自動読み込みは Settings モジュールがプロジェクトルートを特定して行います。テストなどで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB/SQLite のファイルパスは環境変数で上書き可能です（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
- stop_requested.flag / kill.flag を手動で作成・削除することでプロセスのトリガー操作ができます（data/ 配下に作成）。

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定されています。

その他
- Yaml 設定検証は PyYAML がインストールされている場合に内容チェックを行います。未インストール時はファイル存在チェックのみ行います。
- コード内に多くの注釈（日本語コメント）があり設計意図や安全弁（フェイルオープン/フェイルセーフ）に関する説明が含まれます。リファレンスとして活用してください。

問題報告 / コントリビュート
- バグや改善提案は Issue を立ててください。Pull Request は歓迎します。

以上。必要であれば README の英語版、さらに詳しい運用手順（systemd ユニット例、Dockerfile、CI/CD など）も作成します。どの情報を優先的に追加しますか？