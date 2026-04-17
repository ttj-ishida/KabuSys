# KabuSys

KabuSys は日本株の自動売買システムのコンポーネント群です。取引実行エンジン、監視/アラート、ポートフォリオ構築やリサーチ用ファクター計算、AI を用いたニュースセンチメント評価などを含むモジュール設計になっています。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

- 自動売買に必要な機能をモジュール化した Python パッケージ。
- 主な目的：
  - ExecutionEngine による注文生成・発注・リスク管理
  - MonitoringEngine によるシステム監視・アラート・Kill Switch
  - Portfolio Construction（候補選定・配分・ポジションサイズ計算）
  - Research（ファクター計算、将来リターン、IC 等）
  - AI コンポーネントによるニュースセンチメント・レジーム判定（OpenAI）
  - Paper Trading モードをサポート（本番 DB と分離）
- 永続化は主に SQLite（監視用 etc）と DuckDB（価格・ファイナンス系分析）を使用。

---

## 機能一覧（抜粋）

- Execution
  - 起動スクリプト: `run_execution.py`
  - BrokerClientFactory に基づくブローカークライアント（本番 / モック切替）
  - OrderManager / OrderRepository / Reconciler による注文管理と再同期
  - RiskManager による各種制約（ポジション、利用率、サーキットブレーカー等）

- Monitoring
  - 起動スクリプト: `run_monitoring.py`
  - SystemMonitor: CPU/Mem/Disk、プロセス有無、データ鮮度を監視
  - TradeMonitor: 滞留注文・約定異常価格を検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みと LINE 通知
  - Streamlit ダッシュボード (`monitoring/streamlit_dashboard.py`)

- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap 対応）

- Research / Data
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計サマリー
  - DuckDB を用いた高速集計・分析

- AI（オプション）
  - ニュース NLP（OpenAI）で銘柄ごとの sentiment を ai_scores テーブルへ保存
  - レジーム判定（MA + マクロニュースセンチメントの合成）

- ユーティリティ
  - 環境変数ロード（.env / .env.local の自動ロード）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - Paper Trading 用のレポート生成スクリプト

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトし、プロジェクトルートに移動します。

2. Python 仮想環境を作成して有効化（推奨）：
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（代表的なもの）：
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があればそれを使用してください）

   注意:
   - sqlite3 は標準ライブラリに含まれます。
   - OpenAI 機能を使う場合は `openai` が必要です。
   - LINE 通知を使う場合は `requests` が必要です。
   - Streamlit ダッシュボードを見る場合は `streamlit` が必要です。

4. 環境変数の設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成できます。
   - 自動ロード: デフォルトで OS 環境変数 > .env.local > .env の順で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
   - PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring でオーバーライド可能）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（監視・制御関連）

5. data ディレクトリ
   - 実行時に PID ファイルやフラグファイルを書き込む `data/` ディレクトリを作成してください（起動時に自動生成される場合もあります）。
   - 例: mkdir -p data

---

## 使い方（主要なエントリポイント）

- 実行エンジンを起動（通常は systemd 等でデーモン化して運用）
  - 本番/デバッグ共通:
    - KABUSYS_ENV を指定（例: export KABUSYS_ENV=development / paper_trading / live）
  - Python モジュールとして起動:
    - python -m kabusys.run_execution
  - 仕様:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
    - 起動時、`data/stop_requested.flag` が存在すると起動をスキップします（停止フラグ）。
    - 実行中は `data/execution.pid` に PID を書き込みます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path（Settings.sqlite_path）を使用する設計になっています。
  - 停止方法:
    - 監視ループは `data/stop_requested.flag` を検知して終了します（ファイル生成で停止を促す）。
    - KillSwitch は条件成立時に `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定でクリア動作を制御できます。

- Streamlit ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ポートフォリオや最近の注文、システムステータス、リスクログ等を表示します。

- Paper Trading 検証レポート
  - スクリプト:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db で SQLite ファイルを指定可能（指定がなければ PAPER_TRADING_SQLITE_PATH 環境変数、最終的に data/paper_trading.db がデフォルト）。
  - 検証指標:
    - 稼働率、注文成功率、送信率、P95 レイテンシ などの基準をレポートします。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - ニューススコアリング:
    - kabusys.ai.score_news を呼び出すことで raw_news -> ai_scores へ書き込み。
    - 内部で gpt-4o-mini を利用する想定（API のレスポンス制御、リトライ、バリデーションを実装）。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を呼び出し、market_regime テーブルへ書き込み。

---

## 注意点 / 運用上のポイント

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。
  - OS 環境変数は保護され、`.env.local` の override を制御します。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading と本番 DB の分離
  - `KABUSYS_ENV=paper_trading` の場合、paper_trading 用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用します。これにより本番の監視 DB を汚さずに動作確認ができます。

- プロセス優先度の設定
  - 起動時に `set_process_priority("high")` を呼び出してプロセス優先度を上げようとします。権限不足等で失敗する場合は警告を出してスキップします。

- フラグファイル制御
  - `data/stop_requested.flag`：run_monitoring/run_execution の外部停止制御（存在検出でループを終了する）。
  - `data/kill.flag`：KillSwitch による ExecutionEngine 停止シグナル（`Settings.kill_flag_path` でパス指定可能）。
  - Execution 起動時に `kill_flag_clear_on_start` を有効にすると（Settings.kill_flag_clear_on_start）、起動前に kill.flag を自動削除できます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数ロードと Settings クラスの定義（必須キー検証など）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化（テーブル作成・CRUD）
    - system_monitor.py — CPU/MEM/DISK、データ鮮度、PID チェック
    - trade_monitor.py — 滞留注文、約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限の評価とログ
    - kill_switch.py — フラグファイルの書き込み（Kill Switch）
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 各 Monitor の統合・ポーリングループ
    - streamlit_dashboard.py — Streamlit によるダッシュボード
  - execution/
    - order_manager.py, order_repository.py, order_record.py, reconciler.py, execution_engine.py 等（注文・発注・同期ロジック）
    - broker_factory.py, broker_api.py（ブローカー抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算、aggregate cap、単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores に書き込み
    - regime_detector.py — レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

---

## よく使うコマンド例

- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## 開発メモ / 追加情報

- 設定の必須キー未設定時は Settings 内で ValueError を送出します（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等）。
- DuckDB 接続は分析処理（research / ai）で使用されます。prices_daily / raw_financials / raw_news 等のテーブル構成に依存します。
- AI 系の API 呼び出しでは 429 / ネットワーク断 / タイムアウト / 5xx を想定した指数バックオフを実装しています。
- DB マイグレーションは `monitoring_db.init_monitoring_db` に簡易的なカラム追加チェックがあります（冪等）。

---

必要があれば、README に「環境変数のサンプル .env.example」や「systemd ユニットファイル例」、「運用手順（デプロイ・ロールバック）」などの追加章を作成します。どの情報を優先的に追記しますか？