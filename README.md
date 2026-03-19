# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
データ収集（J-Quants）、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、ファクター計算（研究用ユーティリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株自動売買システム構築のための基盤ライブラリです。主に次の役割を持ちます。

- J-Quants API からの市場データ・財務データ・市場カレンダー取得（レートリミット・リトライ・トークンリフレッシュ対応）
- DuckDB を用いた層別スキーマ（Raw / Processed / Feature / Execution / Audit）の定義・初期化
- 差分 ETL（価格、財務、カレンダー）の自動化と品質チェック
- RSS ベースのニュース収集と記事→銘柄紐付け
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）・IC 計算・統計ユーティリティ
- 発注／監視／監査テーブルのスキーマ（監査ログ・トレーサビリティ）

設計方針として、DuckDB と標準ライブラリを活用し、外部依存を最小化しつつ冪等性・トレーサビリティ・安全性（SSRF 防止、XML パース安全化など）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・再試行・トークン自動更新）
  - schema: DuckDB スキーマ（テーブル・インデックス）定義と初期化
  - pipeline: 差分 ETL（価格 / 財務 / カレンダー）と品質チェックの統合
  - news_collector: RSS 取得・前処理・DuckDB への保存、銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 発注/約定の監査ログスキーマと初期化
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- config: 環境変数の自動読み込み（.env/.env.local）と必須設定の検証
- execution / strategy / monitoring: 発注・戦略・監視用プレースホルダ（将来的な実装領域）

---

## セットアップ手順

以下はローカル開発向けの基本手順です。

前提:
- Python 3.9+（typing | duckdb 等で使用される構文に合わせて下さい）
- ネットワークアクセス（J-Quants API, RSS ソース）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール  
   必要最小限（例）:
   ```
   pip install duckdb defusedxml
   ```
   実際の開発では requirements.txt や pyproject.toml を利用してください。

4. 環境変数設定 (.env)  
   プロジェクトルートに `.env`（およびローカル上書き用 `.env.local`）を置くと自動で読み込まれます（config モジュールによる自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限必要な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   # 省略時の DB パス（例）
   # DUCKDB_PATH=data/kabusys.duckdb
   # SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 初期化 / 使い方（簡易ガイド）

以降のコードは Python REPL やスクリプト内で実行します。DuckDB を使うために `duckdb` パッケージが必要です。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```

2. 監査ログ専用 DB 初期化（別 DB にする場合）
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

3. 日次 ETL 実行（J-Quants トークンは .env から読まれる）
   ```python
   import duckdb
   from kabusys.data import pipeline
   conn = duckdb.connect("data/kabusys.duckdb")  # init_schema 実行済みを想定
   result = pipeline.run_daily_etl(conn)
   print(result.to_dict())
   ```

   - ETL は market_calendar → prices → financials → 品質チェック の順で実行します。
   - `run_daily_etl` は ETLResult を返します。`result.has_errors` / `result.has_quality_errors` を確認してください。

4. 市場データ取得（J-Quants）を直接使う例
   ```python
   from kabusys.data import jquants_client as jq
   recs = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
   # 保存
   from kabusys.data import schema
   conn = schema.get_connection("data/kabusys.duckdb")
   jq.save_daily_quotes(conn, recs)
   ```

5. RSS ニュース収集と保存
   ```python
   from kabusys.data import news_collector as nc
   conn = schema.get_connection("data/kabusys.duckdb")
   results = nc.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
   print(results)  # {source_name: saved_count, ...}
   ```

6. 研究用ファクター計算の例
   ```python
   import duckdb
   from datetime import date
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

   conn = duckdb.connect("data/kabusys.duckdb")
   t = date(2024, 1, 31)
   mom = calc_momentum(conn, t)
   vol = calc_volatility(conn, t)
   val = calc_value(conn, t)
   fwd = calc_forward_returns(conn, t, horizons=[1,5,21])

   # 例: mom の mom_1m と fwd_1d で IC を計算
   ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
   print("IC:", ic)
   ```

7. マーケットカレンダー管理（夜間ジョブ例）
   ```python
   from kabusys.data import calendar_management as cm
   conn = schema.get_connection("data/kabusys.duckdb")
   saved = cm.calendar_update_job(conn)
   print("saved:", saved)
   ```

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化（テスト用）

config モジュールはプロジェクトルートを `.git` または `pyproject.toml` の位置から探索して `.env` / `.env.local` を自動で読み込みます。

---

## 主要な API（要点）

- schema.init_schema(db_path) — DuckDB のスキーマ作成と接続返却（冪等）
- jquants_client.fetch_daily_quotes(...) — J-Quants から日足をページング取得
- jquants_client.save_daily_quotes(conn, records) — raw_prices に冪等保存
- data.pipeline.run_daily_etl(conn, ...) — 日次 ETL 実行（品質チェック含む）
- news_collector.fetch_rss(url, source) / save_raw_news(conn, articles) / run_news_collection(...)
- research.calc_momentum/ calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- data.quality.run_all_checks(conn, target_date, ...) — 品質チェック一括実行
- data.audit.init_audit_db(path) / init_audit_schema(conn) — 監査ログ初期化

各関数はドキュメント文字列（docstring）で引数と戻り値、例外条件が詳細に説明されています。ライブラリ内の docstring を参照してください。

---

## ディレクトリ構成

代表的なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
      - stats.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（上記は主要モジュールの一覧です。実装は各モジュールの docstring に詳細があります。）

---

## 運用上の注意

- J-Quants のレート制限を守るため、jquants_client は内部でレート制御を行います。不要な同時大量リクエストは避けてください。
- ETL は品質チェックでエラーを検出しても全体処理を継続する設計です。呼び出し側は ETLResult を見て適切な対処（アラート、ロールバック等）を行ってください。
- news_collector は RSS パース時に defusedxml を使用し、SSRF 対策・応答サイズ制限などセキュリティ対策を施しています。外部入力を扱う際はさらに検証を追加してください。
- 運用環境（live）では KABUSYS_ENV を `live` にし、発注ロジックや監視を厳格に運用してください（本リポジトリ自体は発注ロジックの実装は最小限—実稼働時の検証を厳密に行ってください）。

---

## 補足 / 開発

- ドキュメントは各モジュールの docstring に詳細な設計意図と挙動が書かれています。特に data/jquants_client.py、data/news_collector.py、data/schema.py、research/* の docstring を参照してください。
- パッケージは `src` レイアウトです。開発時は `pip install -e .` などで editable install を行って下さい（適切な pyproject.toml / setup がある前提）。

---

お問い合わせや拡張、バグ報告はリポジトリの issue をご利用ください。README の補足や使い方のサンプルが必要であれば、具体的なユースケース（ETL スケジューリング、戦略の実装例、発注フローなど）を教えてください。