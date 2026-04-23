KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買（バックテスト／ペーパートレード／本番運用）と、それを支えるモニタリング・リサーチ・AIユーティリティ群をまとめた Python パッケージです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: 実際の発注（live）またはモック発注（paper_trading）
- Monitoring（監視）: システム稼働／注文状況／リスク監視、Kill Switch
- Portfolio モジュール: 銘柄選定・重み付け・単元丸め・ポジションサイジング
- Research モジュール: ファクター計算／特徴量探索
- AI モジュール: ニュース NLP（LLM を使ったセンチメント）・レジーム判定
- ユーティリティ: 設定ウィザード、設定検証、レポート生成 等

主な機能
--------
- 環境ごとに分離された DB（本番とペーパーは SQLite のファイルで分離）
- ExecutionEngine の安全停止（kill.flag / stop_requested.flag）
- System / Trade / Risk のモニタリングとアラート送信フック
- ポートフォリオ構築（候補選定、等配分・スコア加重、リスクに基づく配分）
- ポジションサイズ計算（単元丸め、aggregate cap、コストバッファ）
- DuckDB を使ったファクター計算（Momentum / Volatility / Value）
- OpenAI API を使ったニュースセンチメント集約（ai/news_nlp.py）
- Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- 対話式 .env 作成ウィザード（kabusys.config_setup）および起動前検証ツール（kabusys.validate_config）

前提・必須ライブラリ
-------------------
主に以下が必要です（環境により差分あり）。
- Python 3.9+
- duckdb
- openai
- psutil
- PyYAML（config 検証時に YAML 検査を行う場合）
- （標準ライブラリ）sqlite3, logging, threading 等

インストール例（仮）
- 仮想環境作成後:
  pip install duckdb openai psutil PyYAML

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリを移動
   - git clone ... && cd <repo>

2. Python 仮想環境を作成して依存関係をインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install duckdb openai psutil PyYAML

3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
     ← プロンプトに従い J-Quants, kabu API パスワード等を入力して .env を生成します。
   - もしくは手動で .env を作成（下記「環境変数一覧」参照）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit 1）になります:
     python -m kabusys.validate_config --strict

5. データディレクトリの準備（必要なら）
   - デフォルトで data/ 以下に DB やフラグファイルが置かれます。必要があれば作成しておいてください（logging で logs/ ディレクトリも使用）。

主要な環境変数（代表）
--------------------
（.env に設定する項目の要約）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要（任意やデフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live). デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（monitoring.db）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading.db）。デフォルト: data/paper_trading.db
- OPENAI_API_KEY — OpenAI API キー（AI モジュール実行時）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant/partial/never/reject）。デフォルト: instant
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（0/1）。本番では 0 推奨

起動 / 使い方
------------

- ExecutionEngine（発注エンジン）を起動
  - 簡単スタート:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 説明:
    - paper_trading 環境では MockBrokerClient を使用し、データは data/paper_trading.db に保存され本番 DB と分離されます。
    - run_execution は起動時に data/stop_requested.flag をチェックし、あれば起動せず終了します。
    - 実行中の PID は data/execution.pid に書き込まれます。
    - 停止シグナルは data/stop_requested.flag または data/kill.flag を使って送ることができます（Kill Switch は monitoring 側から書き込みます）。

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず監視 DB は同じパスを参照する設計）。
  - run_monitoring は data/stop_requested.flag を検知してループを抜けます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。
  - 出力は標準出力にレポートを表示します（稼働率・注文成功率・レイテンシ等）。

- AI（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - モジュール関数をアプリケーションから呼び出して利用します（CLI スクリプトは同梱していません）。
    例（Python）:
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key="sk-...")
    または
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key="sk-...")
  - エラーハンドリングやリトライロジックは内部で実装されています。APIキー未指定時は ValueError を送出します。

ログ
---
- setup_logging() により、標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/ を使用します。

プロセス制御 / フラグファイル
----------------------------
- stop_requested.flag: run_monitoring/run_execution がシャットダウンを検知するフラグファイル（data/stop_requested.flag）。
- kill.flag: Kill Switch（監視が重大問題を検出した場合に ExecutionEngine 停止を指示する）。data/kill.flag
- PID ファイル: data/execution.pid

注意事項 / 運用上のガイド
-----------------------
- KABUSYS_ENV=live の場合は本番発注になります。LINE 通知設定や kill_flag_clear_on_start 等は慎重に設定してください。
- .env はセキュリティ上 Git にコミットしないでください（config_setup でも明記しています）。
- process_priority / cpu_affinity の設定に psutil が必要です。権限不足（AccessDenied）や環境差で設定に失敗する場合がありますが、警告ログを出して処理は継続します。
- OpenAI API 呼び出しはレート制限やネットワークエラーに対してリトライロジックを組み込んでいますが、API 費用や使用量には注意してください。

ディレクトリ構成（主要ファイル）
-----------------------------
以下はパッケージ内の主要なファイル／フォルダ一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (注: 実装ファイルがある想定)
  - utils/
    - logging_setup.py
    - process_priority.py

補足: 開発／拡張
----------------
- DuckDB を使ったファクター計算・Research は DB（prices_daily / raw_financials 等）を前提にしているため、データ投入やスキーマ確認が必要です。
- BrokerClientFactory を用いてブローカー間差異を吸収する設計になっています（paper_trading では MockBrokerClient を利用）。
- 各モジュールは比較的 pure function / 独立性が高く、テストや差し替えが容易です（例えば news_nlp の API 呼び出し内部関数はテストでモック可能）。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE（存在する場合）を参照してください。

問い合わせ / 貢献
-----------------
- バグ・改善提案は Issue を立ててください。プルリク歓迎。

以上。必要があれば README にサンプル .env テンプレートやコマンド例（systemd ユニット／cron での起動例）、より詳細な運用手順（ログローテーション、バックアップ、DB マイグレーション等）を追記します。どの情報を追加したいか教えてください。