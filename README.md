README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ群・ユーティリティ群です。  
主な役割は以下です。

- 戦略・ポートフォリオ構築（ファクター計算、ポジションサイジング、リスク調整）
- 実行エンジン（ExecutionEngine）の起動補助とブローカラッパー（paper/live 切替）
- 監視（System / Trade / Risk の定期チェック）と Kill Switch
- AI 補助（ニュース NLP による銘柄別センチメント、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

本リポジトリはライブラリとしても、モジュール単位で CLI 的に実行して運用することも想定しています。

主な機能一覧
--------------
- 環境設定管理
  - .env/.env.local の自動ロード（必要に応じて無効化可）
  - config_setup.py による対話式 .env 作成ウィザード
  - validate_config.py による起動前チェック
- 実行コンポーネント
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading/live 切替）
    - paper_trading 時は MockBroker を使用して data/paper_trading.db に記録
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整可）
- 監視・アラート・Kill Switch
  - MonitoringDB（SQLite）による永続化（system_status / trade_logs / risk_logs / positions / dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch による data/kill.flag 作成で ExecutionEngine 停止指示
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、等金額・スコア加重ウェイト、スコアベース位置サイズ計算、単元丸め、セクター上限適用、レジーム乗数
- リサーチ
  - DuckDB を利用したファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン、IC、統計サマリ
- AI（OpenAI）
  - ニュースの銘柄別センチメント付与（gpt-4o-mini を想定）
  - ETF ベース + マクロニュースでの日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポート生成

セットアップ手順（開発 / 運用前準備）
-----------------------------------
以下は一般的なセットアップ手順の例です。プロジェクト実行環境に応じて適宜調整してください。

1. レポジトリを取得
   - git clone ... など

2. Python 仮想環境を用意（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 必須ライブラリの例（本コードで利用されている主なもの）:
     - duckdb, psutil, openai, (PyYAML は設定検証で任意), など

4. .env の作成
   - python -m kabusys.config_setup
     - 対話式ウィザードで .env を生成できます
   - または .env.example（存在する場合）を参考に編集してください
   - 自動ロードについて:
     - 本モジュールはプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env/.env.local を自動でロードします
     - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

5. 環境変数 / 必須設定（例）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 運用上よく使う:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
   - Paper trading 固有:
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

6. データディレクトリ
   - デフォルトでは data/ 以下に DB・pid・フラグ等を作成します。適宜パスを .env で変更してください。
   - logs/ はログ出力先（LOG_DIR で変更可）。

使い方（主なコマンド・実行方法）
-------------------------------

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - 生成後は python -m kabusys.validate_config で検証推奨

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動を行いません
    - 実行中は data/execution.pid に PID を書きます（PID ファイルパスは Settings.pid_file_path で変更可）
    - 終了は stop フラグ (data/stop_requested.flag) を書く、または KillSwitch による data/kill.flag により行われます

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）
  - 監視は本番用 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パスを指定できます。

- AI 機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日分のニュースをスコアして ai_scores テーブルに書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF (1321) の MA とマクロニュースを合成して market_regime テーブルに書き込む
  - いずれも OPENAI_API_KEY を設定するか api_key 引数で渡してください

停止・フラグの管理
-----------------
- stop_requested.flag
  - run_execution.py / run_monitoring.py は data/stop_requested.flag の存在を監視し、検出時に安全終了します
- kill.flag
  - KillSwitch（監視ロジック）が条件を満たすと data/kill.flag を作成し、ExecutionEngine に停止指示を送ります
  - Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag を自動クリアする動作を許可します（本番では 0 推奨）

ログ設定
--------
- ログは kabusys.utils.logging_setup.setup_logging を通じて初期化されます
- デフォルト: stdout 出力 + 日次ローテートで logs/<app_name>.log（30日保持）
- 環境変数:
  - LOG_LEVEL（デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
- 既存ハンドラはクリアして再設定するため、複数回初期化しても二重出力を避けます

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイル / ディレクトリを抜粋）

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証ツール
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py           — （trade 監視ロジック：本リポジトリに含まれる想定）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py           — （アラート送信ロジック：本リポジトリに含まれる想定）
  - execution/
    - execution_engine.py       — ExecutionEngine 本体（エンジンの起動・セッション管理）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/                        — デフォルトの DB/フラグが置かれる想定ディレクトリ（生成されます）

（上記は主要モジュールの一覧です。実際のファイル配置はリポジトリのルート構成をご確認ください。）

注意事項・運用上のヒント
-----------------------
- KABUSYS_ENV が "live" の場合、実際に発注が行われます。設定や認証情報は十分に確認してください。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- OpenAI API を使用する機能は API キーと利用料が必要です。失敗時はフェイルセーフ（多くの箇所で 0 やスキップ）を入れてありますが、運用前にテストしてください。
- monitoring と execution を同じホストで運用する場合、監視は常に production sqlite_path を参照する設計です（モニタは環境に関係なく本番 DB を監視する想定）。
- run_execution/run_monitoring の自動再起動は本リポジトリ外（systemd / supervisor / docker-compose 等）で管理するのが簡単です。

貢献・拡張
-----------
- 新しいストラテジーやブローカ実装は execution 以下にブローカファクトリ経由で追加してください。
- AI モデルやプロンプトの改善、再試行ロジックの調整は kabusys.ai 以下を編集してください。
- 設定値は config/*.yaml を用いる設計が含まれます（validate_config でチェック）。YAML を使う場合は PyYAML の導入を検討してください。

ライセンス・その他
------------------
- 本 README はコードベースに基づく説明です。詳細なライセンス条項・運用ポリシーがある場合はプロジェクトルートの LICENSE / docs を参照してください。

必要であれば、README にサンプル .env テンプレートや systemd ユニットファイルの例、Dockerfile / docker-compose の簡易例を追記できます。どの情報を追加しますか？