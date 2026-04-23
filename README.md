# KabuSys

日本株向け自動売買システムの一部コンポーネント群（設定管理、実行エンジン起動スクリプト、監視、研究/ファクター計算、AI 補助モジュール、ポートフォリオ構築ユーティリティなど）。

※ このリポジトリはフルシステムの一部実装を含みます。発注ロジックやブローカー実装は別モジュール（BrokerClientFactory 等）に依存します。

## 概要

- 設定管理（.env 読み書き、自動ロード）
- 実行エンジン起動スクリプト（run_execution）
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading DB に記録
- 監視プロセス起動スクリプト（run_monitoring）
  - システム状態・取引状態・リスクを定期ポーリングしてログ・アラート・Kill Switch を管理
- 監視 DB（SQLite）永続化層（monitoring_db）
- リスク監視・Kill Switch・アラート統括（monitoring/*）
- ポートフォリオ構築の純粋関数群（portfolio/*）
- 研究用ファクター計算（research/*） — DuckDB 上の時系列テーブルを参照
- AI 補助（news_nlp / regime_detector） — OpenAI API 呼び出しでニュースのセンチメント等を算出
- 開発支援ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

## 主な機能一覧

- .env の対話式作成・更新（kabusys.config_setup）
- .env / config/*.yaml の事前検証（kabusys.validate_config）
- ExecutionEngine 起動（kabusys.run_execution）
  - 本番 / ペーパートレードの分離（DB・ブローカークライアント）
  - PID ファイル管理、停止フラグ監視
- Monitoring 起動（kabusys.run_monitoring）
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
  - system / trade / risk の各種チェックを行い monitoring DB を更新
  - kill.flag による ExecutionEngine 停止シグナルの発行
- DuckDB を用いた研究用ファクター計算（momentum / volatility / value 等）
- OpenAI API を用いたニュースセンチメント集約（AI スコアの ai_scores テーブルへの書き込み）
- Paper Trading 検証レポート出力（稼働率 / 注文成功率 / レイテンシ など）

## 前提条件

- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config の YAML 検証に使用）
- SQLite（Python 標準ライブラリで利用可能）

インストール例（仮想環境推奨）:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

（requirements.txt があればそれを利用してください）

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします（上記参照）。

2. .env を作成・編集
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルト値）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI を使う場合必須
     - PAPER_FILL_MODE — paper_trading 用のフィルモード（instant|partial|never|reject）, default: instant
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発用）

   注意: .env は決してリポジトリにコミットしないでください。

3. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付ける

4. DB 初期化
   - Monitoring 用 SQLite テーブルは起動スクリプトが自動で作成します（init_monitoring_db）
   - DuckDB に必要なテーブル（prices_daily / raw_financials / raw_news 等）は別スクリプトや ETL で準備してください（研究用）

## 使い方

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - exit code: 0 = OK、1 = FAIL（エラーあり or --strict で警告も FAIL）

- 実行エンジン起動（日次セッション等を実行）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite（デフォルト data/paper_trading.db）を使用し本番 DB と完全分離
    - 起動時に data/execution.pid 等 PID ファイルを作成
    - data/stop_requested.flag (stop フラグ) が存在すると起動を中止またはエンジン停止を行う

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に関係なく同じ監視 DB を使用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使用

- AI モジュール（ニューススコア・レジーム判定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - api_key: OpenAI API キー（引数、または環境変数 OPENAI_API_KEY）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API の呼び出しはリトライやフェイルセーフを実装していますが、API キーが必須です

- ログ
  - デフォルトログディレクトリ: logs/
  - setup_logging により stdout ストリームハンドラと日次ローテートファイルハンドラを設定します
  - 環境変数 LOG_DIR で変更可

## 停止・フラグファイル

- data/kill.flag
  - KillSwitch（監視）により書き込まれると ExecutionEngine は停止されます
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag が自動クリアされます（本番では推奨されません）

- data/stop_requested.flag
  - run_execution / run_monitoring が存在を見てループを終了します（外部からの停止要求用）

- PID ファイル
  - data/execution.pid 等にプロセス ID が書き出されます

## 主要モジュールと役割（簡易）

- kabusys.config — .env 自動読み込み / Settings クラス（環境変数アクセス）
- kabusys.config_setup — .env を対話式に作成/更新
- kabusys.validate_config — 起動前チェック CLI
- kabusys.run_execution — ExecutionEngine 起動スクリプト
- kabusys.run_monitoring — SystemMonitor のポーリング起動スクリプト
- kabusys.monitoring.*
  - monitoring_db — SQLite テーブル定義 / CRUD
  - system_monitor / trade_monitor / risk_monitor — 個別監視処理
  - monitoring_engine — 各 Monitor を束ねてポーリング、KillSwitch 判定・アラート通知
  - kill_switch — 停止フラグ操作ユーティリティ
- kabusys.execution.* — 発注周りのエンジン・オーダー管理（別ファイル実装）
- kabusys.portfolio.* — 銘柄選定・重み付け・ポジションサイズ計算（純粋関数）
- kabusys.research.* — DuckDB ベースのファクター計算 / 特徴量解析
- kabusys.ai.* — OpenAI を用いたニュース NLP / レジーム判定
- kabusys.tools.paper_verification_report — ペーパートレード検証レポート生成
- kabusys.utils.logging_setup — ロギング設定
- kabusys.utils.process_priority — psutil を用いたプロセス優先度 / CPU affinity

## ディレクトリ構成

（リポジトリの src/kabusys を想定した主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    # 実行時に使用される（DB・フラグ・PID 等）
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper_trading)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/                    # デフォルトログ出力先

## 開発・テスト上の注意

- kabusys.config は自動でプロジェクトルートの .env / .env.local をロードします。テストで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）は別途 ETL スクリプトやデータ準備が必要です。research モジュールは DuckDB 上の該当テーブルを前提としています。
- OpenAI API を使用する機能は API キーが必要です。テスト時は内部の API 呼び出し関数をモックする設計になっています（例: unittest.mock.patch）。

## よく使うコマンドまとめ

- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は以上です。必要であれば、環境変数一覧の詳細（各キーの説明とデフォルト値）や起動時のログ出力例、テーブルスキーマ（DuckDB）等の追加節を作成します。どの情報を優先して追記しますか？