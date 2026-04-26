# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはソースツリー（src/kabusys/*）の主要コンポーネントと使い方をまとめたものです。

概要
----
KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。主な機能として以下を含みます。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を行う。paper_trading モードをサポートし本番 DB と分離。
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク監視を定期的にポーリング・記録し、Kill Switch（停止フラグ）を管理。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム補正などの純粋関数群。
- リサーチ: DuckDB 上の価格・財務データからファクターを算出するモジュール（モメンタム／ボラティリティ／バリュー等）や特徴量解析。
- AI ヘルパー: OpenAI を用いたニュースのセンチメントスコアリング（news_nlp）、マーケットレジーム判定（regime_detector）。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード・検証 CLI、各種 DB/ログ操作ユーティリティ。
- ツール: ペーパートレーディング検証レポート生成スクリプト等。

主な機能一覧
--------------
- 設定関連
  - 対話式 .env 作成/更新: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い data/paper_trading.db に記録
  - Monitoring 起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
- 監視・リスク
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
  - RiskMonitor: ドローダウン・ポジション数上限監視とリスクログ記録
  - KillSwitch: 条件で data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る
- ポートフォリオ構築
  - 候補選定 (select_candidates)
  - 等配分 / スコア加重重み計算 (calc_equal_weights / calc_score_weights)
  - ポジションサイズ算出（risk_based / equal / score）
  - セクターキャップ適用・レジーム乗数計算
- リサーチ
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC・統計サマリ機能
- AI
  - ニュースセンチメントを OpenAI でスコア化し ai_scores テーブルへ書込み
  - レジーム判定を OpenAI と価格データで合成して market_regime テーブルへ保存
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

前提・依存ライブラリ
-------------------
最低限必要なパッケージ（要 Python 3.8+ 想定）:
- duckdb
- pyyaml
- openai
- psutil
- （標準ライブラリ: sqlite3, logging, threading, datetime 等）

インストール例（pip）
- pip install duckdb pyyaml openai psutil

セットアップ手順
----------------
1. リポジトリをチェックアウト／クローン。
2. Python 環境を準備（venv 等）。
3. 依存パッケージをインストール:
   - pip install duckdb pyyaml openai psutil
4. .env を作成:
   - python -m kabusys.config_setup
   - 対話ウィザードが .env を生成します。生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を確認してください。
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。
6. DB 初期化:
   - 実行スクリプト起動時に SQLite/ DuckDB ファイル（デフォルト: data/monitoring.db, data/kabusys.duckdb）が自動作成されます。
7. ログディレクトリ:
   - デフォルト logs/ にアプリ毎のログ（execution.log, monitoring.log 等）が出力されます。必要なら LOG_DIR 環境変数で変更可能。

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト development
  - paper_trading: 発注は MockBroker による擬似約定・専用 SQLite を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- JQUANTS_BULK_API_KEY: J-Quants Bulk API Key（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL, LOG_DIR: ログレベル・ログ格納先

使い方（主要コマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成するとエンジンは安全に停止します。
  - ExecutionEngine は Settings により paper_trading モードで別 DB を使います。
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は本番 sqlite_path を常に使用（環境に依らず）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- AI 機能（スクリプトから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数か引数で指定する必要があります。

停止・Kill Switch
-----------------
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag（run_monitoring では別パスだが同様）を参照してループを終了します。停止したい場合は flag ファイルを作成してください。
- KillSwitch（監視側）はリスク条件で data/kill.flag を書き込み、ExecutionEngine 側がこのファイルの存在を検出して停止する仕組みです。
- Settings に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ
---
- setup_logging ユーティリティでログは stdout と日次ローテートファイルに出力されます（デフォルト logs/）。アプリ名毎にファイルが作成されます（例: logs/execution.log）。
- LOG_LEVEL 環境変数でログレベル指定可能。

ディレクトリ構成（概要）
----------------------
（リポジトリの src/kabusys 以下の主要ファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数/.env の自動読み込み・Settings クラス
  - config_setup.py          : 対話式 .env ウィザード
  - validate_config.py       : 設定検証 CLI
  - run_execution.py         : ExecutionEngine 起動スクリプト
  - run_monitoring.py        : Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py : Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            : ニュース NLP（OpenAI を使ったスコア算出）
    - regime_detector.py     : レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       : SQLite テーブル初期化・永続化層
    - monitoring_engine.py   : 各 Monitor を束ねるエンジン
    - system_monitor.py      : （監視用ロジックの実体は別ファイル群にある想定）
    - risk_monitor.py        : ドローダウン/ポジション数監視
    - trade_monitor.py       : （取引ログ監視）
    - kill_switch.py         : kill.flag 管理
    - alert_manager.py       : （アラート送信管理）
  - execution/
    - execution_engine.py    : ExecutionEngine 本体（起動/セッション管理）
    - broker_factory.py      : ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   : 候補選定・重み計算
    - position_sizing.py     : 株数決定・丸め
    - risk_adjustment.py     : セクター上限・レジーム乗数
  - research/
    - factor_research.py     : ファクター計算（momentum/volatility/value）
    - feature_exploration.py : 将来リターン/IC/統計
  - utils/
    - logging_setup.py       : ログ設定ユーティリティ
    - process_priority.py    : プロセス優先度 / CPU affinity 設定
  - monitoring/...（上記に続く）

注記
----
- paper_trading モードは本番 DB と完全に分離されるように設計されています。PAPER_TRADING_SQLITE_PATH を設定して専用 DB を使用してください。
- AI 関連機能は OpenAI API に依存します。API キー管理や呼び出し制限、コストに注意して運用してください。
- .env ファイルは秘密情報を含むため、絶対に VCS（git）にコミットしないでください（config_setup でも警告あり）。
- production（KABUSYS_ENV=live）では Kill Switch 周り・LINE 通知などの設定を必ず確認してください。

貢献・開発メモ
---------------
- テストや開発時に自動で .env をロードしたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（config.py にて自動ロードを抑止可能）。
- DuckDB を使ったリサーチ機能は大量データを想定しており、prices_daily / raw_financials 等のテーブルが存在することを前提としています。
- ローカル開発では paper_trading を使って動作確認をすることを推奨します。

---

不明点や README に追記してほしい内容があれば教えてください。設定例（.env.example）や system_config の自動生成手順、デプロイ／サービス化手順（systemd / supervisor など）を追加することもできます。