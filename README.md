KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
---
KabuSys は日本株自動売買システムのコードベースです。主に以下の責務を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント（実売買 / ペーパートレード）
- 監視（System / Trade / Risk）と Kill Switch（異常検知時の発注停止）
- ポートフォリオ構築（銘柄選定・配分・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- ユーティリティ（ログ設定・プロセス優先度設定 等）

この README はリポジトリに含まれる主要スクリプト・設定方法・使い方・ディレクトリ構成を日本語でまとめたものです。

主な機能一覧
-------------
- Execution
  - 実口座 / ペーパートレード（KABUSYS_ENV=paper_trading で MockBroker を利用）
  - 発注管理、リスク管理（Rate limit, max position, drawdown など）
- Monitoring
  - CPU / メモリ / ディスク / プロセス稼働チェック
  - 注文ログ（trade_logs），ポジション（positions），リスクログ（risk_logs），ダッシュボード（dashboard）永続化（SQLite）
  - Kill Switch：所定条件（ドローダウン・ポジション上限等）で停止フラグを立てる
- Portfolio construction
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（lot 切り上げ・aggregate cap）
- Research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（OpenAI を利用）
  - ニュース記事のセンチメントスコア化（ai_scores テーブルへ保存）
  - マクロニュース＋ETF MA200 を使った市場レジーム判定（market_regime テーブル）
- ツール
  - 設定ウィザード（.env 作成）: kabusys.config_setup
  - 設定検証 CLI（.env / config/*.yaml の軽い検証）: kabusys.validate_config
  - Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report

セットアップ手順
----------------
前提:
- Python 3.10 以上（typing の "|" 表記等を使用しているため）
- システムによっては psutil のインストールにビルドツールが必要になることがあります

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai psutil pyyaml
   - （実行環境・テストに応じてその他パッケージが必要になる場合があります）

3. プロジェクトルートに .env を作成
   - 自動で作るには対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - 任意・デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合に必要

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

5. データディレクトリ・ログディレクトリの確認
   - デフォルトの DB / PID / flag / logs は project_root 以下の data/ と logs/ に作られます。
   - 例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, logs/

使い方（代表コマンド）
--------------------
- 実行エンジンを起動（出力ログ: logs/execution.log）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます

- 監視（Monitoring）ループを起動（監視ログ: data/monitoring.db, DuckDB: data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（monitoring は常に指定された sqlite_path を使います）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb.DuckDBPyConnection
    - target_date: datetime.date（ニュースウィンドウは target_date の前日 15:00 JST 〜 当日 08:30 JST）
    - api_key を渡すか OPENAI_API_KEY 環境変数を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - OpenAI を使うため APIキーが必要

停止・Kill/Stop の挙動
---------------------
- run_monitoring.py / run_execution.py はプロジェクトルートの data/stop_requested.flag を監視しています（このファイルが存在するとループを終了します）。
  - 停止させたい場合はプロセス外から stop_requested.flag を作成すると安全にシャットダウンします。
- Kill Switch（監視側）が発動すると data/kill.flag が書き込まれ、ExecutionEngine に停止を促します。kill.flag は設定（Settings.kill_flag_clear_on_start）によって起動時に自動クリア可能ですが、本番では 0 を推奨します。
- ExecutionEngine は data/execution.pid に PID を書き出します（プロセス管理・監視に使用）。

ログ
---
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
  - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（logs/<app_name>.log）を設定
  - 環境変数 LOG_DIR / LOG_LEVEL をサポート
  - デフォルトのログディレクトリ: logs/

重要な環境変数（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨・よく使うもの:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必須）
- LOG_LEVEL（デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）

ディレクトリ構成（主なファイル）
-----------------------------
リポジトリの重要なファイル・モジュールを抜粋しています（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート (CLI)
  - utils/
    - logging_setup.py        — 共通ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 & 永続化 API
    - monitoring_engine.py    — 複数 Monitor を束ねるエンジン
    - system_monitor.py       — システム / データ鮮度チェック
    - trade_monitor.py        — 注文滞留・約定異常監視（実装あり）
    - risk_monitor.py         — ドローダウン・ポジション上限チェック
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — （通知送信等の抽象）
  - execution/
    - execution_engine.py     — 発注実行エンジン（EngineConfig, run_session 等）
    - broker_factory.py       — ブローカークライアント生成（Mock / Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum / value / volatility）
    - feature_exploration.py  — forward returns / IC / summary
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores 書込み）
    - regime_detector.py      — マクロ＋ETF MA によるレジーム判定

補足／設計上の注意点
-------------------
- Paper Trading は本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視は監視用 SQLite（SQLITE_PATH）へログを残します。init_monitoring_db() によりテーブル作成と軽微なマイグレーションを行います（冪等）。
- AI 機能は OpenAI API を使用します。API 呼び出しではリトライやレスポンス検証を行い、失敗時はフォールバック（例: macro_sentiment=0.0）してシステム全体の停止を避ける設計です。
- プロセス優先度設定（set_process_priority）やログ設定（setup_logging）は各起動スクリプトから呼ばれるため、環境に応じて権限の調整が必要な場合があります。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報・貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
-----
不明点や追加したいドキュメント（設定項目の詳細、API 仕様、運用手順など）があれば指定してください。README に追記・改善します。