README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
バックテストや研究用の DuckDB、監視・発注ログ用の SQLite、LLM を用いたニュース評価や市場レジーム判定などの機能を備え、実運用（live）とペーパートレード（paper_trading）を切り替えて利用できます。

主な設計方針
- モジュールは責務を明確に分離（監視 / 実行 / ポートフォリオ構築 / 研究 / AI）  
- 可能な限り副作用を抑え、純粋関数・冪等（idempotent）操作を採用  
- ルックアヘッドバイアス防止（日時の取得は呼び出し側で明示的に渡す等）  
- フェイルセーフ：API エラーや欠損データは安全にフォールバック

機能一覧
--------
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - paper_trading モードでは MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - プロセス優先度を high に設定して実行
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン（MonitoringEngine）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
  - 永続化用の SQLite スキーマとユーティリティ（monitoring_db）
  - run_monitoring スクリプト（src/kabusys/run_monitoring.py）でポーリング実行（間隔は MONITOR_POLL_INTERVAL）
- Portfolio Construction
  - 候補選定、重み計算、ポジションサイジング、セクターキャップ、レジーム乗数等の純粋関数群（kabusys.portfolio）
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、特徴量サマリー（kabusys.research）
- AI（LLM 統合）
  - ニュースのセンチメントスコアリング（kabusys.ai.news_nlp）
  - マクロ記事 + ETF MA による市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API（gpt-4o-mini を想定）を用いた解析・冪等書き込み
- ユーティリティ
  - .env 対話式生成ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - ロギング設定ユーティリティ、プロセス優先度設定ユーティリティなど

セットアップ手順
---------------
以下は一般的なセットアップ手順です。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 必須ライブラリ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証の YAML チェック用だが任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がない場合、上記を手動でインストールしてください。

4. 環境変数の準備 (.env)
   - 対話式ウィザードで .env を生成・更新できます:
     - python -m kabusys.config_setup
   - 主に必要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（代表例）
     - KABUSYS_ENV     : development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH     : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH     : 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（paper_trading モード）
     - LOG_LEVEL / LOG_DIR
     - OPENAI_API_KEY  : LLM 呼び出しに必要（news_nlp, regime_detector）
   - .env 作成後は設定検証:
     - python -m kabusys.validate_config
     - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict

5. ディレクトリ作成（必要に応じて）
   - data/ （DB、PID、フラグファイル保存用）
   - logs/（ログファイル保存用）

使い方（実行例）
----------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
    - Execution 起動前に stop_requested.flag がある場合は起動せず終了
    - 実行中に data/stop_requested.flag を作るとエンジンを停止

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
    - 監視は環境にかかわらず Settings.sqlite_path（本番パス）を使用してログを書き込む
    - data/stop_requested.flag が存在すると監視ループを終了

- Kill Switch の運用
  - KillSwitch は RiskMonitor 等の判定で data/kill.flag（Settings.kill_flag_path）を書き込む
  - ExecutionEngine は起動時に kill.flag を確認し、既存の場合は起動を抑止することが想定されています
  - 必要に応じて kill.flag を手動で削除して解除

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL（exit 1）扱い

ログ
---
- logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
- デフォルトログディレクトリ: logs/
- アプリ毎に logs/<app_name>.log（日次ローテーション・30日保持）
- LOG_DIR / LOG_LEVEL 環境変数で上書き可能

重要な挙動・注意点
-----------------
- run_monitoring は monitoring 用の SQLite（Settings.sqlite_path）を本番パスで常に使用します（KABUSYS_ENV に依存しません）。
- run_execution は paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- OpenAI API を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY を要求します。未設定だとエラーまたはフォールバック（モジュールによる）があります。
- process_priority: 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします。権限不足で設定できない場合は警告でスキップされます。
- kill.flag / stop_requested.flag / execution.pid 等は data/ 以下に作成されます。これらは運用フロー（停止・再起動）に使われますので取り扱いに注意してください。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 配下の主なファイルとディレクトリ（このリポジトリのスナップショットに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - config_setup.py          — .env 対話式作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — process 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py は参照されているがここでは省略)
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

補助情報（依存関係の目安）
------------------------
少なくとも以下のライブラリが必要／推奨されます:
- duckdb
- psutil
- openai
- PyYAML（設定検証で YAML 内容検査を行う場合）
- sqlite3 は標準ライブラリで利用可能

開発・運用時のヒント
-------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup が警告を出します）。
- 本番 (KABUSYS_ENV=live) に切り替える前に validate_config で警告・設定ミスがないか確認してください。
- Paper Trading を検証する際は tools/paper_verification_report.py で期間を限定してレポート出力すると便利です。
- LLM 呼び出しはレート制限や一時エラーに対してリトライ実装がありますが、API キーやコストに注意して運用してください。

ライセンス・貢献
----------------
（このリポジトリのライセンス情報がある場合はここに記載してください）

問い合わせ
---------
実装や設計に関する質問があれば、リポジトリの Issues または開発チームにお問い合わせください。

以上。README に記載してほしい追加項目（例: 実際のコマンド例、構成ファイルサンプル、運用手順）や、特定のファイルの詳細な説明が必要であれば教えてください。