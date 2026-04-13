# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群と運用用ツール群です。本リポジトリは注文管理・実行エンジン、監視（Monitoring）機能、ポートフォリオ構成、リサーチ／ファクター計算、AI（ニュースNLP / レジーム判定）連携などを含みます。

---

## プロジェクト概要

- 設計方針
  - 本番環境と Paper Trading を明確に分離（`KABUSYS_ENV` により切替）。
  - DB: 永続化には SQLite（監視/注文ログ）と DuckDB（時系列価格・リサーチ用）を併用。
  - AI 連携は OpenAI（gpt-4o-mini 等）を利用。失敗時はフォールバック（フェイルセーフ）を行う設計。
  - モジュールはできるだけ純粋関数／副作用最小化で実装（テストや解析に有利）。

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - `src/kabusys/run_execution.py` — ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBroker を使用しデータを `data/paper_trading.db` に保存。
- 監視（Monitoring）
  - `src/kabusys/run_monitoring.py` — SystemMonitor ポーリングループを起動。システム状態（CPU/MEM/DISK）、プロセス生存、データ鮮度等を記録。
  - `kabusys.monitoring` パッケージ: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine / SQLite 永続層。
  - Streamlit ダッシュボード: `src/kabusys/monitoring/streamlit_dashboard.py`
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイジング、セクター制約など（純粋関数群）。
- リサーチ（Research）
  - `kabusys.research`：モメンタム・ボラティリティ・バリュー等のファクター計算、前方リターン・IC 計算等。
- AI（ニュースセンチメント / レジーム判定）
  - `kabusys.ai.news_nlp.score_news`：ニュース記事を集約して OpenAI に送り、銘柄単位のセンチメントを `ai_scores` テーブルへ書込。
  - `kabusys.ai.regime_detector.score_regime`：ETF（1321）MA とマクロニュースを合成して market_regime を決定。
- 運用ツール
  - `src/kabusys/tools/paper_verification_report.py`：Paper Trading DB を集計して検証レポートを表示。

---

## 必要条件（主な依存）

以下はコードからの主要依存ライブラリ（バージョンは環境に合わせて調整してください）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- （SQLite 標準ライブラリは組込み）

実際はプロジェクトの requirements.txt がある場合はそちらを使用してください。

---

## インストール / セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存のインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限:
     - pip install duckdb psutil requests openai streamlit

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし OS 環境変数が優先）。
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時に必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ...
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用、未設定なら通知は行わない）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトは data/ 以下）

   - 例 .env（最低限の雛形）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

5. データディレクトリ作成
   - mkdir -p data

6. DB 初期化
   - スクリプト実行時（monitoring / execution）が接続時に `init_monitoring_db` を呼び出すため、手動初期化は不要です。直接 DB を操作したい場合は `kabusys.monitoring.monitoring_db.init_monitoring_db(sqlite_connection)` を呼んでください。

---

## 実行方法（代表例）

- 監視ループを起動（production で運用する監視）
  - デフォルトのポーリング間隔: 60 秒
  - 環境変数で変更: MONITOR_POLL_INTERVAL
  - 実行:
    - python -m kabusys.run_monitoring
  - 例（間隔を 30 秒に変更）:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

  - 補足:
    - run_monitoring は起動時にプロセス優先度を "high" に設定し、PID ファイルの有無などを利用してプロセス生存監視や stale PID の処理を行います。
    - 監視ログは `SQLITE_PATH`（デフォルト: data/monitoring.db）に保存されます。

- 実行エンジンを起動（Order 実行）
  - python -m kabusys.run_execution
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し DB を `PAPER_TRADING_SQLITE_PATH`（data/paper_trading.db）に分離して保存します。
  - 起動時に ExecutionEngine の依存（ブローカー、OrderRepository、RiskManager 等）を組み立ててセッションを実行します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは read-only モードで SQLite を開き、Positions / Orders / System / Overview を表示します。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - もしくは DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定。

- AI 関連（ライブラリ呼び出し）
  - ニュースセンチメントを生成して DB に書き込む（プログラムから呼ぶ例）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect() の接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  - 注意: OPENAI_API_KEY が未設定だと例外を送出します（score_news/score_regime ともに必須）。

---

## 動作モード・振る舞いの注意点

- KABUSYS_ENV
  - development（デフォルト）、paper_trading、live の 3 種類。
  - paper_trading モードではブローカーがモックになり、本番 DB と分離された `PAPER_TRADING_SQLITE_PATH` を使用します。
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在する場所）を基準に `.env` と `.env.local` を自動読み込みします。
  - OS 環境変数が優先されます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PID / kill.flag
  - ExecutionEngine は PID ファイルを書きます（`Settings.pid_file_path`）。Monitoring は PID の有無・生存確認でプロセス状態を判断します。
  - `KillSwitch` は `Settings.kill_flag_path`（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。flag の存在をクリアしたい場合は `KillSwitch.clear()` を呼ぶかファイルを手動削除してください。
- 監視 DB マイグレーション
  - `init_monitoring_db` は冪等にテーブル作成と簡易マイグレーション（カラム追加等）を行います。手動編集に注意。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env の自動ロード含む）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py — SQLite 永続層・MonitoringDB
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE プッシュ通知（クールダウン実装）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ...（注文管理・同期・リコンシリエーション）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（候補選定・配分・リスク制御）
  - research/
    - factor_research.py, feature_exploration.py（ファクター計算・IC 等）
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 連携、ai_scores に書込）
    - regime_detector.py — レジーム判定（ma200 + macro sentiment）
  - data/  (期待されるデータ保存先、実行時に自動作成されることが多い)
    - kabusys.duckdb (デフォルト)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード用、デフォルト)

---

## 運用上のヒント / 注意点

- OpenAI 連携を運用する場合は API 利用制限（レート・コスト）に注意してください。実装はリトライ（指数バックオフ）やバッチ処理、レスポンス検証を行っていますが、実運用では追加の監視が必要です。
- SQLite を複数プロセスで書き込むと競合が起きるため、同じ SQLite ファイルに複数の書込みプロセスを起動する構成は避けるか、慎重に設計してください。（Paper Trading は本番 DB と分離）
- `set_process_priority("high")` を利用しますが、OS によっては権限が必要になったり無視されることがあります（警告ログが出ます）。
- DuckDB はリサーチ用途の読み取り・集計に便利です。prices_daily / raw_financials / raw_news 等のスキーマに依存する処理が多数あります。

---

## 追加情報 / 開発者向け

- ログレベルは環境変数 `LOG_LEVEL` で制御できます（INFO デフォルト）。
- `kabusys.config.Settings` を通じて設定にアクセスしてください（直接 os.environ を参照するより可搬性が高いです）。
- テストや CI で .env の自動読み込みを抑えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってください。
- 各種機能は単体でインポートして使えるように設計されています（例: factor 計算は DuckDB 接続を受け取り副作用なし）。

---

もし README に記載してほしい追加の運用手順（例: systemd サービス定義、コンテナ化、CI 実行例など）があれば教えてください。必要に応じてサンプル systemd ユニットや Dockerfile も作成できます。