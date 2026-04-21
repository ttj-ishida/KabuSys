README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤ライブラリ兼起動スクリプト群です。本リポジトリには以下の主要機能を提供するモジュールが含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト
- 監視（Monitoring）コンポーネント・ポーリングループ
- Paper Trading 向け検証ツール（レポート生成）
- ポートフォリオ構築・ポジションサイズ計算・リスク調整（純粋関数群）
- リサーチ用ファクター計算 / 特徴量解析（DuckDB ベース）
- ニュース NLP（OpenAI）を用いたセンチメント評価・レジーム検出
- 環境設定ウィザードと設定検証ツール
- 共通ユーティリティ（ログ設定・プロセス優先度設定等）

特徴
----
- 開発 / ペーパートレード / 本番 (KABUSYS_ENV) の分離運用を想定
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB として利用（data/kabusys.duckdb）
- 監視（system / trade / risk）により Kill Switch（data/kill.flag）で発注エンジンを安全停止
- OpenAI を用いたニュースセンチメントと市場レジーム判定（失敗時はフェイルセーフで継続）
- ロギングは統一的に設定（stdout と日次ローテーションファイル出力）

前提条件
-------
- Python 3.9+（型アノテーション等の使用を想定）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- OS 権限: プロセス優先度変更や CPU affinity 設定は権限が必要になる場合があります

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt がない場合は下記を直接）。
   - pip install duckdb psutil openai PyYAML

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数の例:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
-----

起動スクリプト（CLI）
- 監視ループを起動する（monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - ログ設定（logs/monitoring.log へ日次ローテート）
    - プロセス優先度を "high" に設定（可能な場合）
    - SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）へ接続
    - SystemMonitor.check_once() をポーリング（デフォルト 60 秒）
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了

- 実行エンジンを起動する（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper トレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient 経由で擬似発注
    - 実行中は data/execution.pid を使用（PID ファイル）
    - 停止: data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書き込まれると安全停止処理が行われます

ユーティリティ / ツール
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の生成 / 更新を対話式で行います

- 設定検証
  - python -m kabusys.validate_config
  - .env と config/*.yaml の存在・基本整合性をチェックします

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

ライブラリ機能（Python から利用）
- リサーチ・ファクター計算
  - 例:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - rows = calc_momentum(duckdb_conn, target_date)

- ポートフォリオ構築 / ポジションサイズ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

- AI（ニューススコアリング）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

主要環境変数（抜粋）
------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db（paper_trading モード用）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

.env の自動読み込みルール
- 起動時に自動でロードされる順序:
  1. OS 環境変数（既存値は保護）
  2. .env（プロジェクトルート）
  3. .env.local（存在すれば上書き。ただし OS 環境変数は保護）
- 無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップ

運用メモ
-------
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution の起動ループがこれを検知して終了する（運用側で作成する単純な停止スイッチ）
  - data/kill.flag: KillSwitch（監視ロジック）によって作成され、ExecutionEngine に停止シグナルを送るために使用
  - KillSwitch は理由テキストを kill.flag に書き込みます（冪等）
- ログ:
  - デフォルト logs/<app_name>.log（TimedRotatingFileHandler により日次ローテート、30日保持）
  - ログディレクトリは LOG_DIR 環境変数で変更可能
- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると、実発注を伴わない MockBrokerClient が使用され、発注ログは data/paper_trading.db に記録されます（本番 DB とは分離）
- プロセス優先度:
  - run_monitoring/run_execution は起動時に set_process_priority("high") を試みます。失敗しても例外にはならず警告ログのみ出ます。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要ファイル群（抜粋）です。実際のリポジトリにはさらにファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — 監視ポーリングループ起動スクリプト
  - run_execution.py         — 実行エンジン起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py       — （監視ロジックの一部）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/               — ExecutionEngine 関連（broker, order_manager, risk_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

開発者向けメモ
--------------
- DuckDB 接続を渡す設計になっているため、テスト時に一時的な in-memory DB を作って関数を呼べます。
- OpenAI 呼び出しは内部で _call_openai_api を使っているため、unittest.mock.patch で置き換えてテストできます。
- .env 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用します。配布後に自動検出できない場合は手動で .env を読み込むか KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

ライセンス / バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

問い合わせ / 貢献
-----------------
- バグ報告・機能要望は issue を立ててください。プルリクエスト歓迎です。

以上が本コードベースの README です。個別のスクリプトやモジュールの詳細な使い方（引数や返り値の仕様）については、該当ファイルの docstring を参照してください。必要であれば README に具体的な例（.env テンプレート、systemd ユニット例 など）を追加できます。