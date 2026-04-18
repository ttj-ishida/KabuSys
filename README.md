KabuSys
=======

日本株自動売買システムのコアライブラリ／起動スクリプト群です。  
このリポジトリには、戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）および AI を使ったニュースセンチメント等のモジュールが含まれます。

概要
----
KabuSys は以下の責務を分離して持つモジュール群で構成されています。

- execution: 発注ロジック（Broker クライアント、OrderManager、ExecutionEngine、リスク管理）
- monitoring: システム稼働・注文状況・リスクのポーリング監視とアラート／Kill Switch
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制約等のポートフォリオ構築ユーティリティ
- research: DuckDB 上の市場データを使ったファクター計算・特徴量解析
- ai: OpenAI を用いたニュース NLP（センチメント）、市場レジーム判定
- utils: ロギング設定、プロセス優先度設定、設定読み込みユーティリティなど
- tools: ペーパートレード検証レポート生成などのスクリプト

主な機能
--------
- 環境設定ウィザードと検証
  - .env を対話式で生成 / 更新: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動スクリプト
  - Production / PaperTrading を切り替えられる ExecutionEngine 起動: python -m kabusys.run_execution
  - PaperTrading は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- 監視エンジン
  - SystemMonitor, TradeMonitor, RiskMonitor を結合したポーリング: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- AI サービス
  - ニュース記事を OpenAI でスコアリングして ai_scores に書き込む（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA に基づく市場レジーム判定（kabusys.ai.regime_detector）
- 研究・分析
  - DuckDB を前提にファクター計算（モメンタム、バリュー、ボラティリティ）や IC 計算
- ペーパートレード検証ツール
  - paper_verification_report による運用品質の Pass/Fail レポート生成

セットアップ手順
----------------

前提
- Python 3.9+（コードは typing や型ヒントを多用）を推奨
- duckdb, openai, psutil 等の外部パッケージが必要

推奨インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（簡易）
   - pip install duckdb openai psutil

   追加（開発・オプショナル）
   - pip install PyYAML  # validate_config の YAML 検査を有効化

3. データディレクトリ作成（デフォルト）
   - mkdir -p data logs

環境変数 / .env
- 主要な環境変数（.env に設定することを推奨）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - OPENAI_API_KEY （AI 機能利用時に必須）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
  - LOG_LEVEL（DEBUG|INFO|…、デフォルト INFO）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意。アラート送信用）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

- .env 作成支援:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

起動・使用方法
--------------

1) ExecutionEngine（発注エンジン）を起動
- デフォルト:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログを残します。
  - 起動時に data/stop_requested.flag が存在すれば起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます（設定で変更可）。
  - KILL スイッチ（data/kill.flag）により外部から安全に停止できます（KillSwitch ロジックに従う）。

2) Monitoring（監視）を起動
- python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で設定（デフォルト 60）
- 挙動:
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite（settings.sqlite_path）へ永続化
  - Process 停止、データ鮮度異常、滞留注文、ドローダウン等の監視を行い、Kill Switch を発動する可能性があります
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- 稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL 判定を出力

4) AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）
- 関数をライブラリから呼び出して使います（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
- API 呼び出しはリトライやフォールバックロジックを備えています（失敗時は安全にデフォルト動作）

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を利用
- デフォルト出力先:
  - コンソール (stdout)
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30 日保持）
- 環境変数 LOG_DIR でログディレクトリを変更可能

よく使うファイル / フラグ
- data/monitoring.db — 監視用 SQLite（デフォルト）
- data/paper_trading.db — ペーパートレード用 SQLite（paper_trading 時）
- data/kabusys.duckdb — DuckDB（データ分析用）
- data/kill.flag — Kill Switch（存在すると ExecutionEngine に停止シグナル）
- data/stop_requested.flag — 起動停止フラグ（run_* スクリプトが検知）
- data/execution.pid — ExecutionEngine PID（実行時に書き出し）

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュールとスクリプトです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化ラッパー
    - system_monitor.py
    - trade_monitor.py       — （実装あり）注文異常検知等
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
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
  - tools/
    - paper_verification_report.py

（この README はコードベースから主要部分を抜粋した概要を示しています。実装の細かい挙動や追加設定は各モジュールの docstring / ソースをご参照ください。）

トラブルシューティング / 注意点
-----------------------------
- OpenAI 関連機能を使用する場合は OPENAI_API_KEY が必須です。キー未設定時は ValueError が発生します（モジュール内で明示）。
- validate_config の YAML 検証は PyYAML が必要です。未インストールでも警告扱いでスキップされます。
- process priority の設定は OS に依存します。権限不足（psutil.AccessDenied）時は警告が出て動作は継続します。
- DuckDB / SQLite ファイルのパスは Settings（環境変数）で変更できます。デフォルトは data/ 以下です。
- 本番（KABUSYS_ENV=live）での運用時は KILL_FLAG_CLEAR_ON_START を 1 にしないよう注意してください（デフォルト 0 を推奨）。
- MONITOR_POLL_INTERVAL に 0 や負の値を指定すると無効になり、デフォルト 60 秒が使われます。

開発に貢献するには
------------------
- 新しい依存を追加したら README と requirements ファイル（存在する場合）を更新してください。
- tests/ があればユニットテストを追加してください（現在のコードは設計上テストが可能になっています）。
- ドキュメント化の不足箇所は各モジュールの docstring に追記してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報が必要な場合はリポジトリルートに LICENSE を追加してください。

以上。プロジェクト固有の運用手順や CI/CD、デプロイ手順があればこの README に追記してください。