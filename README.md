# KabuSys

日本株自動売買システムのコアライブラリ群と実行用スクリプト群のリポジトリです。戦略開発・ポートフォリオ構築・発注エンジン・監視・AI 補助（ニュースセンチメント／レジーム判定）等のコンポーネントを含みます。

---

## 概要

KabuSys は以下を目的とするモジュール群を提供します。

- 株価・財務データを用いたファクター計算・研究（research）
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- 発注実行エンジン（ExecutionEngine、Broker クライアント抽象化）
- 監視コンポーネント（System/Trade/Risk Monitor、Kill Switch、Alert）
- AI によるニュースセンチメント評価・レジーム判定（OpenAI）
- ペーパートレード検証レポート生成ツール

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: python -m kabusys.config_setup
- 起動前設定検証 CLI: python -m kabusys.validate_config
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading DB に書き込む（本番DBと分離）
- 監視（ポーリング）ループ起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視プロセスは常に本番用 sqlite_path を参照（環境に依らず）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI を使ったニュースセンチメント（score_news）・レジーム判定（score_regime）
- DuckDB を用いたファクター計算・特徴量解析
- ログ設定ユーティリティ・プロセス優先度設定ユーティリティなどのユーティリティ群

---

## 必要条件（依存）

代表的な依存ライブラリ（環境により変わります）:

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config 検証で YAML の内容をチェックする場合）

requirements.txt がある場合はそれを使用してください。ない場合は上記を pip でインストールしてください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境作成・有効化（任意）
3. 必要ライブラリをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります
6. データディレクトリの準備（必要に応じて）
   - デフォルト DB / ファイルは data/ 以下に置かれます（存在しない親ディレクトリは自動作成されることがあります）

注意:
- 自動で .env を読み込む機能はデフォルトで有効です（プロジェクトルートの .env を読み込みます）。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主要）

（項目名 — 説明 — デフォルト）

- KABUSYS_ENV — 実行環境: development | paper_trading | live — default: development
  - paper_trading: 発注はモック、paper DB を使用
  - live: 本番
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL — default: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（任意）
- LINE_USER_ID — LINE 通知先（任意）
- DUCKDB_PATH — DuckDB ファイルパス — default: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite DB — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite DB — default: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） — default: INFO
- LOG_DIR — ログ出力ディレクトリ — default: logs/
- PID_FILE_PATH / PID 関連 — default: data/execution.pid
- KILL_FLAG_PATH — kill.flag のパス — default: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1） — default: 0
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒） — default: 60
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject） — default: instant
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時に必要）

例 .env（抜粋）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（起動 / コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 発注エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知して停止します
  - 実行中は PID ファイル（デフォルト data/execution.pid）が作成されます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しません）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知して終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- AI / Research のプログラム的利用例
  - Python スクリプト内でインポートして使用可能（DuckDB 接続を渡す）
    - from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key=...)
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=...)
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns 等

---

## 停止・Kill Switch（安全機構）

- stop_requested.flag
  - run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag の存在を監視し、存在すれば安全終了します（外部から停止するためのフラグ）。
- kill.flag
  - KillSwitch は監視結果（DR awdown やポジション上限など）に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## ログ・DB パス

- ログ:
  - デフォルト出力先: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30日分保持）
  - コンソール出力は stdout に出ます
  - ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")

- DB:
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - 監視用 SQLite: data/monitoring.db（Settings.sqlite_path）
  - ペーパートレード SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

---

## ディレクトリ構成（概要）

リポジトリ内の主なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py            — ニュースセンチメントスコア（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py       — 監視用 DB 永続化層
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知ハンドラ）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算 / スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - execution/               — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - data/                    — 実行時の DB / フラグ / PID 等（data/*.db, data/*.flag, data/*.pid）

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 開発時の注意点 / 補足

- .env は絶対にリポジトリにコミットしないでください（機密情報を含む）。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に行ってください。validate_config は本番向けの簡易ガードを含みます（LINE 通知設定の確認や kill flag クリア設定の警告など）。
- AI モジュールを動かすには OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフを備えていますが、API 料金やレート制限に注意してください。
- monitoring は監視用 DB（SQLITE_PATH）を用いるため、複数プロセスで同一ファイルを扱う場合は注意が必要です（ロック等）。
- duckdb を利用したリサーチ関数群は DuckDB 接続を受け取り SQL を発行します。大規模データを扱う際はメモリ・I/O を考慮してください。

---

必要であれば、README にサンプル .env の完全例、systemd / supervisor 用の起動ユニット例、または Docker 化の手順（Dockerfile / docker-compose）なども追加できます。追加希望があれば教えてください。