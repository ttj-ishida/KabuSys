# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や RSS などから市場データ・ニュースを収集し、DuckDB に格納・品質チェック・監査ログを提供します。戦略・発注・モニタリング層と統合して自動売買システムを構築するための基盤コンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の責務を持つモジュール群を提供します。

- J-Quants API から株価（日足）・財務情報・市場カレンダーを安全に取得（レート制御・リトライ・トークン自動更新）。
- RSS フィードからニュースを収集し、トラッキングパラメータ除去・重複排除して保存。
- DuckDB スキーマの初期化と ETL パイプライン（差分取得・バックフィル・品質チェック）。
- 監査ログ用スキーマ（シグナル→注文→約定のトレーサビリティ）を別モジュールで提供。
- データ品質チェック（欠損・重複・スパイク・日付不整合）の実行。

設計上のポイント:
- ETL と保存処理は冪等（ON CONFLICT 等）に実装。
- リトライ・指数バックオフ・RateLimiter によるレート制御を実装。
- XML/HTTP 関連で SSRF や XML bomb などの脅威に対する防御を実施。
- すべての監査タイムスタンプは UTC を前提。

---

## 主な機能一覧

- jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - API レート制御・リトライ・401 自動リフレッシュ
- news_collector
  - RSS フィード取得、テキスト前処理、記事IDの冪等生成（URL正規化→SHA-256）
  - SSRF/サイズ/XML 攻撃対策
  - raw_news / news_symbols への安全な一括挿入（トランザクション）
- schema
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）を作成する init_schema()
- pipeline
  - 日次 ETL 実行: run_daily_etl（カレンダー取得→価格→財務→品質チェック）
  - 差分取得、バックフィル対応、品質チェック統合
- quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
- audit
  - 監査ログ用テーブル初期化（init_audit_schema / init_audit_db）
- 設定管理 (kabusys.config)
  - .env/.env.local からの自動読み込み (プロジェクトルートの検出: .git or pyproject.toml)
  - Settings クラス経由で環境変数へアクセス

---

## セットアップ手順

前提:
- Python 3.9+（typing の | 記法や型注釈が使われています。プロジェクトの実際の要件に合わせて調整してください）
- DuckDB を利用（Python ライブラリ duckdb）
- ネットワーク接続（J-Quants や RSS へアクセス）

1. レポジトリをクローン（またはパッケージを配置）：
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化（推奨）：
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール（例）：
   - 本リポジトリに requirements.txt がない場合は、最低限以下をインストールしてください:
     - duckdb
     - defusedxml
   ```
   pip install duckdb defusedxml
   ```
   プロジェクトを開発モードで使う場合:
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
   - 必須の環境変数（Settings で _require されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV — one of: development, paper_trading, live (default: development)
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL (default: INFO)
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は対話的に使う / スクリプトから呼ぶときの典型的なコード例です。

1. DuckDB スキーマ初期化:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# 設定された DUCKDB_PATH にファイルを作成してテーブルを初期化
conn = init_schema(settings.duckdb_path)
```

2. 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl

# conn: duckdb connection (init_schema の戻り値)
result = run_daily_etl(conn)
print(result.to_dict())
```

3. ニュース収集ジョブ（既知銘柄コードセットを提供して紐付けを行う例）:
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コード（"7203" 等）のセット
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数, ...}
```

4. J-Quants から直接データ取得（テストや個別取得）:
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
jq.save_daily_quotes(conn, records)
```

5. 監査スキーマ初期化（監査ログを別 DB に作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# あるいは既存 conn に追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

注意点:
- ETL / save_* 関数は冪等に設計されており、再実行しても重複を許さないロジック（ON CONFLICT）になっています。
- jquants_client は内部で RateLimiter を使いレート制限（120 req/min）を遵守します。
- news_collector は SSRF 防止・XML 攻撃対策・レスポンス size 制限を行います。

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
    - data/
      - __init__.py
      - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
      - jquants_client.py      — J-Quants API クライアント（取得/保存）
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - news_collector.py      — RSS ニュース収集と保存ロジック
      - audit.py               — 監査ログ用スキーマ & 初期化
      - quality.py             — データ品質チェック
      - pipeline.py
    - strategy/                 — 戦略層（placeholder）
    - execution/                — 発注実行層（placeholder）
    - monitoring/               — モニタリング / 監視（placeholder）

ドキュメント/設計参照:
- 各モジュール冒頭の docstring に設計方針や処理フローが記載されています。実装の挙動や制約（例: レート制限・リトライ・エラーハンドリング）を把握する際に参照してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuAPI パスワード
- KABU_API_BASE_URL — kabuAPI ベース URL（default: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値は任意。1 等を設定）

---

## セキュリティ & 運用メモ

- RSS パーシングには defusedxml を使用して XML 攻撃を軽減しています。
- RSS 取得時は Content-Length とレスポンスの実体サイズを検査して大きすぎるレスポンスを破棄します（MAX_RESPONSE_BYTES）。
- リダイレクト先の検証およびホストのプライベートアドレス判定により SSRF を防止します。
- 監査テーブルは UTC 保存を前提にしており、init_audit_schema() は接続に対して TimeZone を UTC に設定します。
- J-Quants の API レート制限に従うため、内部に RateLimiter を実装しています。大量取得の際は十分な待ち時間が入ります。

---

## 開発・テストに関する補足

- モジュール内部のネットワークリクエストはテスト容易性のために差し替え可能（例: news_collector._urlopen をモック）。
- DB 初期化は init_schema(":memory:") でインメモリ DuckDB を使ってテストできます。
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に基づくため、単体テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

---

もし README に追加したい内容（例: CI 設定、詳細な API 使用例、運用手順、実際の .env.example など）があれば教えてください。必要に応じて具体的なコード例や運用手順を追記します。