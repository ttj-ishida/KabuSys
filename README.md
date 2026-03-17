# KabuSys

日本株自動売買プラットフォーム基盤ライブラリ (KabuSys)

簡潔な説明:
KabuSys は日本株向けの自動売買・データ基盤用ライブラリです。J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に格納する ETL、RSS からのニュース収集、データ品質チェック、監査ログ用スキーマなどの基盤機能を提供します。設計は冪等性・トレーサビリティ・セキュリティ（SSRF対策・XML安全パース）を重視しています。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で保存し Look-ahead Bias を防止
  - DuckDB へ冪等保存（ON CONFLICT を利用）

- ETL パイプライン
  - 差分更新（最終取得日に基づく自動差分取得）
  - バックフィル (デフォルト: 3 日) による後出し修正吸収
  - 市場カレンダーの先読み（デフォルト: 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集
  - RSS フィード取得・前処理・記事IDは正規化 URL の SHA-256（先頭32文字）
  - defusedxml を使った安全な XML パース
  - SSRF 対策（スキーム検証、プライベートIPブロック、リダイレクト検査）
  - レスポンスサイズ上限（デフォルト 10 MB）など DoS 対策
  - DuckDB へ冪等保存・記事と銘柄の紐付け機能

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙
  - DB データがない場合は曜日ベースのフォールバック

- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル群
  - 発注要求は冪等キー（order_request_id）で重複実行を防止
  - すべての TIMESTAMP は UTC で保存

- データ品質チェック
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - 問題は QualityIssue オブジェクトとして集約（severity: error/warning）

---

## 必要条件 (Requirements)

- Python 3.9+（コードは型注釈や pathlib 等を使用）
- 依存ライブラリ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

（プロジェクトの pyproject.toml / requirements.txt があればそちらを参照してください）

---

## インストール

開発環境での例:

1. 仮想環境の作成・有効化（例: venv）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール:
   ```
   pip install duckdb defusedxml
   # あるいはプロジェクトルートで
   pip install -e .
   ```

---

## 設定（環境変数）

KabuSys は環境変数（またはプロジェクトルートの `.env` / `.env.local`）から設定を読み込みます。自動ロードはデフォルトで有効です（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な設定項目（環境変数名）:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン

- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)

- Slack（通知等で使用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)

- 実行環境・ログ
  - KABUSYS_ENV (任意, 有効値: development, paper_trading, live) 既定: development
  - LOG_LEVEL (任意, 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL) 既定: INFO

注意: 必須の環境変数が未設定の場合、Settings プロパティ呼び出しで ValueError が発生します。

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ（データベース初期化）

DuckDB スキーマを初期化して接続を取得する例:

```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリが自動で作成されます）
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログスキーマのみを追加する場合:

```python
from kabusys.data import audit, schema

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

監査ログ専用 DB を作る場合:

```python
from kabusys.data import audit
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要な API 例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得・保存・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# 初期化済みの DuckDB 接続を取得
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（デフォルト: 今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 市場カレンダー更新ジョブ（夜間バッチ等で実行）

```python
from kabusys.data import calendar_management, schema
conn = schema.init_schema("data/kabusys.duckdb")

saved = calendar_management.calendar_update_job(conn)
print("saved calendar records:", saved)
```

- RSS ニュース収集ジョブ

```python
from kabusys.data import news_collector, schema

conn = schema.init_schema("data/kabusys.duckdb")

# sources は {name: url} の辞書、省略時は組み込み DEFAULT_RSS_SOURCES を使用
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- J-Quants からの個別取得（テストやバッチ内で直接利用可能）

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# トークンは settings.jquants_refresh_token を利用して自動で取得されます
quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェックの単独実行

```python
from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 実装上のポイント / セキュリティ

- API レート制御: J-Quants は 120 req/min。内部に固定間隔の RateLimiter を備えています。
- リトライ: 指定の HTTP ステータス（408、429、および 5xx 系）やネットワークエラーに対する指数バックオフのリトライを実装。
- トークン更新: 401 を受けた場合はリフレッシュトークンから ID トークンを自動で再取得し1回だけリトライ。
- ニュース収集: defusedxml を使用した安全な XML パース、SSRF 対策（スキーム/プライベートIPチェック）、レスポンスサイズ制限、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）で行われます。
- 監査ログは削除しない運用を想定（FK による保護）。全ての TIMESTAMP を UTC で保存。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - news_collector.py            — RSS ニュース収集・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - calendar_management.py       — カレンダー更新・営業日ロジック
    - audit.py                     — 監査ログスキーマ（signal / order_request / executions）
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py                  — 発注/ブローカー連携用プレースホルダ
  - monitoring/
    - __init__.py                  — 監視（軽量プレースホルダ）

---

## 開発・テスト時のヒント

- 自動的にルートの `.env` / `.env.local` を読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化して下さい。
- DB をインメモリで使いたい場合は `":memory:"` を init_schema に渡すと DuckDB のインメモリ DB を使用できます。
- network/HTTP ロジック（news_collector._urlopen など）はモックしやすく設計されています。
- 監査ログのタイムゾーンは `init_audit_schema` 実行時に `SET TimeZone='UTC'` を実行します。アプリ側で UTC を前提に取り扱ってください。

---

## ライセンス / 貢献

本ドキュメントではライセンス情報は含めていません。実プロジェクトへ導入する際はライセンスファイルおよびコントリビューションガイドラインを参照してください。

---

README に記載のない機能や使い方については、コード内の各モジュールの docstring（関数・クラスの説明）を参照してください。必要であれば、具体的な利用例（cron / Airflow での運用例、Slack 通知の実装例、kabuステーション連携例）を追加で作成します。どの例が欲しいか教えてください。