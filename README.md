# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
バックテスト・ポートフォリオ構築、実行エンジン、監視・アラート、AIによるニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の主要機能を持つモジュール群で構成された自動売買システムです。

- 戦略 / ファクター計算（DuckDB を用いた価格データ参照）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 発注実行エンジン（本番 / ペーパートレード切替）
- 監視（プロセス健全性、注文滞留、ドローダウン等の検出）
- アラート（LINE Push）
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、運用での安全性（フェイルセーフ、冪等性、部分失敗時の保護）やルックアヘッドバイアス回避に配慮しています。

---

## 主な機能一覧

- portfolio
  - select_candidates, calc_equal_weights, calc_score_weights（候補選定・重み付け）
  - calc_position_sizes（株数決定・単元丸め・資金スケーリング）
  - apply_sector_cap, calc_regime_multiplier（セクター制限・レジーム乗数）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- execution
  - ExecutionEngine（本番 / paper_trading 切替、Broker クライアントファクトリ）
  - OrderRepository / OrderManager / RiskManager / Reconciler
- monitoring
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（各 Monitor の統合ループ）
  - KillSwitch（閾値超過時に stop フラグの書込）
  - AlertManager（LINE Push 一方向通知、クールダウン管理）
  - SQLite ベースの監視 DB（monitoring_db.py）
- ai
  - news_nlp.score_news（ニュースを LLM にかけて銘柄別スコア化、ai_scores へ書込）
  - regime_detector.score_regime（ETF MA と LLM マクロセンチメントを合成して日次レジーム判定）
- tools
  - config_setup（.env 対話式ウィザード）
  - validate_config（.env / config/*.yaml の事前検証）
  - paper_verification_report（ペーパートレード DB から Pass/Fail レポートを生成）

---

## 必要要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- （任意）PyYAML（config/*.yaml の内容検証に使用）

インストール例:
- pip install duckdb psutil requests openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを配置
2. Python 環境と依存パッケージをインストール
3. .env を準備
   - 対話式ウィザードで簡単に作成:
     - python -m kabusys.config_setup
   - 自動ロード: .env（および .env.local）はプロジェクトルートに置くと自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - .env は絶対に Git にコミットしないでください。
4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります
5. データベースファイル:
   - デフォルトの DB パス（必要に応じて .env で変更）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - 初回起動時に必要なディレクトリがない場合は自動作成されることがあります（スクリプト内メッセージ参照）

必須環境変数（の例）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）

設定ウィザードで扱う項目の一部:
- KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
  DUCKDB_PATH, SQLITE_PATH, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START

---

## 使い方（起動コマンド例）

python モジュールとして実行できます（プロジェクトルートで実行）。

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
    - 実行中は data/execution.pid が作成され、停止はファイルフラグで制御されます（後述）。
    - 起動前に data/stop_requested.flag が存在する場合は起動しません。

- 監視プロセス（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に依らず、本番 sqlite_path（SQLITE_PATH）を使用して監視ログを残します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使って DB パスを指定できます（コマンドライン引数が優先）。

- AI 機能（ライブラリ呼び出し）
  - kabusys.ai.score_news（DuckDB 接続と target_date を渡して呼び出す）
  - kabusys.ai.regime_detector.score_regime（同上）
  - 実行には OPENAI_API_KEY の設定が必要（引数として API key を渡すことも可能）

---

## プロセス制御（ファイルベースの停止 / Kill Switch）

- 停止要求（run_execution, run_monitoring のループを止める）:
  - data/stop_requested.flag を作成すると、起動中の監視・実行ループが検知して終了します。
- ExecutionEngine の停止シグナル（安全装置）:
  - KillSwitch は監視ルール（ドローダウン超過、ポジション上限超過等）を満たした場合、data/kill.flag を書き込みます。ExecutionEngine はこのファイルを参照して停止するようにしています。
  - Settings.kill_flag_clear_on_start = 1 を設定すると起動時に kill.flag を自動クリアします（本番ではデフォルト 0 を推奨）。
- PID ファイル:
  - data/execution.pid（ExecutionEngine が実行中の PID を書き込む）

---

## 主要環境変数（抜粋とデフォルト）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0 | 1（default: 0）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（run_monitoring 用）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の Mock fill 挙動）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）

.env 例は config_setup が生成するテンプレートを参照してください。

---

## 注意点 / 実運用向けのポイント

- Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（SQLITE_PATH）を使用します。監視ログは本番 DB に常に記録されます。
- paper_trading モードでは発注先を MockBroker に差し替え、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
- AI 機能は外部 API（OpenAI）に依存します。API 呼び出しの失敗時にはフェイルセーフ（スコア 0.0 やスキップ）で継続する設計です。
- .env ファイルには機密情報（API トークン等）を含みます。絶対に Git にコミットしないでください。
- プロセス優先度や CPU affinity の設定は psutil を使って行っています。権限不足等で設定できない場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス（自動 .env ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - utils/
    - __init__.py
    - process_priority.py

（上記は本リポジトリに含まれる主要なモジュールの抜粋です。詳細はソースファイルを参照してください）

---

## 追加コマンド / 開発時のヒント

- 開発環境で .env の自動ロードを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 設定の問題を事前にチェック:
  - python -m kabusys.validate_config
- .env の初期作成:
  - python -m kabusys.config_setup
- Paper Trading の運用検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に追加する「サンプル .env」「systemd / supervisor のサービス定義例」「よくあるトラブルシュート」などのセクションも作成できます。どの情報を追加しますか？