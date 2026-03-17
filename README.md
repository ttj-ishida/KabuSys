# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants からのマーケットデータ取得、DuckDB によるスキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、監査ログ用テーブルなど、データ取得〜保管〜品質管理までの基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- 環境変数ベースの設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可能）
  - 必須環境変数の明示的取得
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）遵守、リトライ・指数バックオフ、401時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）でのトレーサビリティ、DuckDB への冪等保存
- ニュース収集モジュール
  - RSS フィード取得・前処理（URL除去・空白正規化）、記事IDは正規化URLの SHA-256（先頭32文字）
  - SSRF 対策、gzip サイズ制限、defusedxml による XML 攻撃防御
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）
  - 記事中の銘柄コード抽出（4桁）と news_symbols への紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - スキーマ初期化・接続ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィルオプション、品質チェックの実行
  - 日次 ETL の統合実行（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性チェックを実装（QualityIssue を返す）
- 監査ログ（audit）
  - シグナル→発注→約定を UUID 連鎖でフルにトレース可能なテーブル群と初期化関数

---

## 必須環境変数

README 内で参照される主要な環境変数（.env に定義してください）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

その他オプション:
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: `1` を設定すると .env 自動ロードを無効化

プロジェクトルートの判定は `.git` または `pyproject.toml` により行われます。

---

## セットアップ手順

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (# Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   必要な主なライブラリ:
   - duckdb
   - defusedxml
   - （標準ライブラリで実装されている箇所が多いため最小限の依存）

   pip install duckdb defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を用意して pip install -e . や pip install -r requirements.txt を実行してください。

3. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記の必須値を設定してください。
   - 例:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=yyyyyyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. DuckDB スキーマ初期化（Python REPL やスクリプトで実行）
   例:
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

5. （監査ログ専用 DB を分離する場合）
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要ユースケース例）

1. DuckDB スキーマの初期化
   - 全テーブルを作成して接続を得る:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

2. 日次 ETL の実行
   - J-Quants から差分取得し、保存・品質チェックまで行う:
     from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)
     print(result.to_dict())

   - オプションで target_date, backfill_days, run_quality_checks などを指定可能。

3. 単体 ETL ジョブ（例: 株価のみ）
   from datetime import date
   from kabusys.data.pipeline import run_prices_etl
   fetched, saved = run_prices_etl(conn, target_date=date.today())

4. ニュース収集ジョブ
   - RSS ソースから収集して raw_news / news_symbols に保存:
     from kabusys.data.news_collector import run_news_collection
     # known_codes に有効な銘柄コードセットを渡すと銘柄紐付けを試みる
     results = run_news_collection(conn, known_codes={"7203", "6758"})
     print(results)  # {source_name: 新規保存件数}

   - 単体 RSS フェッチ:
     from kabusys.data.news_collector import fetch_rss
     articles = fetch_rss("https://news.yahoo.co.jp/rss/...","yahoo_finance")

5. 監査ログ（order/signal/execution）スキーマ初期化
   - 既存の DuckDB 接続に監査スキーマを追加:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

6. データ品質チェック（個別／まとめて）
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn)
   for i in issues:
       print(i)

---

## 実装上の注意点・設計ハイライト

- J-Quants クライアントはレートリミットとリトライ（408/429/5xx、最大 3 回）を備え、401 は自動でリフレッシュして再試行します。
- 取得データには fetched_at（UTC）が付与され、Look-ahead Bias のトレーサビリティに配慮しています。
- 保存処理は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- news_collector は SSRF 対策、受信サイズ上限、gzip 解凍後のサイズ検査、defusedxml による安全な XML パースなど、安全性に配慮しています。
- カレンダー関連のロジックは market_calendar の有無に応じて DB 値優先／曜日フォールバックで一貫性を保ちます。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py                       — 環境変数・設定管理
- execution/                       — 発注/実行関連（未実装のプレースホルダ）
  - __init__.py
- strategy/                        — 戦略層（未実装のプレースホルダ）
  - __init__.py
- monitoring/                      — 監視関連（プレースホルダ）
  - __init__.py
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント（取得・保存）
  - news_collector.py               — RSS ニュース収集・前処理・保存・銘柄抽出
  - schema.py                       — DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py                     — ETL パイプライン（差分更新 / 日次 ETL）
  - calendar_management.py          — 市場カレンダー管理・営業日判定・更新ジョブ
  - audit.py                        — 監査ログスキーマ（signal/order/execution）
  - quality.py                      — データ品質チェック（欠損/スパイク/重複/日付整合性）

---

## 開発・デバッグのヒント

- テストや CI で .env の自動読み込みを無効にしたい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のテスト用にメモリ DB を使うには db_path に ":memory:" を渡します:
  conn = init_schema(":memory:")
- news_collector のネットワーク呼び出しは _urlopen（モジュール内）をモックして差し替え可能です。
- J-Quants のトークンはモジュールレベルでキャッシュされ、ページネーション間で共有されます。force refresh が必要な場合は get_id_token(force) を明示呼び出し可能です。

---

## 免責・今後の拡張

- この README は現在のコードベースから抽出した機能をまとめたものです。ストラテジー層や実際の発注ロジック、監視ダッシュボードなどは別途実装・統合が必要です。
- 実運用ではさらに細かなエラーハンドリング、認証情報の安全な保管（Vault 等）、監査ログの送出先（外部 DB/ログ基盤）、バックアップ方針を検討してください。

---

ご要望があれば、README に含める具体的なコード例（スクリプト雛形）や .env.example のテンプレート、requirements.txt の推奨セットなども作成します。どの部分をより詳しく記載しますか？