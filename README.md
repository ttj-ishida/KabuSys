# KabuSys

KabuSys は日本株の自動売買基盤（データ取得・ETL・品質チェック・監査・ニュース収集など）を提供する軽量なライブラリです。DuckDB をデータ層に用い、J-Quants API や RSS を通じたデータ収集、ETL パイプライン、品質チェック、監査ログ用スキーマなどを備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（サンプルコード）
- 環境変数・設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした内部向けライブラリです。

- J-Quants API からの株価（OHLCV）・財務（四半期 BS/PL）・市場カレンダーの取得と保存
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB 上のスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、次/前営業日の計算）
- 監査ログ（シグナル → 発注 → 約定の追跡可能性）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計における主な方針：
- API レート制限・リトライ・トークン自動リフレッシュの実装
- Look-ahead bias を防ぐため fetched_at や UTC タイムスタンプを記録
- DuckDB への挿入は冪等（ON CONFLICT）で上書き・重複排除
- RSS 取得において SSRF／XML Bomb 等の攻撃対策を実装

---

## 機能一覧

- data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - レート制限（120 req/min のスロットリング）、指数バックオフリトライ、401 時の自動リフレッシュ
  - save_* 系関数で DuckDB に冪等保存（ON CONFLICT）

- data.news_collector
  - RSS の安全な取得（SSRF リダイレクト検査、gzip 上限、defusedxml）
  - ニュース記事の正規化（URL トラッキングパラメータ除去、SHA-256 による記事 ID）
  - raw_news / news_symbols への保存（チャンク挿入、INSERT ... RETURNING）
  - 銘柄コード抽出（4桁数字、既知コードフィルタ）

- data.schema / data.audit
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化ユーティリティ（init_schema, init_audit_db）

- data.pipeline
  - ETL の差分取得ロジック（最終取得日からの差分・バックフィル）
  - run_daily_etl による一括 ETL + 品質チェック実行
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行

- data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks（QualityIssue を集約して返す。severity に基づく判断が可能）

- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチで J-Quants から差分取得して更新）

- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルートを .git / pyproject.toml で判定）
  - 必須環境変数取得時はエラーを投げるヘルパー（Settings クラス）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

---

## セットアップ手順

要件
- Python 3.10 以上（PEP 604 の union types を利用しているため）
- DuckDB
- defusedxml

例: 仮想環境作成・依存パッケージインストール（OS 環境に応じて適宜変更してください）

```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# （必要に応じて他パッケージも追加）
```

プロジェクトをローカルで編集・インストールする場合:
```
# プロジェクトのルートで
pip install -e .
```
（setup.py / pyproject.toml がある前提です。無い場合は単に PYTHONPATH にパッケージを含めるか、スクリプトから直接参照します。）

環境変数 / .env ファイルの準備:
- プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可能）。
- 必須の環境変数については次節「環境変数・設定」を参照してください。

---

## 環境変数・設定

自動ロード:
- OS 環境変数 > .env.local > .env の順で読み込まれます。
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（Settings に定義されているもの）:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視系の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

.env の例（最低限のキー）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings の必須プロパティ (`_require`) は未設定時に ValueError を投げます。
- 自動ロードはプロジェクトルートを .git または pyproject.toml を基準に探索します。配布後や入れ子のケースに注意してください。

---

## 簡単な使い方（サンプル）

以下は代表的な操作の例です。実行前に環境変数（上記）を設定してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（DuckDBPyConnection）
```

2) 監査ログ用 DB 初期化（専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

3) 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効コード集合（省略可）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

5) 個別の J-Quants API 呼び出し（テスト時など）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
data = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 主要 API / 関数の概要

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / settings.sqlite_path / settings.env / settings.log_level
  - settings.is_live / is_paper / is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> 挿入・更新件数
  - save_financial_statements(...)
  - save_market_calendar(...)

  特記事項:
  - レート制限: 120 req/min を守る実装
  - リトライ: 指数バックオフで最大 3 回。408/429/5xx をリトライ対象
  - 401: トークン自動リフレッシュを行い1回リトライ
  - 取得時に fetched_at（UTC）を付与し、いつデータを知り得たか追跡可能

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> 新規挿入された記事IDのリスト
  - save_news_symbols(conn, news_id, codes) -> 挿入数
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)
  - extract_stock_codes(text, known_codes) -> list[str]

  セキュリティ設計:
  - URL 正規化でトラッキングパラメータを削除
  - SSRF 対策: リダイレクト毎にホスト検査、private IP の検出、防止
  - defusedxml で XML 攻撃を防ぐ
  - レスポンス最大サイズを制限（デフォルト 10MB）

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(conn, target_date=None, run_quality_checks=True, ...)
  - 差分取得・バックフィル・品質チェック（QualityIssue リスト）を一括実行

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - QualityIssue オブジェクトで問題の詳細とサンプル行を取得

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

パッケージルート（src/kabusys） の主要ファイル/モジュールは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得・保存）
    - news_collector.py       # RSS ニュース収集・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン
    - calendar_management.py  # 市場カレンダー管理（営業日判定等）
    - audit.py                # 監査ログスキーマ (signal/order/execution)
    - quality.py              # データ品質チェック
  - strategy/                  # 戦略関連（空パッケージ: 実装は追加想定）
    - __init__.py
  - execution/                 # 発注・実行関連（空パッケージ: 実装は追加想定）
    - __init__.py
  - monitoring/                # 監視用モジュール（空パッケージ）
    - __init__.py

各モジュールはドキュメンテーション文字列と設計注記を豊富に含んでおり、内部挙動の理解や拡張に役立ちます。

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリは DuckDB を前提とするため、ディスクのバックアップや永続化方針を検討してください（特に監査ログ等）。
- J-Quants API のレート上限を超えないように設定を守ってください（内蔵 RateLimiter が 120 req/min を想定）。
- 本番（live）環境では settings.is_live を使った安全チェックや発注フラグを実装して、誤発注を防いでください。
- .env に機密情報（トークン等）を置く場合はアクセス制御に注意してください。CI / テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを無効化できます。
- DuckDB への大量一括挿入はチャンクサイズに注意（news_collector はチャンク分割実装あり）。

---

もし README の具体的なセクションに追加したいサンプルや、運用手順（CI/スケジューラへの組み込み、バックアップ、モニタリング）などがあれば教えてください。必要に応じて環境別の運用ガイド（開発 / 紙トレード / 本番）や systemd / cron でのジョブ起動例も作成します。