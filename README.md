# KabuSys

日本株自動売買システム（コンポーネント群）のリポジトリ内ドキュメントです。  
このREADMEはコードベース（src/kabusys）をもとに、セットアップ・起動・主要機能・ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数／設定（主要項目）
- 使い方（起動コマンド例）
- 停止・Kill Switch の運用
- ディレクトリ構成（抜粋）
- 開発時メモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムを構成するモジュール群です。  
主に以下の要素を持ちます：

- ExecutionEngine：発注・リスク管理・約定管理を行う実行エンジン
- Monitoring：システム状態・注文状況・リスクを定期的に監視してアラートや Kill Switch を制御
- Portfolio Construction：銘柄選定、重み付け、ポジションサイズ計算
- Research / Factor：DuckDB を用いたファクター計算・解析
- AI モジュール：OpenAI を用いたニュース NLP と市場レジーム判定
- CLI ツール：.env 作成ウィザードや設定検証、Paper Trading 検証レポート等

設計方針として、発注処理（本番）とペーパートレード（分離された DB・モックブローカー）を明確に分離し、安全性（Kill Switch、監視、ログ）を重視しています。

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスク/プロセス状況、データ鮮度の監視
- TradeMonitor：注文の滞留・約定異常など注文周りの監視（コード参照）
- RiskMonitor：ドローダウン／ポジション上限等の監視とリスクログ記録
- KillSwitch：しきい値超過で ExecutionEngine に停止シグナルを送る（flag ファイル）
- ExecutionEngine：Broker クライアントを介した発注、リスク管理、注文リコンシリエーション
- Portfolio モジュール：候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- Research：モメンタム/ボラティリティ/バリュー等のファクター計算、IC 計算、特徴量解析
- AI：ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- tools.paper_verification_report：Paper Trading の検証レポート生成
- config_setup：.env の対話式生成ウィザード
- validate_config：起動前の設定検証 CLI

---

## 必要条件

- Python 3.9+（プロジェクトの Python 要件に合わせてください）
- 推奨パッケージ（最低限、実行に必要なもの）：
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイル検証時に推奨）
- その他：SQLite 標準ライブラリ（Python に含まれます）

インストールは仮想環境を作成して依存パッケージを pip で入れてください。

例：
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

（requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順（概要）

1. リポジトリをクローンしてワークディレクトリへ移動。
2. 仮想環境を作成・有効化。
3. 依存パッケージをインストール（上記参照）。
4. .env を生成（対話式ウィザード推奨）：
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabu API 等の必須値を対話的に聞きます。
5. 設定を検証：
   - python -m kabusys.validate_config
   - 問題があれば修正してください（--strict を指定すると警告も FAIL 扱い）。
6. 必要なディレクトリを作成（logs, data 等は起動時に作成されることが多いですが事前作成しておくと安心です）：
   - mkdir -p data logs

注意：
- monitoring 起動時・execution 起動時に SQLite / DuckDB ファイルが作成・初期化されます（init_monitoring_db 等）。
- paper_trading モード（KABUSYS_ENV=paper_trading）は監視 DB と本番 DB を分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。

---

## 主要環境変数（抜粋）

Settings クラスで定義されている主要な環境変数とデフォルト値の一部を示します。

- 必須（起動前に .env に設定してください）
  - JQUANTS_REFRESH_TOKEN（J-Quants API トークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）

- 実行環境
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）

- ログ/DB
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading の専用 sqlite、デフォルト: data/paper_trading.db）

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

- その他
  - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START（本番環境で auto-clear を有効にするか、0/1）

詳細は src/kabusys/config.py を参照してください。

---

## 使い方（起動例）

各種エントリポイントはパッケージモードで実行できます（プロジェクトルートで実行）。

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告もエラー扱い

- 監視ループ（SystemMonitor の定期実行）
  - 環境変数でポーリング間隔を上書き可能：
    export MONITOR_POLL_INTERVAL=30
  - 実行：
    python -m kabusys.run_monitoring
  - 補足：
    - 監視は常に本番用 sqlite_path を参照します（KABUSYS_ENV に依存せず）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することでループを終了します（外部制御ファイル）。

- ExecutionEngine（発注実行）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に取引ログを記録します（本番 DB と分離）。
  - 実行：
    python -m kabusys.run_execution
  - 起動時に stop flag が既に存在する場合は起動を中止します。
  - 実行中に同ファイルが作成されるとエンジンは安全に停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / Research の利用
  - OpenAI を使う機能（news_nlp, regime_detector）を使用する場合は OPENAI_API_KEY を設定してください。
  - それぞれのモジュールは DuckDB 接続を受け取って動作します（直接関数を呼び出して利用可能）。

---

## 停止・Kill Switch 運用

- stop_requested.flag（プロジェクトルート/data/stop_requested.flag）
  - run_monitoring / run_execution の外部停止用フラグ。存在すると両ループとも次回確認時に停止します。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch により書き込まれるファイル。ExecutionEngine を停止させるために監視側（RiskMonitor 等）が書き込みます。既存の場合は再書き込みしません（冪等）。
- PID ファイル
  - ExecutionEngine 起動時は data/execution.pid（設定可能）へ PID を書きます。

運用上の注意：
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。自動クリア設定は危険を伴います。

---

## ログ

- setup_logging により、コンソール（stdout）と日次ローテートされたファイル（logs/<app_name>.log）へ出力されます。
- ログ出力ディレクトリは LOG_DIR 環境変数もしくはデフォルト logs/ を使用します。
- ファイルハンドラ作成に失敗するとコンソールのみで継続します。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブモジュール（抜粋）
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続層（監視ログ）
  - system_monitor.py
  - trade_monitor.py       — （コード上存在する想定モジュール）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （通知管理: LINE など）
- execution/
  - execution_engine.py    — 実行エンジン本体（EngineConfig 等）
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
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
- tools/
  - paper_verification_report.py

（上記は主要モジュールの抜粋です。細かい実装は各ファイルを参照してください。）

---

## 開発時メモ / よくある質問

- DB 初期化
  - monitoring と execution 起動時に必要なテーブルは自動で作成（init_monitoring_db）されます。
- paper_trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading のとき、ExecutionEngine は PAPER_TRADING_SQLITE_PATH を使い、本番の monitoring.db と分離してログを残します。
- OpenAI 呼び出し
  - レート制限や一時エラーは指数バックオフでリトライする実装がありますが、API キーは必ず設定してください。
- テスト
  - 各種外部 API 呼び出し（OpenAI、ブローカークライアント等）はモック可能な設計です（テスト用に _call_openai_api を patch する等）。

---

必要に応じて README に追加したい内容（例：デプロイ手順、systemd ユニット例、Dockerfile、監視ダッシュボード例）があれば指示してください。コードの別ファイルについても同様に要約を追加できます。