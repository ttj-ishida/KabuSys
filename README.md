# KabuSys — README (日本語)

このリポジトリは日本株向け自動売買／リサーチ基盤の一部を実装した Python パッケージ群です。
以下はコードベースの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群を提供します。主な役割は次の通りです。

- ExecutionEngine（注文実行・リスク管理）
- Monitoring（稼働監視・アラート・Kill Switch）
- Research（ファクター計算・特徴量解析）
- Portfolio（候補選定・配分・サイズ計算）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一例：
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用
- Paper trading は本番 DB と完全に分離（専用 SQLite ファイル）
- LLM 呼び出し（OpenAI）はフェールセーフ（失敗時は安全側フォールバック）
- 直接 datetime.today()/date.today() を参照しないなどルックアヘッドを避ける設計

---

## 主な機能一覧

- 環境設定管理
  - .env の自動ロード・対話的ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）

- 実行・監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用
    - Paper trading 用 DB は data/paper_trading.db（環境変数で上書き可）
  - Monitoring 起動スクリプト（run_monitoring.py）
    - 定期的なポーリングでシステム・注文・リスクを監視
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
    - Kill Switch による停止フラグ生成（data/kill.flag など）
  - Kill Switch：ドローダウンやポジション上限超過で停止フラグを書込む

- データ永続化
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard 等の SQLite スキーマ管理

- リサーチ / ポートフォリオ構築
  - ファクター計算（モメンタム、ボラティリティ、バリュー 等）
  - 将来リターン、IC、統計サマリー
  - 候補選定（score / equal）、重み計算、ポジションサイズ計算、セクターキャップ適用

- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（news_nlp.score_news）
  - マクロ + ETF MA200 を用いた市場レジーム判定（regime_detector.score_regime）
  - 両モジュールとも API キーの有無を考慮したフェイルセーフを含む

- ユーティリティ
  - ロギングセットアップ（Console + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

- ツール
  - Paper Trading 検証レポート（tools/paper_verification_report.py）

---

## セットアップ手順（ローカル開発向け）

1. Python のインストール
   - 対応バージョンはプロジェクトに依存します（少なくとも Python 3.9+ を想定）。
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML は設定検証で YAML の中身チェックを行う場合に必要: pip install pyyaml
   - （その他、プロジェクトで要求されるパッケージがあれば requirements.txt を参照してインストール）
4. ディレクトリ作成（初回）
   - データ・ログディレクトリを作成:
     - mkdir -p data logs
5. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を利用する場合: OPENAI_API_KEY を設定
6. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告も失敗扱いにする

注意:
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時使用）
- 環境変数による上書き: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR, LOG_LEVEL など

---

## 使い方（起動例・主要コマンド）

- 環境設定ウィザード（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存（development / paper_trading / live）
  - paper_trading: MockBrokerClient を用い、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- Monitoring を起動:
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録する

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラム内呼び出し）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  ※ api_key None の場合は環境変数 OPENAI_API_KEY を参照

停止 / 停止シグナル:
- 実行ループ（run_monitoring / run_execution）はプロジェクトルートの data/stop_requested.flag を検出すると終了します。
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch ロジックにより自動で生成される）。

ログ:
- デフォルトのログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または .env で設定（デフォルト INFO）
- ログは stdout と logs/<app_name>.log（日次ローテーション）に出力されます

プロセス優先度:
- 起動スクリプトは最初に set_process_priority("high") を呼びます（OS 権限により失敗する場合は警告のみ）

---

## 主要環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト development）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH — Execution 用 PID / Kill flag のパス

- AI / OpenAI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- その他
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading 時の注文約定モード（instant | partial | never | reject）
  - LOG_DIR, LOG_LEVEL

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部（src/kabusys）の主要ファイル/モジュール構成です。実際のリポジトリのルートに src/ がある前提です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理
    - config_setup.py           — .env ウィザード（対話式）
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        — ロギング初期化ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        — SQLite テーブル定義 / DB ラッパ
      - system_monitor.py       — システム・データ鮮度監視
      - trade_monitor.py        — （注文監視; 実装ファイルあり）
      - risk_monitor.py         — ドローダウン / ポジション上限監視
      - kill_switch.py          — Kill Switch（flag 書き込み）
      - monitoring_engine.py    — 各 Monitor を束ねるエンジン
      - alert_manager.py        — （アラート管理; 実装ファイルあり）
    - execution/
      - execution_engine.py     — ExecutionEngine 本体（実行・セッション管理）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
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
      - news_nlp.py             — ニュース NLP（OpenAI 呼び出し）
      - regime_detector.py      — レジーム判定（MA200 + LLM）
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py

（上記に示していない補助モジュール・ファイルが存在する場合があります）

---

## 開発時の注意点 / 補足

- .env は絶対にリポジトリにコミットしないでください（機密情報を含む）。
- ローカルで OpenAI を試す場合はトークンの使用量に注意してください（API 利用料発生）。
- psutil によるプロセス優先度・CPU affinity 設定は OS 権限に依存します。権限がない場合は警告が出ます。
- DuckDB / SQLite のバージョンや executemany の挙動で細かな互換差分が発生する可能性があります（コード中に互換処理あり）。
- Monitoring と Execution の停止は data/stop_requested.flag を作る・削除することでコントロールできます。Kill Switch は自動的に data/kill.flag を書き込むことがあります（実運用では kill_flag の扱いに注意）。

---

もし README に追加したい詳細（設定のサンプル .env、より具体的な起動手順、依存パッケージの完全なリストなど）があれば教えてください。必要に応じて README を拡張します。