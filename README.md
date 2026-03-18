# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（データ収集・ETL・品質チェック・監査スキーマ等）

このリポジトリは、J-Quants 等の外部 API から市場データを取得して DuckDB に保存し、品質チェックや戦略／発注層へ渡すための基盤機能を提供します。API クライアント、ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログスキーマなどを含みます。

---

## 主な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPX カレンダーの取得（ページネーション対応）
  - レートリミット制御、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止

- DuckDB を用いたデータスキーマ
  - Raw / Processed / Feature / Execution / Audit の多層スキーマ定義
  - 冪等性を考慮した INSERT（ON CONFLICT）やインデックス定義

- ETL パイプライン
  - 差分更新（最終取得日から未取得分のみ取得）
  - backfill により API 側の後出し修正を吸収
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集（RSS）
  - RSS から記事を収集し raw_news に保存、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、サイズ上限、gzip 対応、XML パースに defusedxml を使用
  - 記事と銘柄コードの紐付け（news_symbols）

- マーケットカレンダー管理
  - JPX カレンダー取得・夜間更新ジョブ、営業日判定ユーティリティ（next/prev/is_trading_day など）

- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティ用スキーマ（order_request_id を冪等キーとして使用）
  - UTC タイムスタンプ、一貫した監査設計

---

## 前提 / 必要環境

- Python 3.10+（型注釈に | を使用）
- 依存ライブラリ（少なくとも以下）
  - duckdb
  - defusedxml

（プロジェクトでは他にも標準ライブラリと urllib 等を利用しています）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン（省略）

2. 仮想環境を作成して有効化
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows:
     python -m venv .venv
     .venv\Scripts\activate

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそちらを利用してください）

4. 環境変数の用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例（.env.example）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本的な操作例）

以下は Python スクリプトや REPL から使う基本例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を作成（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動参照）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

4) ニュース（RSS）収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# sources を省略するとデフォルトの RSS ソースを使用
results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は銘柄コードセット
print(results)  # {source_name: 新規保存数}
```

5) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- ETL の idempotence（冪等性）は save_* 関数（ON CONFLICT）によって担保されています。
- run_daily_etl の引数で target_date、backfill_days、run_quality_checks の調整が可能です。
- settings は環境変数を参照します。自動ロードの挙動はプロジェクトルート（.git / pyproject.toml）を基に .env/.env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

---

## モジュール概要（主な API）

- kabusys.config
  - settings: 環境変数ラッパ（例: settings.jquants_refresh_token）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)

- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...), run_daily_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(...), calendar_update_job(...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 各チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_db(db_path), init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成

（抜粋）:
- src/
  - kabusys/
    - __init__.py
    - config.py                        -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                      -- DuckDB スキーマ定義 / 初期化
      - jquants_client.py              -- J-Quants API クライアント（取得・保存）
      - pipeline.py                    -- ETL パイプライン（差分更新・品質チェック）
      - news_collector.py              -- RSS ニュース収集・保存・紐付け
      - calendar_management.py         -- マーケットカレンダー管理・ユーティリティ
      - audit.py                       -- 監査ログスキーマ初期化
      - quality.py                     -- データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

ドキュメントや DataPlatform.md / DataSchema.md 等の参照資料がプロジェクトに含まれている想定（本コード中に設計参照が多数あります）。

---

## 運用上の注意 / ベストプラクティス

- 環境変数には秘密情報（トークン・パスワード）を含むため、共有リポジトリに直接置かないでください。`.env.local` を使ってローカルのみで管理すると良いです。
- 自動ロードの挙動はプロジェクトルート検出に依存します。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御できます。
- J-Quants のレート制限（120 req/min）と API 利用規約を守ってください。jquants_client は簡易レートリミッタを実装していますが、運用の中で追加の調整が必要になる場合があります。
- DuckDB ファイルは定期バックアップを推奨します。必要に応じてデータベースのパーティショニングやアプリケーション側のローテーション設計を検討してください。
- 監査データは削除しない前提です。ディスク容量管理にご注意ください。

---

## 貢献・拡張案

- kabuステーション API 実装（execution 層の発注・ステータス管理）
- Slack 通知連携（settings.slack_* を使った成功/失敗通知）
- ETL のスケジューリング（cron / Airflow / Prefect など）
- 追加の品質チェックやダッシュボード（monitoring モジュールの拡張）

---

README に書かれている使い方や API は現状のコードベースに基づく概要です。詳細なパラメータや追加機能は各モジュールの docstring を参照してください。必要であれば README をプロジェクトの実際の構成や packaging（pyproject.toml 等）に合わせて調整します。