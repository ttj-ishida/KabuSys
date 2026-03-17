# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants API から市場データ（株価・財務・カレンダー）や RSS ニュースを取得し、DuckDB に保存・品質チェック・ETL を行うためのモジュール群を提供します。発注／監査（audit）や戦略（strategy）、実行（execution）、監視（monitoring）のためのスケルトンも含みます。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定読み込み（.env / .env.local を自動ロード、無効化オプションあり）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応の内部 RateLimiter
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead bias の防止）
  - DuckDB への冪等保存（ON CONFLICT による更新）
- RSS ニュース収集（news_collector）
  - RSS 取得、XML の安全パース（defusedxml）、記載URLの正規化・追跡パラメータ削除
  - SSRF 対策（スキーム検証・プライベートIPブロック・リダイレクト検査）
  - レスポンスサイズ制限（メモリ DoS 対策）
  - DuckDB への冪等保存（INSERT ... RETURNING、トランザクション）
  - 記事と銘柄コードの紐付け（簡易抽出ルール：4桁数字）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得・backfill・品質チェック）
  - 差分更新ロジック（最終取得日を見て必要な範囲のみ取得）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
- 監査ログスキーマ（signal → order_request → execution のトレースを担保）
- 監視・実行・戦略用のモジュール群（スケルトン）

---

## 動作環境

- Python 3.10 以上（型注釈に新しい構文を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリで多くをまかなっていますが、実運用では HTTP クライアントや Slack ライブラリなどを追加で利用する想定です）

requirements.txt / pyproject.toml は本リポジトリに合わせて準備してください。

---

## セットアップ手順

1. リポジトリをクローン、またはパッケージを配置
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - pip install duckdb defusedxml
   - その他プロジェクト固有の依存は pyproject.toml / requirements.txt を参照のこと

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API パスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスと同じ例
   - 監査ログを別 DB に分ける場合:
     - from kabusys.data import audit
     - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     - または既存 conn に対して audit.init_audit_schema(conn)

---

## 使い方（代表的な例）

以下はライブラリを利用するための簡単なスクリプト例です。

- DuckDB の初期化と日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）

```python
from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初期化（初回のみで OK）
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を指定することも可能）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- RSS の収集と保存（ニュース収集）

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
# 既知の銘柄コードセットを用意（例: 上場銘柄リスト）
known_codes = {"7203", "6758", "9432"}

# ソースを指定して実行（None でデフォルトソースを使用）
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J-Quants から株価データを直接取得して保存

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# 直近の株価を取得して保存
records = jq.fetch_daily_quotes(date_from="20240101", date_to="20240131")
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

- 監査スキーマ初期化（audit）

```python
from kabusys.data import schema, audit
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

（注）上記コードは例示です。実運用ではロギングやエラーハンドリング、API レート管理（get_id_token のキャッシュなど）を適切に行ってください。

---

## 設定（環境変数）

主な設定（環境変数名／説明／デフォルト）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuAPI パスワード（必須）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は値を設定（例: 1）

config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動的に読み込みます。`.env.local` は `.env` の上書き（override）として読み込まれます。

---

## 主要ディレクトリ / ファイル構成

（本 README は src/kabusys 配下の現状コードベースに基づく構成を示します）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック含む）
    - news_collector.py       — RSS 収集・前処理・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ（DDL）定義と初期化関数
    - pipeline.py             — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - audit.py                — 監査ログ（signal/order_request/execution）
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py             — 戦略用モジュール（スケルトン）
  - execution/
    - __init__.py             — 発注・実行関連（スケルトン）
  - monitoring/
    - __init__.py             — 監視関連（スケルトン）

---

## 注意点 / 設計方針（抜粋）

- API 呼び出しはレート制限およびリトライ（指数バックオフ）に対応しています。429（Retry-After）に対する考慮もあります。
- データ取得時には fetched_at（UTC）を保存し、Look-ahead bias を防止できるようにしています。
- RSS の処理は安全性と冪等性を重視：defusedxml を使用したパース、URL 正規化、トラッキングパラメータ除去、SSRF 対策、レスポンスサイズ制限、トランザクションでのまとめて保存等。
- DuckDB スキーマは Raw / Processed / Feature / Execution 層に分割されており、外部キーやインデックスも定義されています。
- 品質チェックは Fail-Fast ではなく全チェックを実行して結果を集約します。呼び出し元が重大度に応じて処理を判断します。

---

## 追加情報・拡張

- 実運用では Slack 連携や kabuステーションへの発注連携、戦略の実装、実行（execution）モジュールの具体化、監視ダッシュボードの構築が必要になります。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的にテスト用環境をセットしてください。
- J-Quants の API レスポンスやスキーマのバージョン変更に備えて、例外処理とロギングを充実させることを推奨します。

---

README に記載の操作例や環境変数は開発時の便宜上の例です。実際の運用ではセキュリティ（シークレット管理）やレート制限、取引リスク管理に十分注意して利用してください。