# KabuSys — README

本ドキュメントは、本リポジトリ（src/kabusys 以下）の主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

簡潔な前提：
- Python 3.10 以上を想定（`X | Y` 型注釈等を使用しているため）。
- 主要な外部依存: duckdb, psutil, requests, openai, streamlit（後述の手順でインストールしてください）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究／監視基盤です。主な要素は次の通りです。

- Execution（発注エンジン）: ブローカークライアントを通じて注文を作成・管理し、リスク管理やリコンサイル（再同期）機能を備えます。Paper Trading モードをサポートし、本番 DB と分離して検証が可能です。
- Monitoring（監視）: システムリソース、注文滞留・約定異常、ドローダウン等をポーリングして記録・アラート・Kill Switch 発動を行います。監視データは SQLite に永続化され、Streamlit ダッシュボードで可視化できます。
- Research（研究）: DuckDB 上の時系列データ（prices_daily / raw_financials 等）からファクター計算や特徴量探索を行うモジュール群。
- Portfolio（ポートフォリオ構成）: 銘柄選定、重み算出、ポジションサイズ計算、セクター制限などの純粋関数群。
- AI（ニュース NLP / レジーム判定）: OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価や市場レジーム判定を行い、結果を DuckDB に書き込みます。
- Tools: Paper Trading の検証レポート生成などのユーティリティスクリプトを収録。

---

## 機能一覧（主なもの）

- 実行系
  - ExecutionEngine の起動/停止制御（run_execution.py）
  - Paper Trading モード（MockBrokerClient）と専用 DB（data/paper_trading.db）
  - 再起動時の注文・ポジションのリコンシリエーション（Reconciler）
  - OrderManager による重複注文防止、状態遷移管理

- 監視系
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale order）・約定価格異常検知
  - RiskMonitor: ドローダウン、ポジション上限監視、ダッシュボード更新
  - KillSwitch: リスク閾値超過時に data/kill.flag を書き込み、Execution を停止させる仕組み
  - AlertManager: LINE Messaging API による通知（クールダウン付き）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）

- 研究・データ処理
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ

- AI
  - news_nlp: ニュース記事の銘柄別センチメントを OpenAI に問い合わせて ai_scores に書き込む
  - regime_detector: 1321（ETF）の MA200 乖離とマクロニュースを組み合わせて市場レジーム判定を行う

- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring_db: 監視用 SQLite テーブル初期化・読み書き（マイグレーション対応あり）
  - tools.paper_verification_report: Paper Trading DB を集計して PASS/FAIL レポート出力

---

## セットアップ手順

1. Python（3.10 以上）を用意します。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストールします（例）:
   - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. プロジェクトルートに `.env` / `.env.local` を配置して必要な環境変数を設定できます。
   - 自動ロードは Settings モジュールにより行われます（`.git` または `pyproject.toml` を基準にプロジェクトルートを探します）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合必須）
   - KABUSYS_ENV — 実行環境（development / paper_trading / live）。未設定時は `development`。

6. データディレクトリ
   - デフォルトで `data/` 配下のファイルを使用します:
     - SQLite（監視）: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - PID/flag: data/execution.pid, data/stop_requested.flag, data/kill.flag

   必要に応じて環境変数で上書き可能（Settings クラスのプロパティ参照）。

---

## 使い方（よく使うコマンド・運用メモ）

基本的にパッケージとして実行します（パッケージが PYTHONPATH にあることが前提）。

- 監視プロセスを起動する（ポーリングループ）
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60）。
  - 例:
    - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 注意: 監視は Settings.env にかかわらず本番の sqlite_path（data/monitoring.db）を使用します。

- 実行（ExecutionEngine）を起動する
  - Paper Trading を使う場合は環境変数 `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使用し DB は `data/paper_trading.db` を使用します。
  - 例:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行は `data/stop_requested.flag` の存在を確認します。ファイルが存在する場合は起動せず終了します。
  - 実行時は `data/execution.pid` に PID が書き込まれます。監視はこの PID を見て Execution の生存を判定します。

- Streamlit ダッシュボード（監視結果可視化）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite DB を読み取り専用で開きます。

- Paper Trading 検証レポート生成
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション `--db PATH` で DB を指定可能（デフォルト: data/paper_trading.db）

- AI 機能
  - OpenAI キーは `OPENAI_API_KEY` 環境変数、または関数呼び出し時に渡す `api_key` 引数で与えます。
  - news_nlp.score_news / regime_detector.score_regime を呼び出して、DuckDB 上のテーブル（raw_news / news_symbols 等）に対して解析・書込を行います。
  - API 呼び出しはリトライ（429 / タイムアウト / 5xx）やスコアのクリッピング等、安全策が組み込まれています。

- kill.flag / stop フロー
  - KillSwitch は閾値を超えた場合に `data/kill.flag` を書き込みます。Execution 起動時に `Settings.kill_flag_clear_on_start` を有効にしていると起動時に自動でクリアできます（設定は環境変数 `KILL_FLAG_CLEAR_ON_START=1`）。
  - 管理者が手動で Execution を停止したい場合は `data/stop_requested.flag` を作成します（run_execution / run_monitoring は起動ループでこのファイルをチェックします）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring で使用。デフォルト 60
- SQLITE_PATH: 監視 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用

（Settings クラスでさらに詳細なプロパティを確認できます）

---

## 注意点 / 実運用メモ

- run_monitoring は Settings.env にかかわらず監視用の sqlite_path を使用します（監視 DB は本番用 DB を共有する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper Trading 専用 DB を使用して本番 DB と完全分離します。
- init_monitoring_db は冪等で実行可能です。既存 DB のマイグレーション（カラム追加等）も簡易的に行います（例: trade_logs に latency_ms カラム追加、dashboard に peak_value カラム追加）。
- process priority（高優先度）や CPU affinity は utils.process_priority でプラットフォーム差分を吸収して設定します。権限不足や未対応 OS はログによりスキップされます。
- AI モジュールは外部 API を使うため、API エラー時はフェイルセーフ（0.0 などでフォールバック）を行う設計ですが、API 呼び出しに伴うコスト管理には注意してください。
- テストや CI での .env 自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリの主要なディレクトリ / ファイル（src/kabusys 以下）の抜粋です。モジュールはパッケージ化されており、import で利用できます。

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
    - run_monitoring.py  — SystemMonitor のポーリングループ起動スクリプト
    - run_execution.py   — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート
    - utils/
      - __init__.py
      - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py  — 監視用 SQLite の初期化・永続化 API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py  (参照あり / 実装は別)
      - reconciler.py
      - execution_engine.py (参照あり / 実装は別)
      - broker_factory.py, broker_api.py  (参照あり)
      - order_record.py
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
    - data/ (実行時に作成される想定)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag

（実際のソースは上記ファイル群に実装されています。ここに載せたファイル名は本 README が参照したコードベースに基づく抜粋です）

---

## 開発時のヒント / テストしやすさ

- Settings は .env/.env.local を自動読み込みしますが、テスト時に自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI モジュールの外部 API 呼び出しは `_call_openai_api` を通して行われており、ユニットテストではこの関数を patch してモック可能です（ファイル内にもその旨のコメントあり）。
- MonitoringEngine.run_once は 1 回だけ全てのモニタを実行するため、テストでの単体実行に便利です。
- MonitoringDB のマイグレーションは簡易的な追加カラム処理を含むため、ローカルで DB ファイルを再生成して挙動を確認するのが安全です。

---

もし README に加えて「インストール用の requirements.txt」や「systemd/サービス定義の例」、「.env.example」などのテンプレートを作成したい場合は、その要件（対応する OS・運用方法）を教えてください。必要に応じてサンプルも作成します。