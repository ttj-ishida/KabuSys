# KabuSys

日本株向け自動売買基盤（ライブラリ＋実行スクリプト群）

この README はリポジトリ内のコード（src/kabusys）を対象に、プロジェクト概要、機能、セットアップ手順、よく使う実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントを揃えたシステムです。主な役割は以下の通りです:

- シグナルに基づく発注（ExecutionEngine / OrderManager）
- リコンシリエーション（再起動時の自動復旧）
- ポートフォリオ構成（銘柄選定、重み付け、ポジションサイズ計算）
- ファクター計算・研究機能（DuckDB を用いた Factor / Feature 分析）
- AI を利用したニュースセンチメント（OpenAI）とレジーム判定
- 監視（System / Trade / Risk）とアラート（LINE）、監視ダッシュボード（Streamlit）
- Paper Trading（テスト用の完全分離 DB & Mock ブローカー）
- 運用ツール（Paper Trading 検証レポート等）

設計上、DuckDB は時系列・ファクター計算向けの分析 DB、SQLite は監視ログ・注文履歴などの永続化に使われます。OpenAI API を利用する部分はオプションです。

---

## 主な機能一覧

- Execution / 発注
  - OrderManager / ExecutionEngine: 発注フロー管理、ブローカー抽象化
  - Reconciler: 再起動時の OrderSent 照合とポジション差分検出
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、本番 DB と分離して data/paper_trading.db に記録

- Portfolio Construction
  - 候補選定（select_candidates）
  - 等金額 / スコア加重配分（calc_equal_weights / calc_score_weights）
  - リスク調整（セクターキャップ、レジーム乗数）
  - 株数算出（単元丸め / aggregate cap / risk-based allocation）

- Research / ファクター計算
  - momentum / volatility / value ファクター計算（DuckDB 接続を受け取る純関数）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - ニュース NLP（kabusys.ai.news_nlp.score_news）：OpenAI を用いた銘柄ごとのセンチメントスコア計算と ai_scores への書き込み
  - レジーム判定（kabusys.ai.regime_detector.score_regime）：ETF ma200 乖離 + マクロセンチメントで日次レジーム判定

- Monitoring / 運用監視
  - SystemMonitor / TradeMonitor / RiskMonitor：状態の定期チェックと監視 DB へのログ
  - KillSwitch：条件発動で data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager：LINE Push API で通知（クールダウン有り）
  - Streamlit ダッシュボード（監視データ参照）
  - monitoring DB のテーブル群（system_status, trade_logs, positions, risk_logs, dashboard）

- ツール
  - paper_verification_report：Paper Trading DB を解析して検証レポートを生成

- ユーティリティ
  - process_priority（クロスプラットフォームでプロセス優先度 / CPU affinity 設定）
  - 設定管理（.env 自動読み込み・環境変数ラッパー）

---

## セットアップ手順（開発 / 実行環境）

以下は基本的なセットアップ手順例です。プロジェクトの実行環境や OS によって変更してください。

1. Python 仮想環境を作成・有効化（推奨: Python 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - requirements.txt が無い場合は主要依存を手動でインストール:
     - pip install duckdb psutil requests openai streamlit
   - （sqlite3 は標準ライブラリ。streamlit はダッシュボード用）

3. プロジェクトルートに .env を作成（任意）
   - config.py は自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 必須環境変数を設定
   - JQUANTS_REFRESH_TOKEN （必要に応じて）
   - KABU_API_PASSWORD （kabusapi 接続用）
   - OPENAI_API_KEY （AI 機能を使う場合）
   - 例: export KABUSYS_ENV=development; export KABU_API_PASSWORD="..." など

5. データディレクトリの作成
   - デフォルト DB パスは `data/` 以下を利用するため、必要に応じて作成:
     - mkdir -p data

6. （オプション）DuckDB に prices_daily / raw_financials 等のテーブルをロード
   - Research / AI 機能は DuckDB 内のテーブルに依存します。テーブル準備は運用に応じて行ってください。

---

## 主要な環境変数

（コード内 Settings に定義されているものの抜粋）

- KABUSYS_ENV: 起動環境
  - 有効値: development, paper_trading, live
  - paper_trading の場合、Paper Trading 用 DB / Mock ブローカーを使用

- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE Push 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の成行／約定挙動（instant, partial, never, reject）
- PID_FILE_PATH: 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意: Settings._load_env_file の挙動により、.env/.env.local の自動読み込みが行われます。OS の環境変数は保護され、.env.local は上書きが可能です。

---

## 使い方（実行例）

- ExecutionEngine（発注プロセス）を起動
  - 本番相当:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（MockBroker / 分離 DB）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行開始時にプロセス優先度を上げ、監視テーブルの存在を保証します。

- Monitoring（監視プロセス）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視ログを記録します。

- Streamlit ダッシュボード（監視参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（存在しない場合はエラー表示）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

- AI 機能の利用（例: Python スクリプトから）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  （api_key 省略時は OPENAI_API_KEY を使用）
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 開発者向けユーティリティ
  - process_priority.set_process_priority("high") などでプロセス優先度を制御
  - config.Settings を経由して環境設定を取得（settings = Settings() / settings.sqlite_path 等）

---

## 監視 DB（SQLite）スキーマ概要

init_monitoring_db により作成される主なテーブル:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok

- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms

- positions
  - code (PK), qty, avg_price, current_price, updated_at

- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail

- dashboard
  - 単一行（id=1）で集計情報を保持：updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

マイグレーションや列追加は init_monitoring_db 内で冪等的に行われます（例: latency_ms, peak_value の追加処理あり）。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／.env 読み込みと Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - position_sizing.py      — 株数計算（単元丸め・資金制限）
  - research/
    - factor_research.py      — momentum/value/volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し + ai_scores 書込）
    - regime_detector.py      — レジーム判定（ETF MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite の初期化と永続化 API（MonitoringDB）
    - system_monitor.py       — システム状態・データ鮮度チェック
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成 / 管理
    - alert_manager.py        — LINE Push 通知ラッパー
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py  — Streamlit ベースの運用ダッシュボード
  - execution/
    - order_manager.py        — 発注フロー管理
    - reconciler.py           — 再起動時リコンシリエーション
    - order_repository.py     — 注文レポジトリ（SQLite 操作） ※抜粋されているか確認
    - broker_factory.py       — BrokerClientFactory（Mock / 実ブローカーの選択）
    - ...                     — broker_api, order_record 等
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

（上記は抜粋ベースの一覧です。実際のファイル群はリポジトリ全体を参照してください）

---

## 運用上の注意・ベストプラクティス

- Paper Trading と Live データは明確に分離すること（KABUSYS_ENV=paper_trading を利用）。
- OpenAI キーは運用環境で安全に管理する（.env / シークレットマネージャ等）。
- Monitoring は監視 DB に記録します。監視ループは MONITOR_POLL_INTERVAL に従って繰り返し実行されます。
- KillSwitch により運用上の重大閾値（ドローダウンなど）で ExecutionEngine を停止できます。kill.flag の存在は ExecutionEngine 起動時に注意してください（必要に応じて clear）。
- process_priority / cpu_affinity の設定は OS 権限に依存し、失敗時は警告を出してスキップします。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）は research / AI の計算で利用します。これらは事前に整備しておく必要があります。
- DB バックアップやログローテーションは運用ポリシーに従って行ってください。

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- Execution 起動
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README にサンプルの .env.example（推奨設定）や運用フロー図、Docker / systemd のユニットファイル例、より詳細なテーブル定義（DDL）などを追記できます。どの情報を追加したいか教えてください。