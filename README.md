README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買基盤（調査・ポートフォリオ構築・発注・監視・AI 補助）を目的とした Python パッケージです。本リポジトリは以下の要素を含みます:

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live 切替可）
- 監視サブシステム（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築用純粋関数群（候補選定・重み付け・サイズ算出・リスク調整）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP（OpenAI）を使った銘柄スコアリングとレジーム判定
- 運用・検証用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

特徴
----
- 環境ごとに挙動を分離（KABUSYS_ENV = development | paper_trading | live）
- Paper Trading 時は MockBrokerClient を利用し DB を分離（data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視／発注ログに利用
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / レジーム判定（API キー対応・リトライ付き）
- ロギング統一化（コンソール + 日次ファイルローテーション）
- プロセス優先度 / CPU affinity の簡易ユーティリティ
- フェイルセーフ（API 失敗やデータ欠損は安全にフォールバック）

必要条件（主な依存）
------------------
- Python 3.8+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合、任意）

インストール例（仮）
-------------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

※ 実際の requirements ファイルはプロジェクトに合わせて管理してください。

セットアップ手順
---------------
1. プロジェクトルートに移動（パッケージは src/ 配下）
2. .env を作成（対話ウィザード）
   - python -m kabusys.config_setup
     - 対話形式で J-Quants / kabu API など必須値を設定できます。
3. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合は --strict を付けます
4. データディレクトリ作成（必要なら）
   - data/（SQLite / DuckDB / pid/flag ファイル保存用）
   - logs/（ログ出力）
   - 実行時に自動作成される箇所もありますが、事前に作ると権限エラーを防げます

主要な環境変数（要確認）
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: DEBUG | INFO | WARNING | ...
- LOG_DIR: ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

例（.env の最小例）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO

設定ファイルと検証
-----------------
- config/*.yaml（system_config.yaml, strategy_config.yaml 等）をプロジェクト配下に置く想定
- python -m kabusys.validate_config で環境変数と config/*.yaml の存在・基本整合性をチェック
- PyYAML が無い場合は YAML 中身の検証をスキップする（警告が出ます）

起動方法（実運用 / 開発）
-----------------------
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い paper 用 SQLite に書き込みます
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用（環境にかかわらず）
  - data/stop_requested.flag を置くと監視ループが終了します

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一
- 標準出力（stdout）と日次ローテーションファイル logs/<app_name>.log に出力
- LOG_DIR 環境変数でログ格納先を変更可能

主要モジュール（簡易説明）
------------------------
- kabusys.config / config_setup / validate_config
  - 環境変数の読み込み・対話式作成・検証ツール

- kabusys.execution
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager
  - 実際の発注ロジック・注文管理・リスク管理の集約

- kabusys.monitoring
  - monitoring_db: SQLite スキーマ定義と読み書きラッパ
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、プロセス監視
  - trade_monitor: 注文の滞留・約定異常等の監視（コード参照）
  - risk_monitor: ドローダウンとポジション上限チェック
  - monitoring_engine: 各モニタを束ね定期実行
  - kill_switch: kill.flag による実行エンジンの停止シグナル発行
  - alert_manager: （アラート送信ラッパ、実装参照）

- kabusys.portfolio
  - 銘柄選定（select_candidates）、重み付け（equal/score）、ポジションサイズ算出（risk_based 等）、セクター制限、レジーム乗数

- kabusys.research
  - factor_research: momentum/value/volatility 等ファクター計算（DuckDB）
  - feature_exploration: 将来リターン / IC / 統計サマリー

- kabusys.ai
  - news_nlp: ニュース集合を OpenAI に投げて銘柄ごとのスコアを ai_scores に書き込む（バッチ・リトライ・検証あり）
  - regime_detector: ma200 とマクロニュースでレジーム（bull/neutral/bear）判定・保存

- kabusys.utils
  - logging_setup: ログ設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番です。LINE 通知や Kill Switch の設定、KILL_FLAG_CLEAR_ON_START 等を慎重に設定してください。
- .env は絶対にリポジトリにコミットしないこと（機密情報含む）。
- OpenAI API 呼び出しはコストとレート制限を考慮して利用してください。API キーは OPENAI_API_KEY か関数引数で渡せます。
- 監視ループ／実行エンジンは stop flag（data/stop_requested.flag）や kill.flag を用いた外部制御を想定しています。自動停止フローを整備してください。

ディレクトリ構成（抜粋）
---------------------
プロジェクトの主要構成ファイルは次の通り（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/              # 実行時生成: monitoring.db / paper_trading.db / kill.pid 等
  - logs/              # ログ出力先（デフォルト）

付録: よく使うコマンド例
-----------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

さらに調査したい箇所
-------------------
- execution パッケージの BrokerClient の実装（実ブローカ連携/Mock どちらが使われるか）
- alert_manager（通知先: LINE 等）の具体的な実装
- config/*.yaml のスキーマと generate_config.py（generate スクリプトが存在する場合はそれも参照）

---

この README はソースコードの主要部分からまとめた概要ドキュメントです。実際の運用前に python -m kabusys.validate_config や通期のテストを必ず行ってください。必要なら README にさらにコマンド例や設定項目の詳細を追加します。