README
======
本ドキュメントは本リポジトリ（KabuSys）の概要、セットアップ、実行方法およびディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は日本株自動売買システムのコアライブラリ群です。  
主な目的は以下の通りです。
- シグナル生成・ポートフォリオ構築（research / portfolio）
- 注文実行とリスク管理（execution）
- システム監視・アラート・Kill Switch（monitoring）
- ニュースを用いた AI（LLM）によるセンチメント評価（ai）
- Paper Trading 検証ツール（tools）
- ユーティリティ群（設定読み込み / ロギング / プロセス優先度設定 など）

主な特徴
---------
- 環境変数ベースの設定管理（.env 自動ロード / config_setup による対話式作成）
- Execution / Monitoring の実行スクリプトを用意（プロセス優先度設定、DB 接続、ポーリングなど）
- Monitoring 用 SQLite テーブル定義・永続化ロジックを提供（init_monitoring_db）
- DuckDB 経由での時系列ファクター計算・研究ツール（prices_daily 等を想定）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / 市場レジーム判定の実装（API 呼び出し時のリトライ等を考慮）
- Paper Trading 用の検証レポート生成（tools.paper_verification_report）

前提条件
--------
- Python 3.10 以上（型ヒントで Python 3.10 の構文を使用）
- sqlite3（標準ライブラリ）
- 推奨パッケージ（主要機能を動かすため）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に任意）
- ネットワーク接続（OpenAI API を利用する場合）
- kabuステーション等外部ブローカー（実運用時）

インストール（ローカル開発用）
-----------------------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt を利用）

環境変数 / .env
----------------
設定は .env ファイル（プロジェクトルート）または環境変数で与えます。主なキーとデフォルト／備考は以下。

必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）

任意 / デフォルト値あり
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live) （default: development）
- DUCKDB_PATH           : DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（default: INFO）
- LOG_DIR               : ログディレクトリ（default: logs/）
- OPENAI_API_KEY        : OpenAI API キー（ai 機能利用時）
- PAPER_FILL_MODE       : Paper Trading のフィルモード（instant | partial | never | reject、default: instant）
- MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、default: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等も Settings で管理

.env を対話式に作成する
- python -m kabusys.config_setup
  - 対話式ウィザードで .env を生成できます（.env は絶対に Git にコミットしないこと）。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります。

主要スクリプト（実行方法）
-------------------------

1) 監視（Monitoring）
- 実行:
  - python -m kabusys.run_monitoring
- 概要:
  - Settings から sqlite_path（監視 DB）・duckdb_path を読み、Monitoring 用テーブルを初期化（init_monitoring_db）。
  - SystemMonitor を定期実行（デフォルト 60 秒）。MONITOR_POLL_INTERVAL 環境変数で変更可能。
  - 停止: プロジェクトルート/data/stop_requested.flag が存在するとループを抜けて終了。
  - 監視は KABUSYS_ENV に関係なく production sqlite_path を使用します（監視は本番データを想定）。

2) 実行エンジン（Execution）
- 実行:
  - python -m kabusys.run_execution
- 概要:
  - Settings を読み込み、env に応じて SQLite パスを切り分け（paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離）。
  - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading 環境では MockBrokerClient を使用）。
  - ExecutionEngine をスレッドで起動し、stop flag を監視。stop は data/stop_requested.flag で指示。
  - 起動前に stop flag が既にある場合は起動せず終了。
  - PID ファイル（data/execution.pid）を作成します（Settings.pid_file_path）。

3) Paper Trading 検証レポート（tools）
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で指定しても可）
- 概要:
  - paper_trading の SQLite DB を参照して稼働率、注文成功率、レイテンシ等を集計し PASS/FAIL を判定します。

4) AI（ニュース NLP / レジーム判定）
- ライブラリ API:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)
- 注意:
  - OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要。
  - API 呼び出しは一定のリトライ処理を含み、失敗時はフェイルセーフ（ゼロフォールバック）で続行します。

停止・Kill Switch
-----------------
- run_monitoring / run_execution はどちらもプロジェクトルート/data/stop_requested.flag の存在でグレースフルに停止します。
- Kill Switch（自動停止判定）は monitoring.kill_switch が data/kill.flag を書き込みます。ExecutionEngine はこのファイルを参照して停止できます。
- Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
----
- ログはデフォルトで stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション、30日分保持）へ出力されます。LOG_DIR 環境変数で変更可能。
- setup_logging(app_name="execution" | "monitoring" 等) でアプリ名に応じた log ファイルが生成されます。

データベース初期化
-----------------
- 監視用テーブルは init_monitoring_db(sqlite_conn) を呼ぶことで作成されます（冪等）。
- DuckDB 側のテーブル（prices_daily / raw_financials / raw_news 等）は別途データ投入パイプラインが必要です（本リポジトリ内の data.pipeline を参照のこと）。

開発者向けユーティリティ
-----------------------
- 設定の自動ロードはデフォルトで有効。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます。
- .env の読み込み順序:
  - OS 環境変数 > .env.local > .env
- validate_config により .env と config/*.yaml の存在／基本整合性をチェックできます（PyYAML があれば YAML のパースも検証）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要なファイル/モジュールの抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続層
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — 注文滞留等監視（実装参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — アラート送信（LINE 等、実装参照）
  - execution/
    - execution_engine.py    — 実行エンジンコア（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 経由）
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート

注意事項 / 運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大な影響を与えるため validate_config の利用を強く推奨します。
- .env は機密情報（API トークン等）を含むため絶対にリポジトリに含めないでください。
- run_execution は paper_trading モードでは発注先がモックに切り替わり、paper_trading 用の SQLite に記録されます。実運用時は KABUSYS_ENV=live を設定して実ブローカーを使います。
- MONITOR_POLL_INTERVAL は秒単位で指定できます。不正値（0 や文字列等）はデフォルト（60 秒）にフォールバックされます。
- OpenAI を利用する機能は API コストがかかります。キーの管理と呼び出し頻度に注意してください。

追加の参照
-----------
- 各モジュールの docstring / コメントに実装の意図や挙動が詳細に記載されています。特に ai/*.py、research/*.py、portfolio/*.py はアルゴリズム仕様に関する注釈が多いため参照してください。

問題・開発の進め方
-----------------
- まず .env を作成し、python -m kabusys.validate_config で設定を確認してください。
- DuckDB に時系列データを投入して research / ai の機能を確認します（テストデータを用意することを推奨）。
- Monitoring（run_monitoring）を立ち上げて監視ログが data/monitoring.db に蓄積されることを確認してください。
- 実行エンジン（run_execution）は paper_trading で動かして動作確認 → live 切替 の順が安全です。

以上。必要であれば README に記載するコマンド例や環境変数の表をさらに追加します。どの部分を詳細化したいか教えてください。