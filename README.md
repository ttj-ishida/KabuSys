README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を想定した Python パッケージです。
本リポジトリは以下の主要コンポーネントを含みます。

- 発注エンジン実行スクリプト（ExecutionEngine）
- 監視プロセス（Monitoring）
- ポートフォリオ構築、ポジションサイズ計算、リスク調整の純粋関数群
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント / レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポートなど）

機能一覧
--------
主な機能は次のとおりです。

- ExecutionEngine の起動 / 停止管理（実運用・ペーパートレードの切替）
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、専用の paper_trading DB に記録
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）のポーリング
  - システム負荷・プロセス稼働・データ鮮度・ドローダウン・滞留注文などを監視
  - Kill Switch（条件を満たすと data/kill.flag に理由を書き込み ExecutionEngine を停止）
- ポートフォリオ構築ユーティリティ
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元株丸め、aggregate cap）
  - セクター集中制限適用、レジームに応じた乗数
- リサーチ / ファクター計算
  - Momentum, Volatility, Value などのファクターを DuckDB 上で計算
  - 将来リターン、IC（Spearman）や統計サマリ
- AI モジュール（OpenAI API を利用）
  - ニュースセンチメント（ai_scores）
  - マクロニュース + ETF MA によるレジーム判定（market_regime）
- 運用ツール
  - .env 対話式セットアップ（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート（tools.paper_verification_report）

前提 / 必要ライブラリ
--------------------
主な依存（例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- (オプション) PyYAML（config/*.yaml の検証に使用）

インストール（開発環境例）
-------------------------
1. リポジトリをクローンして作業ディレクトリを src パスに通す（もしくはパッケージをインストール）
   - 例: git clone ... && cd <repo>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

セットアップ手順
---------------
1. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env に機密値（トークン等）を保存します。*.env は絶対に Git にコミットしないでください。
2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。
3. （Paper Trading を使う場合）PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH を .env で調整

主要な環境変数（要点）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBroker を利用し data/paper_trading.db に記録
  - live: 実際の発注を行う想定（注意して設定すること）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う AI 機能で必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグファイルのパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- LOG_LEVEL / LOG_DIR: ログレベルとログディレクトリ
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

実行方法（例）
-------------
- 監視プロセス（Monitoring）を実行:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を使用します（KABUSYS_ENV に依存せず）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループは終了します。

- 実行エンジン（ExecutionEngine）を実行:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading 時は PAPER_TRADING_SQLITE_PATH に記録され、本番 DB とは分離されます。
  - 起動中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか、
    kill.flag により Monitoring が停止シグナルを送る仕組みがあります。

- .env 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ロギング
-------
- 共通の setup_logging を使い、stdout と日次ローテーションログ（logs/<app_name>.log）を出力します。
- LOG_DIR 環境変数または引数で出力先を変更できます。
- デフォルトは logs/ ディレクトリに日次ローテーションで 30 日分保持。

停止フラグ / Kill Switch
-----------------------
- stop_requested.flag: run_monitoring / run_execution がループを終了するための停止フラグ
  - 位置: プロジェクトルート/data/stop_requested.flag（スクリプト内で参照）
- kill.flag: Kill Switch が条件を満たした際に書き込まれ、ExecutionEngine に停止シグナルを送る用途
  - KillSwitch は data/kill.flag に理由を書き込みます（冪等）。

AI 機能について
---------------
- ニュース NLP（kabusys.ai.news_nlp）やレジーム判定（kabusys.ai.regime_detector）は OpenAI API（gpt-4o-mini）を利用します。
- OPENAI_API_KEY を環境変数または関数引数で提供してください。
- API 呼び出しはリトライやフォールバックを備えていますが、API 料金や利用制限に注意してください。

データベース / マイグレーション
-----------------------------
- monitoring_db.init_monitoring_db(conn) により必要なテーブルを冪等に作成します（system_status, trade_logs, positions, risk_logs, dashboard 等）。
- 既存 DB に対する軽微なマイグレーション（列追加）もコード中で実行します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py ...................... 環境変数 / 設定管理（.env 自動ロード）
- config_setup.py ............... .env 対話式ウィザード
- validate_config.py ............ 起動前設定検証 CLI
- run_monitoring.py ............. Monitoring プロセス起動スクリプト
- run_execution.py .............. ExecutionEngine 起動スクリプト

- utils/
  - logging_setup.py ............. ログ設定ユーティリティ
  - process_priority.py .......... プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py ............. SQLite 永続化層（監視ログ）
  - system_monitor.py ............ CPU/メモリ/ディスク/データ鮮度チェック
  - risk_monitor.py .............. ドローダウン・ポジション上限監視
  - kill_switch.py ............... Kill Switch 実装（kill.flag）
  - monitoring_engine.py ......... 各 Monitor を束ねるエンジン
  - (その他 AlertManager / TradeMonitor 等)
- execution/
  - (注文関連コンポーネント: Engine, BrokerFactory, OrderManager, Reconciler, RiskManager など)
- portfolio/
  - portfolio_builder.py ......... 候補選定、重み計算
  - position_sizing.py ........... 株数計算、aggregate cap
  - risk_adjustment.py ........... セクター上限、レジーム乗数
- research/
  - factor_research.py ........... Momentum/Volatility/Value の計算
  - feature_exploration.py ....... forward returns / IC / summary
- ai/
  - news_nlp.py .................. ニュース NLP スコア算出（OpenAI）
  - regime_detector.py .......... マクロ + ETF MA によるレジーム判定
- tools/
  - paper_verification_report.py . Paper Trading 検証レポート生成スクリプト

運用上の注意
------------
- .env ファイルには機密情報（API キー等）を保存します。絶対に Git へコミットしないでください。
- KABUSYS_ENV=live の設定は本番発注につながります。設定値（特に KILL_FLAG_CLEAR_ON_START）を慎重に確認してください。
- Monitoring は常に本番 sqlite_path を参照して監視します（環境にかかわらず）。Paper Trading の監視と実行を物理的に分離する場合は適切に DB パスを設定してください。
- OpenAI API の呼出しはコストとレイテンシに注意。API キーの管理は厳格に行ってください。

補足
----
- 自動で .env を読み込む機能は config.py に組み込まれており、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env/.env.local を読みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- YAML 検証には PyYAML が必要です。インストールされていない場合、validate_config は YAML チェックをスキップします。

お問い合わせ
------------
このドキュメントやコードに関する質問・修正はリポジトリの issue にてお願いします。