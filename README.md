README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
このリポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine（発注／注文管理／リスク制御）
- Monitoring（システム監視、Kill Switch、アラート）
- Portfolio Construction（候補選定、重み付け、ポジションサイジング）
- Research（ファクター計算、特徴量分析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム推定）
- CLI ツール（環境設定ウィザード・設定検証・Paper Trading 検証レポート等）

主な設計方針は「本番データベースとテスト（ペーパートレード）を分離」「ルックアヘッドバイアスを防ぐ」「外部 API 呼び出しは明示的に制御する（APIキー等）」です。

機能一覧
--------
- 発注エンジン（kabuステーション連携 / MockBroker によるペーパートレード）
- 注文履歴・ポジションの永続化（SQLite / DuckDB）
- 実行時のリスク管理（ポジション上限・ドローダウン監視など）
- システム監視（CPU/メモリ/ディスク/データ鮮度、プロセス生存監視）
- Kill Switch（条件を満たしたら data/kill.flag を作成して Execution を停止）
- ニュースの NLP スコアリング（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- ポートフォリオ構築（候補選定、重み付け、リスク調整、単元丸め）
- Research 用ユーティリティ（ファクター計算、IC 計算、統計サマリ）
- 便利ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

前提（動作環境 / 依存）
---------------------
- Python 3.9+（型注釈に Union|None などが使用されています）
- 推奨パッケージ（必要に応じてインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- ネットワークアクセス（kabuステーション API / OpenAI を使う場合）
- ローカルに data/ および logs/ へ書き込み可能な権限

例: 必要パッケージのインストール
- pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <this-repo>
   - cd <repo>

2. （任意）仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - python -m pip install --upgrade pip
   - python -m pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

4. 環境変数の初期化（.env を作成）
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - ウィザード後、.env が生成されます。必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_* など

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - mkdir -p data logs

使い方
------

起動スクリプト
- 実行（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し、デフォルトでは data/paper_trading.db を使用して本番 DB と分離します。
    - プロセスは data/execution.pid に PID を書きます。
    - 停止は data/stop_requested.flag の作成で行います（run_execution はこのファイルを見て停止処理を行います）。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト: 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保持します。
    - stop フラグファイル data/stop_requested.flag を検知するとループを終了します。

主要環境変数（抜粋）
- KABUSYS_ENV
  - development / paper_trading / live
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — paper_trading 用 DB
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能を利用する場合）
- PAPER_FILL_MODE（ペーパートレードの約定モード: instant/partial/never/reject）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring 用）

停止・Kill Switch
- ExecutionEngine を強制停止したい場合:
  - Kill Switch: kabusys.monitoring.kill_switch が条件成立で data/kill.flag を作成します（run_execution は起動時に kill flag の存在をチェックし起動を抑止する機能があるため注意）。
  - 手動で停止: data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。
- run_execution は data/execution.pid を作成します。ログ・PID の管理に注意してください。

ログ
- デフォルト出力: stdout + 日次ローテーションファイル
- ログディレクトリ: LOG_DIR 環境変数またはデフォルト logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）

ツール
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI（ニュース NLP / レジーム）
- ニューススコアリング:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API を利用。api_key 引数または環境変数 OPENAI_API_KEY が必要。
- レジームスコア:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に OpenAI API を利用。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード（CLI）
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/                 — ExecutionEngine 関連（broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（監視データ）
    - system_monitor.py        — システム監視（CPU/メモリ/プロセス/データ鮮度）
    - trade_monitor.py         — 注文系監視（滞留/異常約定検出）※詳細実装ファイルあり
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各監視を束ねるエンジン
    - alert_manager.py         — アラート送信（LINE 等）※実装に依存
  - portfolio/
    - portfolio_builder.py     — 候補選定、等配分/スコア配分
    - position_sizing.py       — 株数決定、aggregate cap、単元丸め
    - risk_adjustment.py       — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py  — forward returns / IC / summary
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し、結果検証、DB 書込）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント統合）
  - data/                      — 実行時に使用する DB / flag / pid ファイル（リポジトリ直下の data/ を想定）
  - logs/                      — ログファイル（デフォルト）

注意点 / 運用上のヒント
-----------------------
- run_monitoring は監視用 DB（SQLITE_PATH）を使用します。監視は本番 DB を見る仕様になっているため、環境変数設定に注意してください。
- run_execution は KABUSYS_ENV に応じてペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使うので、本番データと混同しない設計になっています。
- OpenAI や kabu API を利用する機能は API キー / パスワードが必須です。キー管理は .env を利用し、絶対にリポジトリにコミットしないでください。
- kill.flag / stop_requested.flag / execution.pid の存在有無でプロセスの挙動が変わります。運用時はこれらファイルの管理ルールを定めてください。
- DuckDB は分析用 DB、SQLite は監視・取引ログ用の永続層として利用されています。バックアップや容量管理に注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリのルートにある LICENSE ファイル（ある場合）を参照してください。

問い合わせ / 貢献
------------------
バグ報告・機能要望・プルリクエストはリポジトリの Issues / Pull Requests を通じて受け付けてください。README で触れていない内部 API を利用する場合は、該当モジュールの docstring を参照してください。

以上。必要なら、README に含める具体的な .env のサンプルや systemd / supervisor 用の起動スクリプト雛形なども追記します。どの情報を追加希望か教えてください。