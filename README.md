README
=====

概要
---
KabuSys は日本株向けの自動売買・リサーチ基盤の骨組みです。  
主な用途は次のとおりです。

- アルゴリズムに基づく銘柄選定・ポートフォリオ構築
- 発注エンジン（ExecutionEngine）による発注管理（paper_trading / live 切替）
- システム稼働監視（Monitoring）と自動 Kill Switch
- DuckDB を使った研究用ファクター計算 / 特徴量分析
- OpenAI を利用したニュース NLP（センチメント）や市場レジーム推定
- Paper Trading の検証レポート生成

主な設計方針:
- 環境設定は .env / 環境変数で管理（自動読み込みあり）
- Paper Trading は本番 DB と完全分離（data/paper_trading.db）
- DuckDB を使い分析処理をオンメモリで高速実行
- ロギングは統一的に設定（logs/ 日次ローテート）

機能一覧
--------
大きな機能群（モジュール）と役割:

- 設定管理
  - kabusys.config.Settings: 環境変数・.env 読み込みと型検証
  - config_setup: 対話式で .env を生成
  - validate_config: 起動前チェック（必須環境変数・ファイルの存在など）

- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading を分離）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録

- 監視 (monitoring)
  - monitoring_db: SQLite に監視関連テーブルを作成・操作
  - SystemMonitor / TradeMonitor / RiskMonitor: 各種監視ロジック
  - KillSwitch: リスク条件で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 複数モニタを束ねて定期実行、アラート通知連携

- 発注・実行 (execution)
  - ExecutionEngine, OrderManager, BrokerClientFactory, RiskManager, Reconciler 等（発注ロジック、リスク管理）
  - paper_trading モードでは MockBroker を使用し data/paper_trading.db に保存

- ポートフォリオ構築 (portfolio)
  - portfolio_builder: 候補選定・重み計算（等分配 / スコア加重）
  - position_sizing: 株数計算（lot 単位丸め、リスクベース等）
  - risk_adjustment: セクターキャップ・レジーム乗数

- リサーチ (research)
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン / IC / 統計サマリ等

- AI (ai)
  - news_nlp: raw_news をまとめて LLM に投げ、銘柄ごとにセンチメントを ai_scores に書き込み
  - regime_detector: ETF の MA200 とマクロニュースを LLM で評価し市場レジームを判定

- ユーティリティ
  - logging_setup: 一貫したログ出力（stdout + 日次ローテート file）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低依存例:
     - pip install duckdb psutil openai
     - （YAML ファイルの検証を使う場合）pip install PyYAML
   - 実プロジェクトでは requirements.txt があればそれを使用してください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルート）。例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...
   - 自動ロードの挙動:
     - デフォルトで .env は自動読み込みされます（プロジェクトルートが検出できる場合）。
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 初期ディレクトリ作成（必要に応じて）
   - data/ および logs/ は実行時に自動作成されますが、権限等で失敗する場合は手動作成してください。

使い方
------

各種 CLI / 実行コマンドの例。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いに:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - development: 発注なし（開発用）
    - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
    - live: 実注文を送信
  - 起動前に既に data/kill.flag があると起動しません。
  - 停止方法:
    - data/stop_requested.flag を作成すると run_execution が検出して実行中の Engine を停止します。
    - KillSwitch により data/kill.flag が書き込まれると停止シグナルとなります。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒
  - run_monitoring は本番 sqlite_path（Settings.sqlite_path）を常に使用して監視ログを残します。
  - 停止方法:
    - data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先される）

- AI / リサーチ機能（プログラム内呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.connect(...)）を引数として渡して使用します。
  - OpenAI API キーが必要（引数で渡すか OPENAI_API_KEY を環境変数で設定）

ログ・DB の既定値
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- ログディレクトリ: logs/
  - ログファイル名はアプリ名に応じて logs/<app_name>.log（例: logs/execution.log）
  - 日次ローテーションを標準実装（30日保持）

重要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（整数）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動読み込みを無効化

停止フラグ / Kill Switch
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py がポーリング中にこのファイルを検出すると安全に終了します（管理向けの停止フラグ）。
- data/kill.flag
  - KillSwitch が危険事象（例: 大きなドローダウンやポジション数上限超過）を検出するとこのファイルを書き込みます。
  - ExecutionEngine は起動時にこのフラグがあると起動を停止します。

ディレクトリ構成（主なファイル）
-------------------------------

リポジトリ内の主要なファイル・パッケージ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 読み込み・Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前チェック CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 連携）
    - regime_detector.py         — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — （アラート送信ロジック、実装あり）
  - execution/
    - execution_engine.py        — ExecutionEngine 本体（発注ループ）
    - order_manager.py
    - broker_factory.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 注意点
-------------
- .env は機密情報（API キー等）を含みます。絶対にリポジトリへコミットしないでください。
- PyYAML が無いと config/*.yaml の内容検証はスキップされます（validate_config が警告を出します）。
- OpenAI 呼び出しはレート制限や一時エラーに対するリトライロジックを持ちますが API キーの管理に注意してください。
- run_monitoring は MonitoringDB にログを永続化します。監視 DB は Settings.sqlite_path（デフォルト data/monitoring.db）です。
- paper_trading モードは本番 DB と分離するため、実運用時は必ず設定を確認してください（KABUSYS_ENV=live 時は特に注意）。

ライセンス・貢献
----------------
（この README の内容はコードベースの説明です。実プロジェクトでのライセンス表記や貢献方法が必要であればプロジェクトルートに LICENSE / CONTRIBUTING.md を追加してください。）

以上。必要であれば README に含めるサンプル .env のテンプレートや起動フロー図、より詳細なディレクトリツリーを追加します。どの情報を拡張したいか教えてください。