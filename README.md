KabuSys — 日本株自動売買システム
=================================

このリポジトリは、国内株自動売買システム「KabuSys」のコードベースです。  
README はプロジェクトの概要、主要機能、セットアップ手順、使い方（主要コマンド例）、およびディレクトリ構成を日本語でまとめたものです。

要点
-----
- Python 製の自動売買 / 監視 / リサーチ用ライブラリ群と起動スクリプト群を含む。
- DuckDB（時系列価格・ファクター計算など）、SQLite（監視・取引ログ）、OpenAI（ニュース NLP / レジーム判定：任意）などと連携。
- 環境ごとに挙動を分離（development / paper_trading / live）。
- ペーパートレード時は本番 DB と分離して data/paper_trading.db を使用する仕組みあり。

主な機能
---------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替対応（KABUSYS_ENV）。
  - Paper trading の場合は MockBrokerClient を使い、専用 SQLite に記録。
  - プロセス優先度の設定・PID ファイル管理・停止フラグ監視を実装。

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視。
  - system_status / trade_logs / risk_logs / dashboard / positions を SQLite に永続化。
  - Kill Switch（条件を満たすと data/kill.flag を書いて ExecutionEngine を停止）。

- Portfolio construction（portfolio パッケージ）
  - 銘柄選定、重み計算（等分配・スコア加重）、セクターキャップ、ポジションサイズ決定ロジック。

- Research（research パッケージ）
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）、将来リターン計算、IC 計算、統計サマリー。
  - DuckDB を使ってデータを SQL と Python 混合で計算。

- AI（ai パッケージ）
  - ニュース NLP スコアリング（OpenAI API を使った銘柄単位のセンチメント算出）。
  - 市場レジーム判定（MA200 とマクロニュースの LLM センチメント合成）。

- ユーティリティ
  - 環境設定ウィザード（config_setup.py）で .env を対話的生成。
  - 設定検証ツール（validate_config.py）で .env と config/*.yaml の事前チェック。
  - ログ設定ユーティリティ（utils.logging_setup）／プロセス優先度設定（utils.process_priority）等。

前提・依存
-----------
主な Python パッケージ（代表例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証を行う場合）
- sqlite3（標準ライブラリ）

（プロジェクトに requirements.txt がなければ手動でインストールしてください）
例:
- pip install duckdb psutil openai pyyaml

重要なデフォルトファイル / ディレクトリ:
- data/monitoring.db（SQLite、監視用。環境変数 SQLITE_PATH で指定可）
- data/paper_trading.db（ペーパートレード用 SQLite）
- data/kabusys.duckdb（DuckDB、データ分析用。環境変数 DUCKDB_PATH で指定可）
- data/execution.pid（ExecutionEngine の PID ファイル）
- data/kill.flag（Kill Switch が発動したときに作成）
- data/stop_requested.flag（外部から監視/実行の停止を要求するためのフラグ）

設定（主要な環境変数）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db（Monitoring は環境に関わらず本番 sqlite_path を使用する点に注意）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の充足挙動（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

自動 .env ロード
----------------
- プロジェクトルートにある .env / .env.local は自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（基本）
---------------------
1. リポジトリをクローンして Python 仮想環境を作成:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. .env を作成:
   - 対話式に作成する（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成し、README の主要環境変数を記載する。

4. 設定検証:
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）:
   - mkdir -p data logs

使い方（主要コマンド）
---------------------

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB とは分離されます）。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - ExecutionEngine の PID は data/execution.pid に書かれます。
    - 停止は data/stop_requested.flag を作成するか、kill.flag（Kill Switch）により停止されます。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番設定）を使って監視ログを書き込みます。

- 環境設定ウィザード:
  - python -m kabusys.config_setup
  - 対話式に .env を生成・更新できます。

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定。

- AI 機能（プログラムから呼ぶ）:
  - ニュース NLP（銘柄ごとの AI スコア算出）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - 市場レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

ログ
----
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト: logs/）。
- コンソール出力は stdout に出力されます（utils.logging_setup.setup_logging）。

停止 / Kill Switch
-----------------
- 外部から強制停止するには data/stop_requested.flag を作成（run_* スクリプトはこれを検知して終了）。
- システム的な停止（リスクルール等）を発動するには KillSwitch が data/kill.flag を書きます。Execution は起動時にこのフラグを検査します。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理、.env 自動ロード
- config_setup.py          — .env 作成ウィザード（対話式）
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

パッケージ（主な subpackages）
- ai/
  - news_nlp.py             — ニュースセンチメント算出（OpenAI 連携）
  - regime_detector.py      — 市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs...）
  - system_monitor.py       — システム状態 / データ鮮度監視
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - trade_monitor.py        — （略：滞留注文・約定異常検出など）
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - kill_switch.py          — kill.flag の作成/管理
  - alert_manager.py        — （略：LINE 等への通知管理）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（上記は主要ファイルの抜粋です。実際のツリーはリポジトリの内容に準じます）

開発者向けノート
-----------------
- DB マイグレーションは簡易的に init_monitoring_db() 内で実行（カラム追加等のチェックと ALTER）。
- DuckDB の SQL 実行は duckdb.DuckDBPyConnection を受け取り行う設計。research / ai モジュールは DuckDB を直接参照して計算を行う。
- OpenAI の呼び出し部はリトライ・バックオフやレスポンスのバリデーションを行っており、テスト時には該当呼び出し関数をパッチして差し替えられるよう設計されています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CWD に依存しない探索ロジックです。

よくある運用上の注意
-------------------
- Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します。運用時は監視 DB の指定に注意してください。
- Paper trading は paper_trading 用 DB に記録し本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください（validate_config の警告をよく読むこと）。
- Kill Switch は意図せずクリアされないよう KILL_FLAG_CLEAR_ON_START を本番で 0 にしてください。

問題・拡張
----------
- 価格が取得できない銘柄に対するフォールバックや lot_size の銘柄別対応など、将来的な拡張ポイントが複数コメントで指摘されています（position_sizing, risk_adjustment 等）。

ライセンス / 貢献
-----------------
- この README にライセンス情報は含めていません。リポジトリに LICENSE ファイルがあればそちらを参照してください。
- 貢献方法はプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。

以上。必要であれば、README に入れるサンプル .env のテンプレートや、よく使うコマンド集（systemd / Supervisor 用のユニットファイル例、docker-compose 例など）を追加で作成します。どの情報を詳細化したいか教えてください。