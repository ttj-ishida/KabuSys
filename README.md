# KabuSys

日本株向け自動売買プラットフォームの一部を切り出したコードベースの README（日本語）。

このリポジトリは、戦略・ポートフォリオ構築、発注実行エンジン、監視、AI を使ったニュース評価・レジーム判定、各種ツール類を含むモジュール群で構成されています。実運用・ペーパートレード双方を想定した設計になっています。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのライブラリ群および起動スクリプト群です。主な要素は次のとおりです。

- ExecutionEngine（発注エンジン）と BrokerClientFactory による発注処理（本番 / ペーパートレード対応）
- Monitoring（System / Trade / Risk モニタ）による定期監視、kill-flag による安全停止
- Portfolio コンポーネント（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- Research（ファクター計算・特徴量探索）
- AI モジュール：ニュースセンチメント評価・市場レジーム判定（OpenAI を使用）
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定、紙上検証レポート等

設計方針として「DBや外部 API への不要なアクセスを避ける」「ルックアヘッドバイアスを起こさない」「失敗時は安全側にフォールバックする」ことが繰り返し採用されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py : SystemMonitor をポーリングで回す監視プロセス
- 設定関連
  - config_setup.py : .env 対話式ウィザード（.env の作成/更新）
  - validate_config.py : 環境変数 / config/*.yaml の検証 CLI
- モニタリング
  - system_monitor, trade_monitor, risk_monitor をまとめる MonitoringEngine
  - kill_switch による停止フラグ（data/kill.flag）書き込み
  - monitoring_db: SQLite に永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築
  - 候補選定（スコアソート）、等金額 / スコア加重、およびポジションサイズ算出（lot 単位）
  - セクター集中除外、レジーム乗数
- リサーチ
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp: raw_news を LLM でスコア化して ai_scores に保存
  - regime_detector: マクロ記事 + ETF MA200 を組み合わせてレジーム判定
- ツール
  - tools/paper_verification_report.py : ペーパートレード DB の検証レポート生成

---

## セットアップ手順（開発環境）

以下は開発・実行に必要な基本手順です。プロジェクトルートがパッケージとして扱えることを前提としています（src 配下）。

1. Python 仮想環境を作成・有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は、以下を目安にインストールしてください。

     pip install duckdb psutil openai

   - 追加（任意）
     - PyYAML（config/*.yaml の検証を行う場合）: pip install pyyaml

   - 注: 実行する機能により必要パッケージは異なります（AI 関連は openai が必須）。

3. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定してください。
   - 対話式で作る場合:

     python -m kabusys.config_setup

   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)

   - 代表的な設定（.env あるいは環境変数）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（AI 機能で必須）
     - KILL_FLAG_CLEAR_ON_START: 0 | 1（起動時に kill.flag を自動クリアするか）

4. データディレクトリ
   - デフォルトでは data/ および logs/ を使用します。スクリプトが開始時に自動作成することもありますが、実行前に作成しておいてもよいです。

---

## 使い方

基本的にはパッケージ経由で Python モジュールを実行します（パッケージとしてインストール済み、あるいはパスが通っている前提）。

- 設定ウィザード（.env を生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする場合:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 停止には data/stop_requested.flag を作成（または kill.flag の存在を検出して動作する一部コンポーネントあり）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に書き込みます（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中の停止は data/stop_requested.flag を作ることでエンジン停止シグナルを送れます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（プログラムから利用）
  - news スコアリング（DuckDB 接続が必要）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key None の場合 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

  注意: AI モジュール呼び出し時は OPENAI_API_KEY の有無を確認してください。未設定だと ValueError が発生します。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH などは Settings 経由で確認可能（デフォルトは data 内）

---

## 停止・フラグ関連

- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に停止指示を出す用途のフラグ。
  - KillSwitch はリスク条件（ドローダウン超過、ポジション数上限等）に応じてこのファイルを書きます。

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py がチェックする「停止要求」フラグ（存在すればループを抜けて終了）。

- data/*.pid
  - ExecutionEngine 起動時に PID を書く仕組みがあり、PID ファイルのパスは Settings で指定します。

---

## トラブルシューティング（よくある注意点）

- OpenAI 関連
  - OPENAI_API_KEY が未設定だと news/regime の各関数は ValueError を送出します。テスト時は環境変数に設定してください。
  - API 呼び出しはリトライとフェイルセーフが組まれていますが、レート制限や 5xx はログを参照してください。

- DB パス
  - .env の DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合、validate_config は警告を出します（起動時に自動作成されることもあるため）。必要に応じて事前作成してください。

- ログ
  - デフォルトでは logs/ に日次ローテートでログが出力されます。LOG_DIR 環境変数で変更可能です。ログディレクトリ作成に失敗するとコンソール出力のみになります。

- 権限
  - psutil によるプロセス優先度変更や CPU affinity 設定は権限により失敗することがあります。失敗時は警告ログによりスキップされます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 下の主なファイル・ディレクトリの構成概略です。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py           (存在する場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

（この README はリポジトリ内のソースコードから要点をまとめたドキュメントです。各モジュールの詳細な使用法・引数・戻り値は該当ソース内の docstring を参照してください。）

---

必要に応じて、特定のモジュールの詳細な使い方や API のサンプルを追加で作成します。どの機能について詳しく知りたいか教えてください。