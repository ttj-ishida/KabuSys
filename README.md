# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ取得、ETL、品質チェック、ニュース収集、監査ログなどの基盤コンポーネント群を提供します。

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・市場カレンダー等を安全に取得するクライアント
- DuckDB を使ったデータスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定、前後営業日取得など）
- 監査ログ（シグナル→発注→約定のトレース）用テーブル群

設計上のポイントは「冪等性」「Look-ahead バイアス対策（fetched_at の記録）」「外部リソースの安全対策（SSRF対策, XML防御）」です。

---

## 機能一覧

- データ取得（J-Quants API）
  - 日足（OHLCV）・財務（四半期）・市場カレンダー
  - レート制限対応（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークン更新
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス・制約を含む初期化関数
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - run_daily_etl により一括実行
- ニュース収集
  - RSS フィード取得、コンテンツ前処理、記事ID の冪等生成、DuckDB への保存
  - SSRF 対策・XML 攻撃対策（defusedxml）・受信サイズ制限
- カレンダー管理
  - 営業日判定、次・前営業日取得、期間内営業日リスト、夜間のカレンダー差分更新ジョブ
- 監査ログ
  - signal_events / order_requests / executions テーブルによるトレース可能な監査ログ
- 設定管理
  - .env（プロジェクトルート）および .env.local 自動読み込み（必要に応じて無効化可）
  - 環境変数経由で設定を参照する Settings オブジェクト

---

## 必要条件

- Python 3.10+（型注釈に | を使用）
- 依存パッケージ（例）
  - duckdb
  - defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／コピーする

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e .）

4. 環境変数 (.env) を用意する  
   プロジェクトルートに `.env` または `.env.local` を配置すると、自動で読み込まれます。
   自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（最低限設定が必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN="xxxxx"
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（クイックスタート）

以下は Python REPL やスクリプトでの利用例です。

1. スキーマ初期化（DuckDB 作成とテーブル定義）
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値（デフォルト data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

2. J-Quants トークン取得（明示的に）
```python
from kabusys.data import jquants_client as jq

# settings.jquants_refresh_token を内部で使って id_token を取得
id_token = jq.get_id_token()
```

3. 日次 ETL 実行（差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4. 個別 ETL ジョブ（価格のみなど）
```python
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())
```

5. RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出時に許可する銘柄コードの集合（省略可）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(res)
```

6. カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

7. 監査スキーマの初期化（audit 用テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

---

## 設定と挙動のポイント

- 環境変数読み込み
  - プロジェクトルートは .git または pyproject.toml を探索して自動判定します。
  - 自動で `.env`（上書き不可）→ `.env.local`（上書き可）の順に読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

- J-Quants クライアント
  - レート制限は 120 req/min に固定（内部で間隔スロットリング）。
  - リトライ: ネットワークエラーや 408/429/5xx を対象に最大 3 回リトライ（指数バックオフ）。401 を受け取った場合は自動でトークンをリフレッシュして 1 回リトライします。
  - 取得時に fetched_at を UTC で記録して Look-ahead を防止します。

- ニュース収集
  - 記事 ID は URL を正規化（トラッキングパラメータ除去等）して SHA-256 の先頭 32 文字を使用し冪等性を実現します。
  - defusedxml を使って XML 関連の攻撃を防御、SSRF のためのホストチェックやリダイレクト検査を行います。
  - レスポンスサイズ上限を設定（10 MB）しメモリ DoS を防止します。

- 品質チェック
  - 欠損データ（OHLC 欠損は error）、重複（error）、スパイク（warning）、日付不整合（future / 非営業日は error/warning）を検出します。
  - run_all_checks は全チェックを実行し、検出結果を QualityIssue のリストで返します。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集・前処理・保存ロジック
    - schema.py              — DuckDB スキーマ定義と init_schema(), get_connection()
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー管理・夜間更新ジョブ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal / order_request / execution）初期化
  - strategy/
    - __init__.py
    (戦略関連モジュールはここに実装)
  - execution/
    - __init__.py
    (発注・ブローカー連携などはここに実装)
  - monitoring/
    - __init__.py
    (監視・メトリクス関連)

---

## 開発・テスト時のヒント

- テストや CI 実行時に自動 .env 読み込みを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のインメモリ DB を利用するには `":memory:"` を渡します:
  - conn = schema.init_schema(":memory:")
- news_collector の HTTP 呼び出しはモック可能です。特に _urlopen を差し替えて外部アクセスを制御できます。

---

もし README に含めたい追加情報（例: 実際の pyproject.toml / CI 設定、より詳細な API リファレンス、ユースケース別のサンプルスクリプト等）があれば教えてください。README を追補して詳細な利用例や運用手順を追加します。