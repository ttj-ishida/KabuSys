# KabuSys

日本株向けの自動売買データ基盤ライブラリ／モジュール群です。  
J-Quants などの外部データソースからのデータ取得、DuckDB での永続化、ETL パイプライン、ニュース収集、カレンダー管理、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## 主要機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min）, リトライ（指数バックオフ）, 401 自動リフレッシュ対応
  - 取得時刻（fetched_at）の UTC 記録で Look-ahead Bias を防止
- DuckDB スキーマ定義／初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、冪等的なテーブル作成
- ETL パイプライン
  - 差分更新ロジック（最終取得日から未取得分を取得）
  - バックフィルで API の後出し修正を吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集モジュール
  - RSS フィード取得、テキスト前処理、URL 正規化、記事 ID（SHA-256）生成
  - SSRF、XML ブロック、Gzip/BOM 攻撃対策、受信サイズ制限
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理
  - 営業日判定、前後営業日の検索、期間内営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティ
  - UUID ベースの冪等キー、UTC タイムスタンプ、インデックス
- データ品質チェックモジュール
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出

---

## 要求環境 / 依存

- Python 3.10 以上（PEP 604 の型書き方などを使用）
- 主な依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を使用（追加の HTTP クライアントは不要）

インストール方法の一例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはパッケージ化している場合:
# pip install -e .
```

---

## 環境変数 / 設定

このライブラリは環境変数から設定を取得します。以下が主な環境変数です（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- LOG_LEVEL — ログレベル ('DEBUG','INFO','WARNING','ERROR','CRITICAL')（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git か pyproject.toml があるディレクトリ）を検出し、
  ルート直下の `.env` を読み込み、さらに `.env.local` があれば上書きで読み込みます。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. `.env` を作成して必須変数を設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB スキーマ初期化（後述の使い方参照）

---

## 使い方（主な API とサンプル）

以下は Python REPL / スクリプトからの利用例です。

- DuckDB スキーマを初期化して接続を得る:
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path に基づく（.env で DUCKDB_PATH を設定しておく）
conn = schema.init_schema(settings.duckdb_path)
```

- 既存 DB に接続する:
```python
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
```

- 日次 ETL を実行する（株価 / 財務 / カレンダー取得 + 品質チェック）:
```python
from datetime import date
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)  # デフォルトで今日を対象に実行
print(result.to_dict())
```

- 個別 ETL ジョブ（例: 株価 ETL）:
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブ:
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# デフォルト RSS ソースを使う場合は sources=None、既知銘柄コードセットを渡すと自動紐付けが行われる
known_codes = {"7203", "6758", "9984"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- マーケットカレンダー夜間更新ジョブ:
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- 監査ログ（Audit）初期化（既存接続に監査テーブルを追加）:
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
# または専用 DB を作る場合:
# conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 注意点 / 設計上の挙動

- J-Quants リクエストはモジュール内でトークンキャッシュを持ち、必要時に自動リフレッシュします。401 発生時は 1 回のみ自動リフレッシュして再試行します。
- API レート制限（120 req/min）を守るため、内部で固定間隔スロットリングを行います。
- DuckDB への保存は冪等設計（ON CONFLICT DO UPDATE / DO NOTHING）です。ETL を複数回実行しても重複は管理されます。
- ニュース収集は SSRF、XML の脆弱性（defusedxml を使用）、Gzip/BOM、受信サイズ上限等に配慮しています。
- 品質チェックは Fail-Fast 方式ではなく、全チェックを実行して検出結果（QualityIssue リスト）を返します。呼び出し元で致命度に応じた対応を行ってください。
- プロジェクトルートの自動検出は、パッケージ配置後も動作するよう __file__ を起点に親ディレクトリを探索します。

---

## ディレクトリ構成（概要）

リポジトリの主要ファイル群（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
    - news_collector.py      — RSS ニュース収集・保存ロジック
    - schema.py              — DuckDB スキーマ定義 / 初期化
    - pipeline.py            — 日次 ETL / 個別 ETL ジョブ
    - calendar_management.py — カレンダー管理 & 夜間更新ジョブ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（発注〜約定トレーサビリティ）初期化
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（細かい実装は各モジュールを参照してください）

---

## 開発 / テストに関するヒント

- 自動 .env 読み込みを無効化してテストしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト用にインメモリ DuckDB を使う場合は `":memory:"` を db_path に指定できます。schema.init_schema(":memory:") で初期化可能です。
- ネットワーク／外部 API 呼び出し部分は関数単位でモック可能なように設計されています（例: news_collector._urlopen を差し替え）。

---

もし README に追加したい「サンプル .env.example」や「CI / 実運用のデプロイ手順（systemd / cron / Airflow など）」、あるいは各モジュールの API ドキュメント（関数一覧や戻り値の詳細）を生成したい場合は、どの情報を優先して含めるか教えてください。