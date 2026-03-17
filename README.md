# KabuSys

日本株向けの自動売買システム向けユーティリティ集。データ取得（J‑Quants）、ETL、ニュース収集、DuckDB スキーマ・監査ログなど、戦略／発注層の下支えをするインフラ機能を提供します。

---

## プロジェクト概要

KabuSys は以下を主目的とした Python モジュール群です。

- J‑Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマの定義・初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS からのニュース収集と記事→銘柄紐付け（SSRF/サイズ制限/トラッキング除去対応）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル定義と初期化
- カレンダー管理（営業日判定・前後営業日の取得等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント：
- J‑Quants API のレート（120 req/min）を厳守する固定間隔スロットリング
- リトライ（指数バックオフ）・401 時の自動トークンリフレッシュ
- DuckDB へは冪等（ON CONFLICT）で保存
- ニュース収集は SSRF 対策・受信サイズ制限・XML パースの安全化（defusedxml）あり

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - レートリミッタ、リトライ、トークンキャッシュ

- data/schema.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)

- data/pipeline.py
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（市場カレンダー→株価→財務→品質チェック を順次実行）

- data/news_collector.py
  - fetch_rss（URL 正規化・トラッキング除去・SSRF 対策・gzip 対応）
  - save_raw_news（INSERT ... RETURNING で新規挿入ID取得）
  - save_news_symbols / run_news_collection（既知銘柄セットによる紐付け）

- data/calendar_management.py
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job

- data/quality.py
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（ETL 後の品質チェックをまとめて実行）

- data/audit.py
  - 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）

- config.py
  - .env 自動ロード（プロジェクトルートの .env / .env.local を読み込み）
  - Settings クラス（環境変数経由での設定取得）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 必要要件（例）

- Python 3.10+
- duckdb
- defusedxml
- （ネットワークアクセス：J‑Quants API、RSS フィードへの HTTP(S)）

（プロジェクトの pyproject.toml / requirements.txt を用意している場合はそれを使用してください。）

---

## インストール

ローカル開発環境での例：

1. 仮想環境作成・有効化（任意）
2. パッケージを開発モードでインストール

```bash
python -m pip install -e .
# 依存パッケージがある場合は追加で pip install -r requirements.txt
```

---

## 環境変数（主なもの）

config.Settings で参照される環境変数（必須・任意）:

- 必須
  - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API パスワード
  - SLACK_BOT_TOKEN — Slack 通知用トークン
  - SLACK_CHANNEL_ID — Slack チャンネル ID

- 任意 / デフォルトあり
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — environment（development / paper_trading / live）（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local がある場合、自動で読み込みます。
- 無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨: .env.example を作成して管理してください（リポジトリには機密情報を含めないこと）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## クイックスタート（使用例）

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（簡易）

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

run_daily_etl は市場カレンダー取得 → 営業日に調整 → 株価・財務の差分取得 → 品質チェック を順に行います。
ETLResult オブジェクトで取得/保存件数や品質問題・発生エラーを参照できます。

3) ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出時のフィルタ（例: 東京証券取引所の有効コードセット）
res = run_news_collection(conn, known_codes=set(["7203","6758"]))
print(res)  # {source_name: saved_count, ...}
```

4) 監査ログ（発注追跡）スキーマ初期化

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

5) 個別 API 呼び出し（J‑Quants）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings から refresh token を使って取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- J‑Quants API のレート制御（120 req/min）とリトライロジックが組み込まれています。
- fetch_* 系はページネーション対応、save_* 系は DuckDB に対して冪等に保存します。

---

## API 例（主要関数）

- data.schema.init_schema(db_path)
- data.schema.get_connection(db_path)
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
- data.news_collector.fetch_rss(url, source, timeout=30)
- data.news_collector.save_raw_news(conn, articles) -> list of new ids
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.calendar_management.is_trading_day(conn, date)
- data.quality.run_all_checks(conn, target_date=None)
- data.audit.init_audit_db(db_path) / init_audit_schema(conn)

（各関数は docstring で詳細が記載されています。テストや運用時に引数で id_token を注入することでテスト容易性が高まります。）

---

## ディレクトリ構成

リポジトリ内の主なファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - schema.py
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py  (戦略関連モジュール置き場、現状はプレースホルダ)
    - execution/
      - __init__.py  (発注/ブローカ連携用モジュール置き場、現状はプレースホルダ)
    - monitoring/
      - __init__.py  (監視・メトリクス関連、プレースホルダ)

例（ツリー表示）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ schema.py
   │  ├─ jquants_client.py
   │  ├─ pipeline.py
   │  ├─ news_collector.py
   │  ├─ calendar_management.py
   │  ├─ quality.py
   │  └─ audit.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

---

## 運用上の注意 / ベストプラクティス

- 機密情報（トークン等）は .env に直接保存せず、秘匿ストアや CI/CD のシークレット機能を利用してください。
- J‑Quants のレート制限・Retry-After ヘッダに従うため、長時間の大量取得はスロットリングの影響を受けます。バッチを時間帯分散してください。
- DuckDB ファイルのバックアップを定期的に行ってください（データ損失対策）。
- news_collector は外部 URL を取得するため、ネットワークポリシーに注意してください。SSRF 対策を組み込んでいますが、運用上のアクセス制御も検討してください。
- ETL のスケジューリング（cron / Airflow / Prefect 等）は標準的なバッチ方式で可能です。run_daily_etl を定期呼び出ししてください。
- 監査ログ（audit）スキーマは UTC 保存を前提としています（init_audit_schema で TimeZone を UTC に設定）。

---

## 貢献 / 開発

- 新しい機能追加やバグ修正は PR を作成してください。
- 単体テスト・モックを多用し、外部 API 呼び出しは注入可能にしてテスト容易性を確保してください（既に id_token 注入や _urlopen のモックポイントが用意されています）。

---

README に書かれている以外の細かい実装や設定は各モジュールの docstring を参照してください。質問や使用例のリクエストがあれば、目的に合わせたサンプルコードを提供します。