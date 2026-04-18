# KabuSys

日本株自動売買システム「KabuSys」のリポジトリ用 README（日本語）

この README はリポジトリ内のコードベースに基づいて作成しています。実行方法、設定、ディレクトリ構成、主要コンポーネントの振る舞いをまとめています。

バージョン: 0.1.0 (src/kabusys/__init__.py)

---

概要
- KabuSys は日本株の自動売買・研究・監視機能を提供するモジュール群です。
- 主な機能：売買実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI を使ったセンチメント評価）、Paper Trading 用の検証ツールなど。
- 設定は環境変数（.env）で行い、DuckDB / SQLite をデータ永続化に使用します。ログはコンソール出力と日次ローテーションファイルに出力します。

主な機能一覧
- 実行:
  - run_execution.py：ExecutionEngine を起動。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、本番 DB と分離して `data/paper_trading.db` へ記録。
  - プロセス優先度を高く設定（psutil による）。
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御可能。
- 監視:
  - run_monitoring.py：SystemMonitor をポーリングしてシステム状態やデータ鮮度を記録。既定間隔 60 秒（環境変数で上書き可）。
  - MonitoringEngine：SystemMonitor, TradeMonitor, RiskMonitor を束ね、アラート & Kill Switch 判定を行う。
  - MonitoringDB：SQLite ベースの監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）。
- ポートフォリオ:
  - 銘柄選定、重み算出、ポジションサイズ算定、セクターキャップ、レジーム乗数など純粋関数群（副作用なし、メモリ内計算）。
- 研究:
  - DuckDB を活用したファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン計算、IC（Information Coefficient）など。
- AI:
  - news_nlp.py：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント → ai_scores テーブルへ保存。APIキーが必要。
  - regime_detector.py：ETF（1321）の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定し DB に書き込む。
- ツール:
  - paper_verification_report.py：Paper Trading DB を集計して検証レポートを生成（稼働率、注文成功率、レイテンシ等）。
- 設定関連:
  - config_setup.py：.env を対話式で生成・更新するウィザード。
  - validate_config.py：必須環境変数や config/*.yaml の存在・簡易検証を行う CLI。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - requirements ファイルがある場合はそれを使う（リポジトリに依存一覧がある想定）。
   - 主要な依存（コードで使用されている）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証時に任意で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env を作成（対話式ウィザード推奨）
   - 実行:
     - python -m kabusys.config_setup
   - ウィザードは .env（デフォルト）を生成します。必須項目は JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など。

4. 設定検証
   - 実行:
     - python -m kabusys.validate_config
   - 必須項目が欠けていたり、パスが不正なら警告/エラーが表示されます。
   - 厳格モード（警告を失敗扱い）:
     - python -m kabusys.validate_config --strict

5. DB ディレクトリ / ログディレクトリ作成
   - デフォルトのパスはプロジェクト下面の data/ と logs/。自動で作成される場合がありますが、必要に応じて手動で作成してください。

環境変数（主なもの）
- 必須（起動前に設定）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境・動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用しデータベースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - live: 本番モード（注意して設定）
  - LOG_LEVEL: DEBUG/INFO/...（ログレベル）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- DB/ファイルパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading 環境で使用）
  - PID_FILE_PATH: 実行エンジン PID ファイル path（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- AI
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必要
- 監視ポーリング間隔（monitoring）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。1未満や不正値はデフォルトにフォールバック。

基本的な使い方（起動コマンド）
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
    - エンジンは別スレッドで実行され、data/stop_requested.flag を作成すると停止をトリガーできます。
    - 実行開始時にプロセス優先度が "high" に設定されます（psutil が許可する場合）。
- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定。例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照（KABUSYS_ENV に依存せず）。
  - 停止は data/stop_requested.flag により検知して終了。
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは引数 --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

停止／Kill Switch
- kill.flag:
  - KillSwitch はリスク条件（ドローダウンやポジション上限）を満たすと設定された kill.flag ファイル（デフォルト data/kill.flag）を作成して ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に kill.flag を検査し、存在する場合は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアすることも可能だが本番では非推奨）。
- stop_requested.flag:
  - run_execution/run_monitoring は data/stop_requested.flag の存在をチェックし、発見時にクリーンに終了します。

ログ
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（アプリ名ごとにファイル名が生成される: execution.log, monitoring.log 等）。
- ログ出力の解決順:
  1. setup_logging の引数 level
  2. 環境変数 LOG_LEVEL
  3. デフォルト "INFO"
- ログディレクトリは LOG_DIR 環境変数で上書き可能。

DuckDB / SQLite
- DuckDB は分析用の大規模データ（prices_daily, raw_financials など）を扱う想定で使用。
  - デフォルト: data/kabusys.duckdb（環境変数 DUCKDB_PATH）
- SQLite は監視ログや発注ログ（paper_trading 用 DB を含む）を扱う。
  - 監視 DB（monitoring.db）デフォルト: data/monitoring.db（環境変数 SQLITE_PATH）
  - Paper trading DB デフォルト: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH）

注意点／設計方針（抜粋）
- ルックアヘッドバイアス回避: 日付関連処理は datetime.today()/date.today() に強く依存しない実装方針（関数引数で日付を明示的に受け取る）。
- フェイルセーフ: 外部 API（OpenAI 等）失敗時はフォールバック（0.0 等）で継続し、致命例外は抑制する設計が多い。
- 冪等性: DB 書き込みは可能な限り冪等に設計（例: market_regime の DELETE→INSERT、monitoring_db のテーブル作成は IF NOT EXISTS）。
- OS 補助: プロセス優先度や CPU affinity の設定はプラットフォーム差分を吸収（psutil を利用）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/ (上記)
  - execution/ (一部参照 - Execution 系の実装が実際に存在する想定: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager)

（注）この README はリポジトリの一部ソースをもとに作成しています。実際のファイル構成・機能はリモートの完全なリポジトリ内容と差異がある場合があります。

よく使うコマンドまとめ
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート／トラブルシュート（簡易）
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動ロードします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログファイルが作成されない:
  - LOG_DIR を確認。ログディレクトリが作成できない場合は標準出力のみになります（エラーが stderr に出ます）。
- OpenAI 関連の問題:
  - OPENAI_API_KEY を設定してください。API 呼び出しエラーはログに記録され、一定回数リトライした後フォールバックする実装です。

ライセンス / コントリビューション
- README には含まれていません。リポジトリの LICENSE ファイル・ CONTRIBUTING.md を参照してください（存在する場合）。

以上。README の内容に追記や修正が必要であれば、必要な点（たとえば実際の起動フロー、追加の環境変数、missing files など）を教えてください。