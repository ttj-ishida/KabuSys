README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。本リポジトリは以下の主要機能を提供します。

- 発注エンジン（ExecutionEngine）とモニタリング（Monitoring）の起動スクリプト
- 環境設定ウィザードと設定検証ツール
- ポートフォリオ構築、リスク調整、ポジションサイズ計算などのポートフォリオロジック
- DuckDB を用いたファクター計算・リサーチ機能
- Paper Trading 用の検証レポート生成ツール
- OpenAI を使ったニュース NLP / レジーム判定モジュール（任意機能）

安全性を重視し、Paper Trading と Live 環境は分離される設計です（データベース・ブローカークライアントなど）。

主な機能一覧
--------------
- 実行（Execution）
  - Engine 起動スクリプト（python -m kabusys.run_execution）
  - ブローカー抽象化（実口座 / MockBroker の切替）
  - 発注・注文管理、リスク管理、調整、レコンシリエーション

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（条件により Execution を停止するための flag ファイル）

- 環境設定・検証
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

- リサーチ / ポートフォリオ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリー
  - 候補選定、重み付け、セクター上限適用、ポジションサイズ計算

- AI（任意）
  - ニュースの LLM によるセンチメントスコアリング（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API（gpt-4o-mini 等）を使用（API キー必須）

- ツール
  - Paper Trading 検証レポート出力（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリのインストール
   - 必要パッケージ（最低限）
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config 検証で YAML 検査を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

3. 環境変数の準備
   - .env を作成する方法（推奨）:
     - python -m kabusys.config_setup
     - 対話ウィザードに従って .env を生成します。
   - 手動で設定する代表的な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（例: data/kabusys.duckdb） — デフォルトあり
     - SQLITE_PATH（例: data/monitoring.db） — 監視 DB
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他: LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START など

   - 自動 .env ロードについて
     - 起動時にプロジェクトルートの .env と .env.local を自動読み込みします（OS 環境変数が優先）。
     - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を使用

5. データディレクトリとファイル
   - ログ: デフォルト logs/
   - SQLite / DuckDB の親ディレクトリは存在しない場合は起動時に作成されることがありますが、権限等に注意してください。

使い方
------

基本の起動コマンド

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動しません。
    - 実行中は data/execution.pid を使用する場合があります。
    - 強制停止は data/stop_requested.flag を書くか、Kill Switch により data/kill.flag が作成されると ExecutionEngine に停止シグナルが送られます。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します（注意）。
    - 停止フラグ: data/stop_requested.flag を監視し存在すればループを終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可。環境変数 PAPER_TRADING_SQLITE_PATH が使われます。

注意点 / 運用上の留意事項
- .env は決して Git 管理下に置かないでください（config_setup も README に明記しています）。
- KABUSYS_ENV によって発注系の動作が大きく変わります。特に live 設定時は十分に注意してください（validate_config で live 時の警告があります）。
- Monitoring は監視 DB に常に「本番の sqlite_path」を使う設計です。paper_trading であっても監視ログは該当のパスに書かれます（run_monitoring の実装参照）。
- OpenAI を使う処理は API キーが必須です（OPENAI_API_KEY）。API 呼び出し失敗時はフェイルセーフとして無害なデフォルトで継続する設計になっていますが、ログを確認してください。
- Kill Switch（data/kill.flag）:
  - RiskMonitor がトリガー条件を満たすと、KillSwitch が data/kill.flag を作成して ExecutionEngine の停止を促します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアしますが、本番では 0 を推奨します。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要モジュールと役割（本リポジトリから抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理。自動 .env 読込・優先度のロジックを含む。
  - config_setup.py
    - .env 対話式ウィザード。
  - validate_config.py
    - .env や config/*.yaml の起動前検証ツール。
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、スレッド運用）。
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）。
  - utils/
    - logging_setup.py: ロギングの統一設定（stdout + 日次ローテートファイル）。
    - process_priority.py: プラットフォーム非依存のプロセス優先度/affinity 設定。
  - monitoring/
    - monitoring_db.py: SQLite による監視ログ永続化層（初期化・マイグレーションを含む）。
    - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度監視。
    - trade_monitor.py: （注文関連の監視 — コードベースに含まれるがここでは省略） 
    - risk_monitor.py: ドローダウン・ポジション上限監視。
    - kill_switch.py: 停止フラグ作成ロジック。
    - monitoring_engine.py: 各モニタの集約ランナー。
    - alert_manager.py: （アラート送信管理 — 実装参照）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 発注エンジン・注文管理・ブローカークライアントの抽象化など（実行ロジック）。
  - portfolio/
    - portfolio_builder.py: 候補選定、重み計算
    - risk_adjustment.py: セクター上限、レジーム乗数
    - position_sizing.py: 発注株数計算・集約キャップ処理
  - research/
    - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB 経由）
    - feature_exploration.py: 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py: ニュース記事の LLM センチメント評価（ai_scores への書込）
    - regime_detector.py: マクロ + ETF MA によるレジーム判定とテーブル書込
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成

主要なファイル（起動・運用時に注目）
- run_execution.py: 発注エンジン起動
- run_monitoring.py: 監視ループ起動
- config_setup.py: .env ウィザード
- validate_config.py: 設定検証
- monitoring/monitoring_db.py: 監視 DB 初期化、スキーママイグレーション
- utils/logging_setup.py: ログの標準化

サンプル .env（最小）
-------------------
以下は参考例です（実際は config_setup で生成してください）。絶対に Git にコミットしないでください。

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

その他
-----
- 追加の設定ファイル（config/*.yaml）はプロジェクト設定用に想定されています（validate_config 参照）。PyYAML がインストールされていればパース検査を行います。
- ログはデフォルト logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30 日分保持）に出力されます。LOG_DIR 環境変数で変更可能です。
- 本ドキュメントはコードベース内の docstring・コメントを元に要約しています。実運用前に validate_config を実行して環境を確認してください。

問題・フィードバック
------------------
実行中のログ・validate_config の出力を参照し、不整合や欠損がないか確認してください。特に本番（KABUSYS_ENV=live）では設定のミスや kill flag の扱いに注意してください。