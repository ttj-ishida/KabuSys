# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋実行/監視ツール群）

このリポジトリは、シグナルからポジション構築、発注、監視、Paper Trading の検証、研究用ファクター計算、ニュース NLP によるセンチメント評価などを含む自動売買システムの主要コンポーネントをまとめたコードベースです。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 発注系（Execution）
  - ブローカークライアント抽象化、OrderManager、ExecutionEngine、Reconciler（再同期）
  - Paper Trading モード（ブローカーはモック、実データベースと分離）
- 監視系（Monitoring）
  - System / Trade / Risk の各種モニタ、アラート管理、kill フラグ、監視 DB（SQLite）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み付け、リスク制御（セクター制限、レジーム乗数）、株数決定（単元丸め、aggregate cap）
- 研究用（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン、IC 計算、統計サマリ
- AI モジュール（ai）
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングする `news_nlp`
  - マクロセンチメント + ETF MA による市場レジーム判定 `regime_detector`
- ユーティリティ
  - 設定/環境変数ロード（`.env` 自動読み込み）、プロセス優先度設定、各種 DB 初期化/ラッパ

---

## 主な機能一覧

- 環境設定管理（`.env` / `.env.local` の自動ロード、OS 環境優先）
- ExecutionEngine：発注・注文状態管理・リスク制御を含む実行エンジン
- Paper Trading：本番 DB と分離した専用 SQLite に記録して検証可能
- Monitoring：
  - SystemMonitor（CPU/Memory/Disk、プロセス PID チェック、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じてフラグファイルを作成し ExecutionEngine 停止を促す）
  - AlertManager（LINE Push でアラート送信、クールダウン管理）
- Streamlit ダッシュボード（監視データの可視化）
- Research：DuckDB 経由でファクター計算・IC・統計を実行
- AI：OpenAI を使ったニュースセンチメント（スコアリング）、レジーム判定（冪等書き込み）
- Tools：Paper Trading 用検証レポート生成スクリプト

---

## 要件（推奨）

- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（OpenAI / LINE API を使う場合）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

（コード内で参照される環境変数とデフォルト値／必須の有無を抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意・デフォルトあり
  - KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject。デフォルト: instant）
  - PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill フラグパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1"=True）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（デフォルトあり）
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート用（未設定なら送信はスキップ）

.env の自動ロード
- リポジトリルート（.git または pyproject.toml が見つかる場所）から `.env` -> `.env.local` の順で読み込みます。
- OS 環境変数を保護するため .env による上書きは `.env.local` のみで可能。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール

   ```bash
   pip install -r requirements.txt
   ```

   ※ requirements.txt がない場合は最低限以下を導入してください:

   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数の設定

   - ルートに `.env`（または `.env.local`）を作成し、必要な変数を設定します。
   - 重要: `JQUANTS_REFRESH_TOKEN` と `KABU_API_PASSWORD` は必須です（実行するモジュールにより不要な場合あり）。
   - OpenAI を使う場合は `OPENAI_API_KEY` を設定してください。
   - Paper Trading を試す場合は `KABUSYS_ENV=paper_trading` を設定します。

5. データディレクトリ準備

   必要に応じて `data/` を作成します（SQLite / DuckDB のデフォルト場所）。

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要スクリプト・実行例）

- 監視プロセス起動（SystemMonitor のポーリングループ）

  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定できます（デフォルト: 60）。

  ```bash
  python -m kabusys.run_monitoring
  # または
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  注意: monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します。

- Execution（取引実行）起動

  KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し、Paper Trading 用 DB に記録されます（`data/paper_trading.db` が既定）。

  ```bash
  python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード（監視）

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成（ツール）

  指定期間のレポートを標準出力に出力します。DB を明示するか環境変数 `PAPER_TRADING_SQLITE_PATH` を使います。

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラムから呼び出す）

  ライブラリ API を直接呼べます（OpenAI API キーが必要）。

  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # ニューススコア（target_date に対する前日15:00〜当日08:30 JST の記事を対象）
  score_news(conn, date(2026, 4, 10), api_key="sk-...")
  # レジームスコア（market_regime テーブルへ書き込む）
  score_regime(conn, date(2026, 4, 10), api_key="sk-...")
  ```

---

## 注意事項 / 運用メモ

- Paper Trading は実際の発注を行わず、モックブローカーを用いる想定です。本番 DB（monitoring.db など）と Paper Trading DB は分離されます。
- ExecutionEngine 起動時に kill.flag のクリアを自動化する場合は設定（KILL_FLAG_CLEAR_ON_START）を利用してください。
- process priority は `kabusys.utils.process_priority.set_process_priority("high")` を使って起動時に高優先度を要求しますが、OS の許可がない場合は警告が出てスキップされます。
- OpenAI 呼び出しは外部 API に依存するため、レート制限や一時的な失敗に対してリトライやフェイルセーフ（0.0 フォールバック）を実装しています。ただし API キー管理とコストに注意してください。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブル作成・永続化 API
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE 送信用ユーティリティ（クールダウン管理）
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ...（OrderRecord、リスク管理など）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/vol）
    - feature_exploration.py — 将来リターン、IC、統計
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/ (実行時に使用される想定ディレクトリ)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)

---

## 開発・拡張のヒント

- DuckDB をデータソース（prices_daily / raw_financials 等）として用い、Research モジュールは SQL と Python の組合せで計算する設計になっています。大量データのバッチ処理や分析に適しています。
- AI モジュールは OpenAI の JSON Mode を利用する想定です。API レスポンスの堅牢なパース・バリデーションが組み込まれています。
- 監視 DB（SQLite）はマイグレーション処理を含んでおり、既存 DB にカラムを追加するロジックが実装されています（冪等）。
- Execution 側はクラッシュ耐性を考慮した二相的な永続化手順を採用しています（OrderSent の永続化等）。

---

## ライセンス / 貢献

この README はコードベースの説明用です。ライセンスやコントリビューション方針はリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

---

この README はリポジトリに含まれている主要モジュールからまとめた概要と実行手順です。必要であれば、各モジュール（ExecutionEngine / MonitoringEngine / AI モジュール等）のより詳細なドキュメントや使用例、設定テンプレート（.env.example）を追加できます。必要な場合はどの部分を詳述するか教えてください。