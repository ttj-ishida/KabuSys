# KabuSys — README (日本語)

本リポジトリは日本株向けの自動売買・研究・監視プラットフォーム「KabuSys」の軽量実装です。本 README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は次の主要なコンポーネントを備えたシステムです。

- 注文発行と状態管理を行う ExecutionEngine（実取引・ペーパートレード対応）
- システム稼働・注文状態・リスクを監視する MonitoringEngine
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター上限）
- ファクター計算・リサーチユーティリティ（DuckDB 経由）
- ニュースを LLM（OpenAI）でスコアリングして AI 指標を生成
- 市場レジーム判定（MA とマクロセンチメントの合成）
- 管理ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

設計方針として、DB はローカルの SQLite / DuckDB を使用し、LLM 呼び出しはフェイルセーフ（失敗時はフォールバック）で安全性を重視した実装になっています。

---

## 機能一覧（抜粋）

- Execution
  - 実際のブローカーまたは MockBroker を使った発注
  - リコンシリエーション（再起動時の自動同期）
  - 注文状態の永続化（SQLite）
  - リスク管理（最大ポジション比率、ポジション数、ドローダウン等）

- Monitoring
  - CPU / メモリ / ディスク使用率のログ化
  - Execution プロセス生存チェック（PIDファイル）
  - 注文滞留（stale orders）、約定価格異常の検出
  - ダッシュボード集計（dashboard テーブル）
  - LINE による通知（AlertManager）
  - Kill Switch（ルールにより data/kill.flag を書き込んで ExecutionEngine を停止）

- Portfolio
  - 候補選定（スコア順ソート）
  - 等配分 / スコア加重配分
  - セクター集中制限の適用
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）

- Research / Data
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターンや IC（Information Coefficient）計算
  - ニュース NLP による銘柄別センチメント評価（OpenAI）

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成
  - streamlit_dashboard: 監視ダッシュボード表示

---

## 前提 / 推奨環境

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード使用時)
- SQLite は標準ライブラリで利用可能

通常は requirements.txt を用意している想定で以下のようにインストールします:

    pip install -r requirements.txt

（requirements.txt がない場合は上記パッケージを個別にインストールしてください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードはデフォルトで有効で、OS 環境変数が優先されます。自動ロードを無効化するには:

    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` にすると MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離されます
- PAPER_FILL_MODE: paper_trading 時の約定モード（`instant`|`partial`|`never`|`reject`。デフォルト `instant`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト `data/paper_trading.db`）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- DUCKDB_PATH: DuckDB パス（デフォルト `data/kabusys.duckdb`）
- PID_FILE_PATH: Execution PID ファイルパス（デフォルト `data/execution.pid`）
- KILL_FLAG_PATH: Kill Switch 用フラグファイルパス（デフォルト `data/kill.flag`）
- LOG_LEVEL: ログレベル（`DEBUG`/`INFO`/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60）

例（.env）:

    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-...
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    LOG_LEVEL=INFO

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ移動

2. Python 仮想環境を作成・有効化（推奨）

    python -m venv .venv
    source .venv/bin/activate  # macOS/Linux
    .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

    pip install -r requirements.txt

（requirements.txt がない場合は duckdb, psutil, openai, requests, streamlit を個別にインストールしてください）

4. .env ファイルを用意して必要な環境変数を設定（上記参照）

5. data ディレクトリを作成（必要時）

    mkdir -p data

監視 DB / DuckDB は起動スクリプトが自動で初期化します（init_monitoring_db）。

---

## 使い方（主要コマンド）

プロジェクトはモジュールとして実行可能です（パッケージルートが PYTHONPATH に含まれていることを想定）。

- Monitoring の起動

    python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
  - 実行中にプロジェクトルートの data/stop_requested.flag を作成するとループを終了します（停止フラグ）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します

- ExecutionEngine の起動（実トレード or ペーパー）

    python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に分離されます
  - エンジンは data/execution.pid を生成（PID ファイル）し、data/stop_requested.flag や data/kill.flag によって停止できます

- Streamlit ダッシュボード（監視データ閲覧）

    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）

    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # または DB 指定
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / リサーチ関数の利用（ライブラリとして）

  Python スクリプトや REPL から呼び出せます。例:

    from kabusys.ai.news_nlp import score_news
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, date(2026, 4, 1), api_key="sk-...")

  - OpenAI を使う機能は OPENAI_API_KEY を参照します（引数で上書き可能）
  - LLM 呼び出しはリトライ・フォールバック設計になっています（失敗時はゼロや既存値を保護）

---

## Kill / Stop の仕組み

- data/kill.flag: KillSwitch が書き込むフラグ。存在すると run_execution 側で停止を促す用途に使えます。
- data/stop_requested.flag: 手動でプロセスを止める / 起動を阻止するための共通フラグ（run_monitoring / run_execution がチェック）
- data/execution.pid: ExecutionEngine の PID ファイル。SystemMonitor はこの PID ファイルを見てプロセス生存を確認します。

kill/stop ファイルはプロセス間でシンプルなシグナルとして機能します（ファイル存在チェック）。

---

## 注意事項 / 実運用でのポイント

- KABUSYS_ENV によって動作が大きく変わります。ペーパートレード実行時は `paper_trading` を使い、実取引時は `live` を指定してください。
- OpenAI 絡みの処理は API 利用料が発生します。キーの管理やコール頻度に注意してください。
- PID / flag ファイルは運用スクリプトや systemd 等と連携することを想定しています。プロセス優先度や CPU アフィニティ設定は utils/process_priority.py で行われます。
- SQLite / DuckDB のファイルはバックアップやローテーション、アクセス制御を適切に行ってください（特に本番環境）。
- .env / .env.local の自動読み込みは、プロジェクトルート（.git または pyproject.toml を探索）に依存します。パッケージ配布後は環境変数直接の設定を推奨します。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - data/ (実行時生成想定)      — DB / PID / フラグファイル等（例: data/monitoring.db, data/kabusys.duckdb）
  - ai/
    - news_nlp.py                — ニュースの LLM センチメント評価（ai_scores 書き込み）
    - regime_detector.py         — マーケットレジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py           — SQLite ベースの監視DB 初期化 / API（MonitoringDB）
    - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度 / PID チェック
    - trade_monitor.py           — 注文滞留・約定価格異常検出
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みロジック
    - alert_manager.py           — LINE push 通知
    - monitoring_engine.py       — 監視の総合オーケストレーション
    - streamlit_dashboard.py     — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py           — 注文 State Machine 外部 API
    - reconciler.py              — 起動時のリコンシリエーション（注文・ポジション整合）
    - order_repository.py        — 注文永続化（SQLite）  ←（ファイル全体はここに含まれる想定）
    - ...                        — ブローカーインターフェース等
  - portfolio/
    - portfolio_builder.py       — 候補選定・等重/スコア重み
    - position_sizing.py         — 株数算出・リスク制限・単元丸め
    - risk_adjustment.py         — セクター上限・レジーム乗数
  - research/
    - factor_research.py        — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py    — forward returns / IC / 統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成（コマンドライン）
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - その他モジュール多数（詳細はソース参照）

---

## 開発 / テスト

- 個別モジュールはライブラリとしてインポートして利用できます（例: portfolio.calc_position_sizes）。
- MonitoringEngine には run_once() がありテスト用途に1回だけ実行できます。
- LLM 呼び出し部分は内部で呼び出す関数をモックしやすいように設計されています（テストでの差し替えを想定）。

---

## 最後に

この README はコードベース内のドキュメントと実装コメントに基づいてまとめています。詳細な API や設計ドキュメント（PortfolioConstruction.md 等）が別途存在する想定です。運用前には各種閾値・パラメータ（リスク設定、PAPER_FILL_MODE、LINE 通知設定等）を十分に確認してください。

不明点や追加で README に記載したい情報があれば教えてください。必要に応じて運用手順や systemd ユニット例、docker 化手順なども追記します。