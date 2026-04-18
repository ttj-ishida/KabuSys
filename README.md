# KabuSys

日本株自動売買システムのコードベース。戦略・ポートフォリオ構築・実行エンジン・監視・研究用ユーティリティを含むモジュール群です。

> 現バージョン: 0.1.0

## プロジェクト概要
KabuSys は日本株の自動売買に必要な以下の機能を提供する Python パッケージです。

- データ解析・ファクター計算（DuckDB を用いる）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine（ブローカーとの発注・注文管理・リスク制御）
- 監視（システム稼働状況・注文状況・リスク監視）および Kill Switch
- AI を用いたニュースセンチメント評価（OpenAI）
- ペーパートレード用の分離された DB と検証レポート生成ツール
- 開発支援 CLI（.env ウィザード、設定検証）

設計上、実行系と研究系／分析系は分離されており、ペーパートレード時は本番 DB を汚さないよう専用の SQLite を使います。

---

## 主な機能一覧
- 環境管理
  - .env の自動読み込み（プロジェクトルートに基づく） / 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- ログ管理
  - 統一的な logging 設定（コンソール stdout + 日次ローテートファイル出力）
- 実行エンジン
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV による paper_trading／live の切替）
  - PID ファイル管理 / stop フラグ検出で安全停止
- 監視
  - run_monitoring: SystemMonitor のポーリングループ
  - MonitoringEngine：System / Trade / Risk 各 Monitor の統合とアラート・Kill Switch 評価
  - 監視情報は SQLite（monitoring.db）へ永続化
- ポートフォリオ構築
  - 候補選定・等分/スコア加重・リスクベースの単元丸めなど
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC、統計サマリなど
- AI（ニュースNLP / レジーム判定）
  - OpenAI API を使ったニュースセンチメント（ai.news_nlp）
  - ETF + マクロニュースを用いた市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発マシン向けの基本手順）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 主要依存例:
     - duckdb, psutil, openai, PyYAML (YAML 検証を使う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. .env の準備
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成し、少なくとも下記必須キーを設定:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて OPENAI_API_KEY 等を設定）
   - 自動ロードを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict
6. 初期ディレクトリ / ファイル
   - data/ （SQLite / PID / flag ファイルを格納）
   - logs/ （ログファイル）

---

## 使い方（代表的な実行コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 補足:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
    - 監視は KABUSYS_ENV に関係なく settings.sqlite_path（デフォルト data/monitoring.db）を使用
    - 停止するにはプロジェクトルートの data/stop_requested.flag を作成（存在検出でループ終了）

- 実行（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
    - ExecutionEngine の PID は data/execution.pid に書き込まれる
    - Execution の停止は data/stop_requested.flag を作成するか、Engine 内部で kill.flag（data/kill.flag）を検出する形で行われる

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定可能（または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI スコアリング / レジーム判定はモジュール API を呼び出して使います：
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を利用

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレードの約定挙動、instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数上書き）
- KILL_FLAG_CLEAR_ON_START（本番での kill.flag 自動クリアを制御: "0" or "1"）

自動 .env ロードはプロジェクトルートの .env と .env.local を読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## Kill / Stop フラグと停止挙動
- data/stop_requested.flag
  - run_monitoring と run_execution が監視している停止フラグ。作成されると安全にループ／エンジンを終了します。
- data/kill.flag
  - KillSwitch（監視側）が生成する停止指示フラグ。ExecutionEngine は起動時にこのフラグをチェックし、存在する場合は起動せずまたは停止処理を行います。
- PID ファイル
  - data/execution.pid（ExecutionEngine 用）

KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアする挙動になります（本番では 0 を推奨）。

---

## ログ
- デフォルト出力先: stdout（コンソール）とファイル logs/<app_name>.log（日時ローテート、30 日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一設定されます。
- ログディレクトリを変更する場合は環境変数 LOG_DIR を設定可能。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールの一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ヘルパ
  - monitoring/
    - monitoring_db.py       — SQLite 用監視 DB 永続化層
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （注文関連の監視ロジック）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — Monitor をまとめるエンジン
    - alert_manager.py       —（アラート送信ロジック）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文履歴の永続化
    - risk_manager.py        — 発注リスク制御
    - reconciler.py          — ブローカーとの差分解消ロジック
    - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算 / 単元丸め
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（実際のツリーはリポジトリの内容に依存します。上は主要ファイルの抜粋です。）

---

## 開発上の注意 / 実行時ガイド
- run_monitoring は MONITOR_POLL_INTERVAL で制御されるポーリングループです（デフォルト 60 秒）。
- Monitoring は環境に依らず監視用 sqlite_path（settings.sqlite_path）を使用します。Execution は paper_trading の場合に paper_sqlite_path を使用して DB を分離します。
- OpenAI API を使用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・バックオフやフェイルセーフ（失敗時は 0.0 を利用）を備えていますが、API 利用制限やコストに注意してください。
- .env を絶対に Git リポジトリにコミットしないでください（config_setup のヘッダーにも注意書き有り）。
- SQLite / DuckDB ファイルは data/ 以下に置くことを想定していますが、環境変数でパスを上書きできます。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。validate_config は live 向けの注意点を警告します。

---

## よく使うコマンド（まとめ）
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: python -m kabusys.run_monitoring
- 実行開始: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要があれば README に「開発者向けの詳細セットアップ」「ユニットテストの実行方法」「依存関係の固定方法(requirements.txt)」などを追記できます。どの情報を追加しますか？