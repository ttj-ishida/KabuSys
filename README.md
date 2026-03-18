# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants や RSS などからデータを取得して DuckDB に蓄積し、ETL・品質チェック・監査ログ等を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価（日足）、財務（四半期 BS/PL）、JPX のマーケットカレンダーを安全かつ冪等に取得・保存する
- RSS フィードからニュースを収集し、記事の正規化・トラッキングパラメータ除去・SSRF 対策を行った上で保存する
- DuckDB に対するスキーマ定義・初期化を行い、Raw / Processed / Feature / Execution の各レイヤーを提供する
- ETL パイプライン（差分取得、バックフィル、品質チェック）を提供する
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB で管理する

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）に合わせた固定間隔スロットリングを実装
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュをサポート
- データ取得時刻（fetched_at）の記録により look-ahead bias を防止
- DuckDB への保存は冪等操作（ON CONFLICT）で重複を排除

---

## 主な機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - RateLimiter、リトライ、トークンキャッシュ（ページネーション間共有）
- data.news_collector
  - RSS 取得（gzip 対応、Content-Length/最大読み込みバイト数制限）
  - defusedxml による XML パース（XML Bomb 対策）
  - URL 正規化（トラッキングパラメータ除去）、記事 ID は URL 正規化後の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - save_raw_news / save_news_symbols（DuckDB へトランザクション単位で保存）
- data.schema
  - DuckDB スキーマ（Raw / Processed / Feature / Execution）定義と初期化（init_schema）
  - インデックス定義
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新、backfill、品質チェックの統合
- data.calendar_management
  - market_calendar を用いた is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）
- data.audit
  - 監査用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）
- data.quality
  - 欠損検出・スパイク検出・重複チェック・日付不整合チェック
  - run_all_checks による一括実行、QualityIssue による結果表現

---

## 動作要件（推奨）

- Python 3.10+
  - （コードで `X | None` のユニオン記法や型ヒントを使用）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィードなど）

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトでは他にロギングやテスト用パッケージが必要になる場合があります）

---

## 環境変数 / 設定

KabuSys は .env（および .env.local）または OS 環境変数から設定を読み込みます（自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（Settings）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、デフォルト: development) — 値: development / paper_trading / live
- LOG_LEVEL (任意、デフォルト: INFO) — 値: DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. Python 仮想環境の作成と依存インストール
   - 例: python -m venv .venv && source .venv/bin/activate
   - pip install duckdb defusedxml

2. 環境変数設定
   - プロジェクトルートに `.env` を作成するか環境変数を設定
   - 必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）を設定

3. DuckDB スキーマ初期化
   - Python スクリプトや REPL から data.schema.init_schema を呼び出す
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     conn.close()
     ```

4. 監査ログ DB（任意）
   - 監査ログを別 DB として初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     audit_conn.close()
     ```

---

## 使い方（代表的な例）

以下はライブラリを直接呼び出す最小例です。実運用では適切なログ設定や例外処理、スケジューラ（cron / Airflow 等）でのラッピングを推奨します。

- DuckDB スキーマ初期化（上記参照）

- 日次 ETL を実行する
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  # DB を初期化（初回のみ）
  conn = init_schema(settings.duckdb_path)

  # ETL 実行（target_date を省略すると today）
  result = run_daily_etl(conn)
  print(result.to_dict())

  conn.close()
  ```

- 市場カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data.news_collector import fetch_rss, save_raw_news, run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)

  # 単一ソース取得
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = save_raw_news(conn, articles)
  print("new articles:", len(new_ids))

  # 複数ソースを一括で実行（既定の DEFAULT_RSS_SOURCES を使用する場合は sources=None）
  results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)

  conn.close()
  ```

- J-Quants の株価取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  # id_token を指定しなければモジュールキャッシュ経由で自動取得・リフレッシュされます
  quotes = fetch_daily_quotes(code="7203", date_from="20220101", date_to="20220131")
  ```

- 品質チェックの実行（個別または全チェック）
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

注意点：
- J-Quants API へのリクエストは 120 req/min に制限されています。jquants_client は内部でスロットリングとリトライを行います。
- fetch_* 系はページネーションに対応し、ID トークンはページ間で共有されます。
- save_* 系は ON CONFLICT を使って冪等に保存します。

---

## 開発・テストのヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時に自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector._urlopen はテスト用にモックしやすい実装になっています。
- ETL の差分取得ロジックでは DB の最終取得日を参照し、backfill_days によって遡って再取得します（デフォルト 3 日）。
- 監査ログ初期化（init_audit_schema）はオプションでトランザクション化できますが、DuckDB のトランザクション性に注意してください（ネストトランザクション非対応）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・保存
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理（営業日判定 等）
    - audit.py                 — 監査ログ（signal / order_request / executions）
    - quality.py               — 品質チェック（欠損/スパイク/重複/日付整合性）
  - strategy/
    - __init__.py              — 戦略関連（空パッケージ）
  - execution/
    - __init__.py              — 実行（発注）関連（空パッケージ）
  - monitoring/
    - __init__.py              — 監視関連（空パッケージ）

DuckDB スキーマは data/schema.py に集中して定義されています（Raw / Processed / Feature / Execution レイヤー）。

---

## 補足・設計ノート

- セキュリティ面:
  - news_collector は SSRF / XML Bomb / Gzip bomb / メモリ DoS 対策を考慮して設計されています。
  - URL 正規化でトラッキングパラメータを除去し、冪等な記事ID を生成します。
- トレーサビリティ:
  - audit モジュールにより、シグナルから発注・約定に至るすべての流れを UUID で連鎖させて追跡できます。
- 運用:
  - ETL や calendar_update_job、news_collection は Cron / Airflow / Kubernetes CronJob などで定期実行することを想定しています。
  - 本番（live）環境では KABUSYS_ENV を `live` に設定してください。`is_live/is_paper/is_dev` プロパティで挙動を切替可能です。

---

必要であれば、README に追加する内容（例: サンプル .env.example ファイル、CI/CD 手順、Dockerfile、詳細な API 使用例など）や、特定の機能（ニュース収集の拡張、戦略実装テンプレート）のテンプレートを作成します。どの情報を追加しますか？