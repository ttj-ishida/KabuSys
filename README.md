# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

このドキュメントは、提供されたコードベースに基づいてプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

なお、実行可能モジュールは Python のパッケージとして実行することを想定しています（例: `python -m kabusys.run_monitoring`）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究基盤です。主な責務は以下です。

- データ処理・研究（DuckDB を使ったファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- Execution（ブローカーと連携して注文送信・状態管理・復旧）
- Monitoring（システム稼働状況・注文状況・リスク監視・アラート）
- AI 補助（ニュースセンチメント評価 / レジーム判定：OpenAI API を利用）
- Paper Trading 向けの検証レポート生成ツール

設計方針として、現場での安全性（クラッシュ耐性・冪等操作）、ルックアヘッドバイアス対策（日時依存を避ける実装）、および本番／Paper Trading の分離が考慮されています。

---

## 主な機能一覧

- 設定管理（`kabusys.config.Settings`）
  - .env / .env.local の自動読み込み（必要なら無効化可能）
  - 環境（development / paper_trading / live）や DB パスなどを集中管理

- Execution 起動スクリプト（`kabusys.run_execution`）
  - 本番／paper_trading に応じて DB 分離（paper_trading は専用 DB）
  - Broker クライアント生成、OrderManager / RiskManager / Reconciler 組立て、ExecutionEngine の起動

- Monitoring（`kabusys.monitoring`）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン / ポジション上限監視（kill flag 書き込み等）
  - AlertManager：LINE Push による通知（クールダウン付き）
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
  - Streamlit ダッシュボード（read-only 接続で監視 DB を可視化）

- AI（`kabusys.ai`）
  - news_nlp.score_news：raw_news を集約して OpenAI で銘柄別センチメントを算出・ai_scores へ書き込み
  - regime_detector.score_regime：ETF（1321）の MA200 とマクロニュースの LLM 結果を統合し市場レジームを判定・永続化

- 研究（`kabusys.research`）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- ポートフォリオ（`kabusys.portfolio`）
  - 候補選定、等重/スコア重み、リスク調整（セクター上限、レジーム乗数）、株数算出（単元丸め・aggregate cap）

- ユーティリティ
  - process_priority（プロセス優先度・CPU affinity 設定）
  - MonitoringDB（SQLiteベースの監視ログ層）
  - tools.paper_verification_report：Paper Trading の検証レポート生成 CLI

---

## 要件

- Python 3.10 以上（型アノテーションの union 演算子 `|` を使用）
- 必要な Python パッケージ（主要なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使用する場合）
- 標準ライブラリ: sqlite3, logging, datetime など

インストール例（仮）:
```
python -m pip install duckdb psutil requests openai streamlit
```

プロジェクトに requirements ファイルがある場合はそちらを利用してください。

---

## 環境変数（主なもの）

Settings クラスで参照される主要な環境変数とデフォルト:

- KABUSYS_ENV: 起動環境（`development` / `paper_trading` / `live`） — デフォルト `development`
- SQLITE_PATH: 監視用 SQLite DB パス — デフォルト `data/monitoring.db`
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト `data/kabusys.duckdb`
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時使用） — デフォルト `data/paper_trading.db`
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード — `instant`（その他 `partial`, `never`, `reject`）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス — デフォルト `data/execution.pid`
- KILL_FLAG_PATH: kill flag path — デフォルト `data/kill.flag`
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか（`1`で true）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須機能で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須機能で使用）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能を用いる場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用トークン / ユーザ ID（AlertManager）

.env の自動読み込み:
- ルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動でロードします。
- OS 環境変数は上書きされません（`.env.local` は上書き可）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

簡単な .env 例:
```
KABUSYS_ENV=paper_trading
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=U12345678
```

---

## セットアップ手順（ローカル開発 / 動作確認）

1. Python をインストール（3.10+）
2. 必要パッケージをインストール:
   ```
   python -m pip install duckdb psutil requests openai streamlit
   ```
3. プロジェクトルートに `.env` / `.env.local` を作成して必要な環境変数を設定
4. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
5. DuckDB / SQLite の初期スキーマは、各起動スクリプトが必要に応じて初期化します（例: `init_monitoring_db` が monitoring DB のテーブルを作成）。

---

## 実行方法（代表例）

- Monitoring を開始する（常駐ポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。0以下など不正な値は無視されてデフォルトにフォールバックします。
  - Monitoring は環境にかかわらず監視用 SQLite（`SQLITE_PATH`）を使用します。

- Execution（注文エンジン）を起動する:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録され、本番 DB と分離されます。
  - 起動時にプロセス優先度を "high" に試みて設定します（権限によっては警告が出ます）。

- Streamlit ダッシュボード（監視 DB の可視化）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only URI で接続します。MonitoringEngine が動作中でないとデータが無い/開けない場合があります。

- Paper Trading 検証レポート（ツール）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで SQLite ファイルを指定可能（指定がない場合は `PAPER_TRADING_SQLITE_PATH` 環境変数や `data/paper_trading.db` を使用）。
  - 出力は標準出力にレポートを印字します（稼働率・注文成功率・レイテンシなど）。

- AI（ニュースセンチメント / レジーム判定）を呼ぶ関数はライブラリ関数として提供されています（OpenAI API キー必須）。直接 CLI エントリはありませんが、アプリケーション内から呼び出します。
  - OpenAI を使用するため、`OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時にキーを渡してください。
  - アウトコストと API レート制限に注意してください。

---

## 注意事項 / 動作上のポイント

- DB の分離:
  - Monitoring は常に `SQLITE_PATH`（監視 DB）を使用します（環境に依存しない）。
  - Execution は `paper_trading` 環境時に `PAPER_TRADING_SQLITE_PATH` を使用（本番 DB と分離）。

- Kill Switch:
  - リスク条件が満たされた場合、`KILL_FLAG_PATH`（デフォルト `data/kill.flag`）に理由を書き込みます。ExecutionEngine 側でこのフラグを確認して停止する実装になっている前提です。
  - `KILL_FLAG_CLEAR_ON_START` を `1` に設定すると、起動時にフラグをクリアする挙動を取ることが想定されています（設定値は Settings で提供）。

- OpenAI API を利用する機能:
  - `kabusys.ai.news_nlp` と `kabusys.ai.regime_detector` は OpenAI（gpt-4o-mini）を利用します。API のエラー（429 / タイムアウト / 5xx）に対して指数バックオフで再試行し、最終的にフォールバックする実装があります。
  - API キーは `OPENAI_API_KEY` で与えるか、関数引数で指定してください。
  - 出力は JSON 検証を行い、不正な出力は無視する安全設計です。

- プロセス優先度:
  - 起動スクリプトは `kabusys.utils.process_priority.set_process_priority("high")` を呼び、OS に応じて優先度変更を試みます（権限不足の場合は警告で続行）。

- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を読み込みます。環境に応じて `.env.local` を使ってローカル上書きが可能です。
  - 自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主要ファイル／パッケージと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（Settings クラス）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading の分離対応）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit による監視ダッシュボード
  - execution/
    - order_manager.py — 注文の作成・送信・状態同期ロジック
    - reconciler.py — 起動時の注文/ポジション再同期（リコンシリエーション）
    - （Broker 連携関連ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

（注）上記は提供コードから抽出した構成の要約です。実際のソースツリーには他にもファイルやサブパッケージが含まれる可能性があります（例: data / strategy など）。

---

## 開発・運用に関する補足

- テスト・ローカル検証:
  - paper_trading モードを活用して外部ブローカーへの実発注を避けながら検証できます（DB 完全分離）。
  - AI 機能は API コストが発生するため、テスト時はモック化（関数の patch）を推奨します。コードはテスト差替えを想定した設計（_call_openai_api の差替えなど）になっています。

- ロギング:
  - 起動スクリプトは基本 INFO レベルで logging.basicConfig を設定します。必要に応じて `LOG_LEVEL` 環境変数で変更可能（Settings.log_level）。

- マイグレーション:
  - `init_monitoring_db` は冪等にテーブルを作成し、既存 DB に対する簡単なカラム追加マイグレーション（例: trade_logs.latency_ms）を実施します。

---

## よくあるコマンドまとめ

- モニタ開始（デフォルト間隔 60 秒）:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- Execution 起動（paper_trading）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

この README は提供されたソースコードをもとに作成しています。実運用やデプロイに際しては、環境固有の詳細（kabuステーションの接続情報、J-Quants の資格情報、OpenAI の利用ポリシー、監視閾値の調整など）を適切に設定してください。質問やドキュメントの拡張要望があれば教えてください。