# KabuSys

日本株自動売買システムの一部（コアユーティリティ、監視、ポートフォリオ構築、リサーチ、AI補助モジュールなど）をまとめた Python パッケージです。本 README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで、以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）起動スクリプト（本番 / paper trading 切替）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- 監視データの永続化（SQLite ベースの monitoring DB）
- ポートフォリオ構築（候補選定・重み計算・単元丸め・リスク適用）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI 補助モジュール（ニュースの NLP スコアリング、レジーム検出：OpenAI 利用）
- 運用支援ツール（paper trading 検証レポート生成、Streamlit ダッシュボード）

重要な設計方針の例：
- Paper Trading は本番 DB と分離（デフォルト: `data/paper_trading.db`）。
- 自動環境変数読み込み（プロジェクトルートの `.env` / `.env.local` を参照。無効化可）。
- 監視は環境に依存せず本番の sqlite_path を使用して永続化。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - `kabusys.run_execution` — ExecutionEngine 起動（`KABUSYS_ENV=paper_trading` 時は MockBroker を使用）
  - `kabusys.run_monitoring` — SystemMonitor のポーリングループ起動（デフォルト間隔 60 秒）
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度をチェック
  - TradeMonitor: 注文滞留（stale order）・約定価格異常の検出
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件発生時に `data/kill.flag` を書き込み ExecutionEngine 停止
  - AlertManager: LINE Push によるアラート送信（チャンネル設定が必要）
- データ永続化（SQLite monitoring DB）
  - テーブル: `system_status`, `trade_logs`, `positions`, `risk_logs`, `dashboard`
  - スキーマは `kabusys.monitoring.monitoring_db.init_monitoring_db` で冪等に作成/マイグレーション
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスク調整（セクター制限、レジーム乗数）、株数決定（lot 単位丸め、aggregate cap）
- リサーチ
  - DuckDB 経由でファクター計算（prices_daily / raw_financials を利用）
  - 将来リターン、IC（Spearman）、ファクター統計
- AI（OpenAI）
  - `kabusys.ai.news_nlp.score_news` — ニュース記事を集約して銘柄ごとにセンチメントを算出・`ai_scores` に書込み
  - `kabusys.ai.regime_detector.score_regime` — MA200 乖離 + マクロニュースの LLM センチメントから市場レジーム判定
- 運用ツール
  - `kabusys.tools.paper_verification_report` — Paper Trading 結果の検証レポートを生成
  - `kabusys.monitoring.streamlit_dashboard` — Streamlit ベースの監視ダッシュボード

---

## 必要条件 / 依存

明示的な requirements.txt はここには含めていませんが、主に以下が必要です。

- Python 3.9+（typing の新しい表記や型ヒントを利用）
- ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
  - そのほか、標準ライブラリのみで動作するモジュールも多くあります

セットアップの一般的手順（例）:

```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要なパッケージをインストール（プロジェクトに requirements.txt があれば）
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（代表例）

プロジェクトでは `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数：

- J-Quants / ブローカー / API
  - `JQUANTS_REFRESH_TOKEN` — 必須（J-Quants）
  - `KABU_API_PASSWORD` — 必須（kabuステーション）
  - `KABU_API_BASE_URL` — (デフォルト: http://localhost:18080/kabusapi)
  - `OPENAI_API_KEY` — OpenAI を使う機能で必要
- 実行環境切替
  - `KABUSYS_ENV` — one of `development` | `paper_trading` | `live`（デフォルト: development）
  - `PAPER_FILL_MODE` — paper trading の約定挙動（`instant|partial|never|reject`、デフォルト `instant`）
  - `PAPER_TRADING_SQLITE_PATH` — paper trading 用 sqlite（デフォルト: `data/paper_trading.db`）
- DB / ファイルパス
  - `DUCKDB_PATH` — DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
  - `SQLITE_PATH` — monitoring 用 sqlite（デフォルト: `data/monitoring.db`）
  - `PID_FILE_PATH` — ExecutionEngine の PID ファイル（デフォルト: `data/execution.pid`）
  - `KILL_FLAG_PATH` — kill flag ファイル（デフォルト: `data/kill.flag`）
  - `KILL_FLAG_CLEAR_ON_START` — 起動時に kill.flag を自動で消すか（"1"で有効）
- 監視 / ログ
  - `MONITOR_POLL_INTERVAL` — Monitoring のポーリング間隔（秒、デフォルト 60）
  - `LOG_LEVEL` — `DEBUG|INFO|WARNING|ERROR|CRITICAL`
- LINE 通知
  - `LINE_CHANNEL_ACCESS_TOKEN`
  - `LINE_USER_ID`

.env の書式はシェル形式に準拠しており、`.env.local` は `.env` を上書きします（OS 環境変数は保護されます）。

---

## セットアップ手順（ステップ）

1. リポジトリをクローンして仮想環境を作成
2. 依存パッケージをインストール（duckdb, psutil, requests, openai, streamlit など）
3. `data/` ディレクトリを作成（`data/monitoring.db`、`data/kabusys.duckdb`、`data/paper_trading.db` など）
4. `.env` を作成（機密情報はコミットしない）
   - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - OpenAI を使う場合: `OPENAI_API_KEY`
   - 運用時: `KABUSYS_ENV=live`（本番）あるいは `paper_trading`
5. DuckDB / monitoring DB にテーブルがない場合は起動スクリプトが初回で作成します（init_monitoring_db が冪等で実行）

注意:
- Paper Trading 実行時は DB を分離（`KABUSYS_ENV=paper_trading`）。
- 起動スクリプトは起動時にプロセス優先度を "high" に設定しようとします（権限により失敗してもスキップされます）。

---

## 使い方

主要な起動方法（パッケージをインストール済み、カレントはリポジトリルートを想定）：

- Monitoring 起動（ポーリングループ）
  - デフォルト 60 秒間隔。`MONITOR_POLL_INTERVAL` で上書き可。
  - 実行:
    - python -m kabusys.run_monitoring
  - 補足: 監視は常に Settings の sqlite_path（本番 DB）を使用します。

- ExecutionEngine 起動（当日セッションを実行）
  - Paper Trading モードにするには `KABUSYS_ENV=paper_trading`
  - 実行:
    - python -m kabusys.run_execution
  - 補足: Paper モード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離されます。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション `--db PATH` で DB パスを指定可能（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）
  - 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ等のサマリーと PASS/FAIL 判定

- Streamlit ダッシュボード（監視）
  - 実行（ヘッダーにある起動方法をそのまま利用）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードでは read-only モードで monitoring DB の情報を表示します。

- AI 機能（ニュース NLP / レジーム検出）
  - OpenAI API キーが必要（`OPENAI_API_KEY`）
  - 関数:
    - `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 実装上、429/タイムアウト/5xx はリトライ、API 例外は安全にフォールバックする設計です。

---

## 監視 DB（主要テーブル）

`kabusys.monitoring.monitoring_db.init_monitoring_db` により作成される主なテーブル：

- system_status: CPU / memory / disk / process_ok / recorded_at
- trade_logs: 発注イベントログ（logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 現在保有（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベント（logged_at, event_type, metric_name, metric_value, threshold, detail）
- dashboard: 集計表示（id=1 に固定。portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

監視コンポーネントは上記テーブルを読み書きします（冪等な初期化・簡易マイグレーションを実行）。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要ファイル・モジュール構成（`src/kabusys` 配下）です：

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — monitoring DB 初期化 / MonitoringDB クラス
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Execution 関連モジュール: broker_factory 等)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py

その他、データファイル・DB は `data/` 配下（例: `data/monitoring.db`, `data/kabusys.duckdb`, `data/paper_trading.db`）を想定しています。

---

## 運用上の注意

- 機密情報（API トークンやパスワード）は `.env` に保存しても良いですが、リポジトリにコミットしないでください。
- `KABUSYS_ENV=paper_trading` により paper trading 用の DB とモックブローカーを使用し、本番資金と完全に分離できます（テスト推奨）。
- Monitoring は本番 sqlite_path を参照するため、監視専用で別実行環境を分ける場合は注意してください。
- OpenAI を使う機能は API 利用料金が発生します。API キーの取り扱いに注意してください。
- 起動時にプロセス優先度を「high」にしようとしますが、権限不足で失敗する場合があります（警告ログが出ます）。

---

## 追加情報 / 開発者向け

- Settings は `kabusys.config.Settings` を通じて取得してください（グローバルな `settings` インスタンスも提供）。
- DB 初期化 / スキーマ変更は `kabusys.monitoring.monitoring_db.init_monitoring_db` にまとめられています。マイグレーションは最小限の ALTER を行います。
- テスト時に環境変数の自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコードベースの主要点を抜粋してまとめたものです。実行や運用に際してはそれぞれのモジュールの docstring やログ出力を参照してください。必要であれば、デプロイ / サービス化（systemd ユニット、コンテナ化）や完全な requirements.txt の作成についても別途まとめます。