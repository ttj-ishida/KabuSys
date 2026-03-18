# KabuSys

日本株向け自動売買 / データプラットフォーム（KabuSys）のリポジトリ。  
DuckDB をデータレイクに使い、J-Quants から市場データや財務データを取得して ETL → 特徴量生成 → 研究 / 戦略開発 / 発注監査までを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python ベースのライブラリ群です。

- J-Quants API からの株価・財務・カレンダーデータ取得（差分取得・ページネーション対応）
- DuckDB を用いたスキーマ管理（Raw / Processed / Feature / Execution / Audit レイヤ）
- ETL パイプライン（差分取得 + バックフィル + 品質チェック）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化）
- 監査ログ用テーブル群（シグナル → 発注 → 約定のトレース）

設計上のポイント:

- DuckDB を中心に SQL + Python で処理を記述
- J-Quants クライアントにレートリミット制御・リトライ・トークン自動更新を実装
- ETL は冪等（ON CONFLICT / DO UPDATE）を意識
- ニュース収集では SSRF / XML Bomb / 大容量応答対応などセキュリティ対策を実装

---

## 機能一覧

主な提供機能（モジュール別）

- kabusys.config
  - 環境変数の読み込み（.env / .env.local 自動ロード）、設定ラッパー settings
  - 必須変数チェック（_require）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、fetch / save 関数（daily quotes / financial statements / market calendar）
  - RateLimiter（120 req/min）、リトライ、401 時のトークン自動更新
- kabusys.data.schema
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）定義と init_schema()
- kabusys.data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - ETL 結果管理 ETLResult
- kabusys.data.news_collector
  - RSS 取得、記事正規化、ID 生成、raw_news 保存、記事→銘柄紐付け（extract_stock_codes）
  - SSRF / リダイレクト検査、gzip 上限、XML パースの安全化（defusedxml）
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- kabusys.data.calendar_management
  - market_calendar の管理・更新、営業日判定ユーティリティ（is_trading_day / next_trading_day 等）
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats: zscore_normalize（再エクスポート）
- kabusys.data.audit
  - 監査ログ用テーブル群と初期化ユーティリティ（init_audit_schema, init_audit_db）

---

## セットアップ手順

※プロジェクトに requirements.txt が同梱されている想定です。最低限必要な外部ライブラリは duckdb と defusedxml などです。

1. リポジトリをクローンしてワークディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   例（requirements.txt がある場合）:

   ```bash
   pip install -r requirements.txt
   ```

   最低限必要なパッケージ:
   - duckdb
   - defusedxml
   - （必要に応じて）requests 等

4. 環境変数の準備

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。テスト目的で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（Settings クラスで要求されるもの）

   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）

   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 `.env`:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマの初期化

   Python REPL またはスクリプトから実行:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # 必要であれば監査DBを別途初期化
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主なユースケース）

以下は代表的な操作例です。実際は各プロジェクトの CLI やバッチジョブでラップして実行することを想定します。

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を取得して保存（個別呼び出し）

  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

  jquants_client は内部でレートリミット（120req/min）とリトライ、401 時の自動トークン更新を行います。

- ニュース収集ジョブ

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄リスト
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

  特徴:
  - RSS の URL 正規化、トラッキングパラメータ削除
  - XML パースは defusedxml を利用（安全化）
  - SSRF 対策（リダイレクト先のアドレス検査、非 http/https スキーム拒否）
  - 受信サイズ上限（10MB）対応

- 研究（ファクター計算・IC 評価）

  必要な DuckDB 接続と prices_daily / raw_financials が存在することが前提。

  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2025, 1, 15)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 将来リターンを取得して IC を計算
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

  補助: zscore_normalize() でクロスセクションの Z スコア正規化が可能。

- カレンダー操作ユーティリティ

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2025, 1, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## ディレクトリ構成

主要ファイル/モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（自動 .env ロード等）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 / 保存）
    - news_collector.py             — RSS 収集・記事保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（差分取得・品質チェック）
    - features.py                   — 特徴量ユーティリティ（再エクスポート）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — market_calendar 管理、営業日API
    - etl.py                        — ETL 型の公開インターフェース（ETLResult 再エクスポート）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログテーブル定義 / 初期化（監査用 DB）
  - research/
    - __init__.py
    - feature_exploration.py        — 将来リターン、IC、統計サマリー
    - factor_research.py            — Momentum / Volatility / Value 計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

README に記載のない内部ユーティリティや追加モジュールが含まれる場合があります。上記はリポジトリ内の主な実装ファイルです。

---

## 注意点 / 運用上のヒント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に干渉する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- DuckDB スキーマ初期化は冪等です。既存 DB がある場合は上書きしませんが、audit schema は別 DB に分けることを推奨します。
- jquants_client は API レート制御、リトライ、401 の自動処理を行いますが、API キー（refresh token）は機密情報です。適切に管理してください。
- news_collector の RSS 収集は外部 URL へアクセスするため、企業ネットワークやホワイトリスト要件などに注意してください。
- ETL の run_daily_etl は各ステップで例外を捕捉して継続する設計です。結果の ETLResult を確認して問題（errors / quality_issues）を監視してください。

---

必要であれば、README に CLI コマンド群、Docker / systemd / Airflow による運用例、テスト手順や CI 設定のテンプレートも追加できます。どの情報を優先して追加しますか？