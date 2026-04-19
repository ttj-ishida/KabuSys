README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。本リポジトリは以下の機能群を含みます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の実行
- 監視エンジン（MonitoringEngine）: システム稼働状況・注文状況・リスク監視、Kill Switch
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、ポジションサイズ算出、セクター制限等
- リサーチ（research）: ファクター計算、将来リターン、IC 計算、特徴量解析
- AI 補助（ai）: ニュースを LLM でスコアリング（news_nlp）、市場レジーム判定（regime_detector）
- ツール（tools）: ペーパートレード検証レポート生成など
- 環境設定ユーティリティ: .env 生成ウィザード、設定検証 CLI
- 共通ユーティリティ: ロギング設定、プロセス優先度設定など

主な設計方針
- DuckDB / SQLite を用いたデータ永続化（分析用は DuckDB、監視・発注ログは SQLite）
- .env による設定管理（自動ロード機能あり）
- Paper Trading と Live 環境の分離（paper_trading は専用 SQLite を使用）
- LLM 呼び出しは失敗時にフォールバックしフェイルセーフ化

機能一覧
----------
主な機能（抜粋）:

- 実行関連
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - ブローカークライアントの切替（実口座 / Mock, KABUSYS_ENV=paper_trading で Mock）
  - 発注履歴・注文ログ（trade_logs）管理
  - PID / stop フラグ連携（data/execution.pid, data/stop_requested.flag）

- 監視関連
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセスの存在チェック、データ鮮度検査
  - TradeMonitor: 注文の滞留・約定異常監視（trade_logs の解析）
  - RiskMonitor: ドローダウン・ポジション数の監視とアラート記録
  - KillSwitch: ルールに基づいて data/kill.flag を書き込む
  - MonitoringEngine: 上記を束ねてポーリング実行（run_monitoring.py）

- ポートフォリオ
  - 候補選定: select_candidates
  - 重み計算: calc_equal_weights, calc_score_weights
  - セクター制限: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier
  - ポジションサイズ決定: calc_position_sizes

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 参照）
  - 将来リターン / IC / 統計サマリー

- AI
  - news_nlp.score_news(): raw_news を LLM でスコア化して ai_scores に書き込む
  - regime_detector.score_regime(): ETF とマクロニュースを元に市場レジーム判定（market_regime テーブル）

- ツール
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report（期間指定可）

セットアップ手順
----------------

前提
- Python 3.10+
  - 型ヒントに PEP 604 の union 型 (|) を使用しているため 3.10 以上を推奨します。

依存パッケージ（主要）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証を行う場合に推奨）

インストール例（仮想環境推奨）
- pip を用いる例:
  1. 仮想環境作成 & 有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  2. パッケージインストール
     - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

環境設定 (.env)
- リポジトリルートに .env を配置します。自動読み込み機能により起動時に環境変数へ反映されます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 推奨手順:
  1. ウィザードで作成:
     - python -m kabusys.config_setup
  2. 設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も FAIL 扱いになります

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI モジュール利用時)
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔、秒。デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (本番環境用の安全設定)

使い方
------

基本コマンド
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - プロセス優先度を High に設定します。
    - data/execution.pid に PID を記録します。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは一元管理）。
    - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / リサーチの利用
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行する関数です。詳細はモジュールドキュメント参照。
- regime_detector.score_regime(conn, target_date, api_key=None)

ログ
- ログはデフォルトで stdout に出力され、日次ローテーションで logs/<app_name>.log にも出力されます（30 日保持）。
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")

停止 / Kill Switch
- ExecutionEngine の停止シグナル:
  - KillSwitch が評価により data/kill.flag を書き込むと Engine に停止シグナルを送る仕組みがあります。
  - run_execution/run_monitoring は data/stop_requested.flag の存在をチェックしてループを終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では推奨されません）。

ディレクトリ構成
-----------------

リポジトリの主なファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

- src/kabusys/utils/
  - logging_setup.py — 統一的なログ設定（stdout + 日次ファイル）
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ永続化層（テーブル作成・CRUD）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文関連の監視（滞留・約定異常等）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch ロジック（kill.flag 書き込み）
  - alert_manager.py — アラート通知のラッパ（LINE 等。コードベース参照）
  - monitoring_engine.py — 各 Monitor を束ねるポーリング本体

- src/kabusys/execution/
  - 実行エンジン関連（BrokerFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・リスク制限・単元丸め
  - risk_adjustment.py — セクター制限・レジーム乗数
  - __init__.py

- src/kabusys/research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — 市場レジーム判定（MA + マクロ記事の LLM 判定）
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート
  - __init__.py

- data/ — デフォルトの DB・フラグファイル等（実行時作成）
  - デフォルト SQLite / DuckDB のパス: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb
  - stop_requested.flag, kill.flag, execution.pid など

追加メモ / 実運用上の注意
-----------------------
- KABUSYS_ENV を live に設定すると本番動作となります。LINE の通知設定や Kill Switch の設定等を十分に確認してください。
- run_monitoring は監視用の SQLite を環境に関係なく production (sqlite_path) を参照します。paper_trading と混在しないよう注意してください。
- OpenAI など外部 API を使用する機能を有効にする場合は API キーを安全に管理してください。
- DuckDB / SQLite のファイルパスやログ出力先は環境変数で上書き可能です。
- config/*.yaml（strategy や risk 設定）は存在することが想定されています。validate_config では YAML のパース検証（PyYAML がインストールされている場合）も行います。生成スクリプト等がある場合はそれを利用してください（validate_config に該当する警告が出ます）。

サンプル .env（最低限）
----------------------
以下は最小限の例（実際には config_setup で入力してください）。秘密情報は実際の値に置き換えてください。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_api_key_here

問い合わせ / 貢献
-----------------
- バグ報告や改善提案は issue を立ててください。
- 大きな設計変更や依存更新の提案は事前に issue で議論してください。

以上が本プロジェクトの概要と利用方法です。README に記載のない操作や詳細は該当モジュールのドキュメント（ソース内 docstring）を参照してください。