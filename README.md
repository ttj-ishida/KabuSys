KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。データ処理（DuckDB）、ポートフォリオ構築、注文実行、監視、リスク管理、研究用ファクター計算、AI（ニュースNLP・レジーム検出）などのコンポーネントを備え、ローカル開発 / ペーパートレード / 本番（live）を切り替えて動かせるように設計されています。

主な特徴
--------
- ExecutionEngine（発注エンジン）: 本番 or ペーパー（MockBroker）を切替可能
- Monitoring: システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を監視しアラート／Kill Switch を実行
- Portfolio construction: 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数対応
- Research: モメンタム / ボラティリティ / バリュー等のファクター計算、IC評価、統計サマリ
- AI モジュール: ニュースを LLM（OpenAI）でスコアリング、マクロ＋MAから市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度・CPU affinity、.env ウィザード、設定検証ツール
- レポート: Paper Trading 検証レポート生成スクリプト

必要な環境・依存パッケージ
-------------------------
（プロジェクトの requirements.txt があればそちらを利用してください。無ければ下記をインストール）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (config/*.yaml の内容検証を行う場合)
- その他、標準ライブラリのみで動作するコンポーネントあり

セットアップ手順
----------------

1. リポジトリをクローンしてプロジェクトルートへ移動。

2. 仮想環境を作成・有効化して依存パッケージをインストール（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai pyyaml

3. 初期設定 (.env) を作成:
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワード等の必須値を入力します。
   - もしくは .env を手動で作成。重要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - OPENAI_API_KEY: OpenAI を使う場合
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL, LOG_DIR, PAPER_FILL_MODE 等

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 必要に応じて data/ ディレクトリや logs/ を作成（setup ログが自動で作成しますが権限等で失敗する場合は事前作成しておくとよいです）。

使い方（主なスクリプト）
-----------------------

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは data/paper_trading.db に記録されます（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が既に存在すると起動を中止します。
    - 停止するにはプロセスに kill を送るか、監視側からの kill.flag を用いる（後述）。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は Settings の sqlite_path（通常 data/monitoring.db）を使用します（環境に依らず本番監視 DB を使う設計）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成するとループ終了します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / 研究用の関数呼び出し（ライブラリ API として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究モジュール（duckdb 接続を渡して使用）:
    - kabusys.research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等

運用上の重要点
--------------
- Kill Switch / Stop フラグ:
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に運転停止を促します。
  - run_execution/run_monitoring は data/stop_requested.flag の有無を定期チェックして終了します（これらは運用でプロセス安全に停止する仕組み）。
  - Settings.kill_flag_clear_on_start=1 を本番で設定すると危険です（自動クリアされるため意図せず再開するリスクあり）。

- ログ:
  - 共通 logging_setup により stdout と logs/<app_name>.log に日次ローテーションで出力します。ログレベルは LOG_LEVEL、ログディレクトリは LOG_DIR で調整可能です。

- DB:
  - DuckDB: 分析・研究用データ（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・注文ログ（data/monitoring.db）およびペーパートレード用 data/paper_trading.db
  - monitoring_db.init_monitoring_db() により必要なテーブルは自動生成・マイグレーションされます。

設定（主な環境変数）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: OpenAI を利用する場合
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE（instant/partial/never/reject）など

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要ファイル・モジュールの抜粋です（プロジェクトルートに src/ 配下で構成される想定）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — 一元的なログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注エンジン周り（Engine, BrokerFactory, OrderManager, RiskManager など）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ロジック）
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
  - data/                    — 実行時に生成される DB ファイルやフラグファイル（data/*.db, data/*.flag）
  - logs/                    — ログ出力先（デフォルト）

設計上の補足
------------
- .env の自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- フェイルセーフ: AI 呼び出しや外部 API エラーは多くの箇所でリトライやフォールバック（ゼロ扱い等）してシステム全体の停止を避ける設計です。
- 冪等性: DB 初期化や market_regime / ai_scores など書き込みは冪等になるよう設計されています（DELETE→INSERT などの扱い）。

トラブルシューティング
---------------------
- ログが出ない / ファイルハンドラ作成に失敗する:
  - LOG_DIR の書き込み権限やディレクトリ作成を確認してください。ログはまず stdout に出力されます。
- 実行が停止する / すぐ終了する:
  - data/stop_requested.flag や data/kill.flag の存在を確認してください。不要なら削除してください。
- 設定検証でエラーが出る:
  - python -m kabusys.validate_config を実行して、指摘に従い .env や config/*.yaml を確認してください。

貢献
----
バグ修正・機能追加はプルリクエストでお願いします。大きな設計変更は issue で事前に相談してください。

ライセンス
----------
（リポジトリに合わせてここにライセンス情報を記載してください）

以上が README の概要です。追加で「デプロイ手順」「systemd / Supervisor 用のサービスユニット例」「具体的な設定例 (.env.example)」などを追加したければ教えてください。