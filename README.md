# KabuSys

KabuSys は日本株の自動売買システムの実装を想定したモジュール群です。取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュース解析などの主要機能を持ち、ローカルの SQLite / DuckDB を使ってデータを管理します。

以下はこのコードベースの概要、機能、セットアップ・使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的：日本株の自動売買運用を支援するためのコンポーネント群（注文管理、リスク監視、ポートフォリオ構築、ファクター計算、ニュースNLP、監視ダッシュボード等）。
- 永続化：SQLite（監視・トレードログ等）および DuckDB（時系列価格・財務データ等）を利用。
- 環境分離：`KABUSYS_ENV` により `development` / `paper_trading` / `live` を切り替え可能。`paper_trading` 時は発注がモック化され、paper_trading 用 DB に記録します（本番 DB と分離）。
- 外部 API：
  - OpenAI（ニュース NLP / レジーム判定で使用） — `OPENAI_API_KEY` が必要。
  - LINE Messaging API（監視アラート送信オプション） — `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID`。
  - kabuステーション 等のブローカ API（実運用時）。

---

## 主な機能一覧

- Execution（発注・注文管理）
  - OrderManager / ExecutionEngine / Reconciler：発注、注文状態同期、再起動時リコンサイル
  - リスク管理（RiskManager）、OrderRepository（SQLite ベース）
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク状況、プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文（stale）・約定価格異常検出
  - RiskMonitor：ドローダウン / ポジション上限監視、kill switch（停止フラグ）連携
  - AlertManager：LINE へのプッシュ通知（クールダウン機能あり）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- Portfolio（ポートフォリオ構築）
  - 銘柄選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限・レジーム乗数
- Research（リサーチ/ファクター）
  - momentum / volatility / value 等のファクター計算、将来リターン・IC 計算、統計サマリー
  - DuckDB を用いた SQL + Python 実装
- AI
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント化して ai_scores に書き込み
  - regime_detector: ETF (1321) の MA にマクロニュースセンチメントを合成してレジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順（ローカル開発用・概略）

1. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要パッケージ（抜粋）:
     - duckdb, psutil, requests, streamlit, openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

   ※プロジェクトに requirements.txt がない場合は上記を参考に必要なパッケージを追加してください。

3. .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 代表的な環境変数例:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

4. DB ディレクトリ作成
   - data ディレクトリを作成しておく（スクリプトが自動で作成する場合もありますが確認推奨）。
     - mkdir -p data

---

## 使い方（主要スクリプト）

- Execution Engine を起動
  - 目的：実際の発注ロジックを起動してマーケットとやり取り（paper_trading ではモック）
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録（本番 DB と完全分離）。
    - 起動時に `data/stop_requested.flag` が存在するとエンジンは起動しません。
    - プロセス PID は `data/execution.pid` に書き込まれます。古い PID が存在して死んでいる場合は削除され、アラートログが残ります。

- Monitoring を起動（ポーリング）
  - 目的：システム状態・トレード状態・リスクを定期監視してログ・通知・kill flag を管理
  - 実行:
    - python -m kabusys.run_monitoring
  - 設定:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は `KABUSYS_ENV` に依らず本番用の sqlite_path（Settings.sqlite_path）を使用して監視データを記録します。
  - 停止:
    - プロジェクトルートの `data/stop_requested.flag` を作成するとループを止められます（または Ctrl-C）。

- Streamlit ダッシュボード（監視 UI）
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 監視用 SQLite DB を read-only で開き、ダッシュボードを表示します。

- Paper Trading 検証レポート生成
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD（期間開始）
      - --to YYYY-MM-DD（期間終了）
      - --db PATH（DB パスを指定、環境変数 PAPER_TRADING_SQLITE_PATH があればそれが優先されます）
  - レポート内容:
    - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などの集計と PASS/FAIL 判定

- AI 関連
  - OpenAI を用いる処理（ニュース NLP / レジーム判定）は `OPENAI_API_KEY` が必要です。
  - エンドポイントは内部で OpenAI SDK を用いて呼び出します。API エラーに対してはリトライ・フォールバックを実装していますが、キーは必須です。

---

## 重要なファイル・フラグ

- data/stop_requested.flag
  - run_monitoring.py、run_execution.py がポーリング／実行ループを安全に終了するために監視する旗ファイル。
- data/kill.flag
  - KillSwitch が書き込む停止要請（ExecutionEngine に停止を促すために使用）。
- data/execution.pid
  - ExecutionEngine の PID を記録するファイル。SystemMonitor はこのファイルを見てプロセス生存を確認します（stale PID の自動削除あり）。
- DB ファイル
  - monitoring.db（Settings.sqlite_path のデフォルト: data/monitoring.db） — 監視ログ等
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH のデフォルト: data/paper_trading.db） — paper_trading 専用 DB
  - kabusys.duckdb（DUCKDB_PATH のデフォルト: data/kabusys.duckdb） — 時系列価格等の大規模データ

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の専用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH: pid/kill flag のパス
- PAPER_FILL_MODE: paper_trading のモック注文挙動（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

（パスはリポジトリルート内の `src/kabusys` を想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定読み込み
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py              — DB スキーマ・永続化ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他、broker_factory, execution_engine, order_repository 等が想定)
  - utils/
    - process_priority.py
  - data/ (実行時に生じる)
    - monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, kill.flag, execution.pid

---

## 開発・運用上の注意

- .env の自動読み込み：
  - プロジェクトルートを .git または pyproject.toml ベースで検出し、`.env` / `.env.local` を読み込みます。OS 環境変数が優先されます。
  - テストなどで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading：
  - `KABUSYS_ENV=paper_trading` 時はブローカークライアントがモックになり、データは専用 DB に保存されます。実運用 DB を汚染しません。
- OpenAI：
  - AI 機能は OpenAI API キーが必要です。API 呼び出しは JSON モードで行われ、429 / ネットワーク断 / 5xx に対してはリトライを行う実装です。
- 権限・優先度設定：
  - 起動スクリプトはプロセス優先度（high 等）を設定しようとします。権限不足で失敗するケースがあるため、その場合はログに警告が出ますが起動自体は継続します。
- フラグファイル：
  - 停止制御はフラグファイル（data/stop_requested.flag, data/kill.flag）で行います。手動操作で停止させたい場合はこれらを作成・削除してください。

---

この README はコードベースの主要な使い方・構成をまとめたものです。実際に運用する場合は環境ごとの設定（API キー、DB のバックアップ、ログ管理、プロセス監視など）を適切に行ってください。必要ならば各モジュール（ExecutionEngine、RiskManager、OrderRepository 等）の詳細ドキュメントを別途作成できます。