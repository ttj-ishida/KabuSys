# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。J-Quants や kabu ステーション等の外部データソースから市場データ・財務データ・ニュースを取得し、DuckDB で管理・品質チェック・ETL を実行できるよう設計されています。戦略（strategy）、発注/実行（execution）、監視（monitoring）などの上位レイヤー実装の土台となるコンポーネント群を提供します。

主な設計方針：冪等性（ON CONFLICT）、Look-ahead バイアス対策（fetched_at 等の記録）、API レートリミット順守、堅牢なエラーハンドリング（リトライ、トークン自動更新）、SSRF/Zip Bomb 対策 等。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定を明示的に取得する Settings オブジェクト
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集モジュール
  - RSS フィード取得・前処理（URL除去、空白正規化）
  - URL 正規化 + SHA-256 による記事ID生成（冪等性）
  - SSRF 対策、gzip/サイズ制限、defusedxml で安全にパース
  - DuckDB へバルク（トランザクション）で保存、銘柄抽出・紐付け機能
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス作成、init_schema / get_connection API
- ETL パイプライン
  - 差分更新（最終取得日判定 + バックフィル）
  - 日次 ETL（calendar → prices → financials）と品質チェックの統合
  - 品質チェック：欠損、スパイク、重複、日付不整合の検出
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログスキーマ（signal/order/execution の完全トレース）

---

## 必要条件（推奨）

- Python 3.10+（ソースにて型アノテーション等を利用）
- 依存 Python パッケージ（代表）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API ／ RSS フィード等）
- （任意）kabu ステーション等のブローカー接続情報

（プロジェクトでは標準ライブラリの urllib, logging 等も使用）

---

## セットアップ手順

1. リポジトリをクローンしてルートに移動（src レイアウトを想定）:
   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. インストール（ソースを開発モードでインストール）:
   pip install -e ".[dev]"  # setup がある場合。ない場合は必要パッケージを個別に pip install duckdb defusedxml 等

   もしくは最低限:
   pip install duckdb defusedxml

4. 環境変数の準備:
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 自動読み込みはデフォルトで有効（プロジェクトルートは .git または pyproject.toml で検出）。
   - 自動読み込みを無効化したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuAPI 接続パスワード
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   任意 / デフォルト:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

   設定は `kabusys.config.settings` から取得できます。

---

## 使い方（主要な例）

以下はライブラリをインポートして使う最小例です。実行は Python プログラム／スクリプト内で行います。

1) 設定を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env, settings.log_level)
```

2) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成して全テーブルを作る
```

3) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 今日分の ETL（デフォルト）
print(result.to_dict())
```

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) J-Quants API から個別データを取得（トークン取得含む）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

6) 監査スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

注意点:
- jquants_client の HTTP リトライ、レート制御、401 の自動リフレッシュは組み込まれています。テスト時は id_token を引数で注入できます。
- news_collector は RSS の安全な取得（SSRF/サイズ/zip-bomb 対策）を行います。テスト時は内部の _urlopen をモック可能です。

---

## 環境変数と設定（settings）

kabusys.config.Settings が環境変数をラップして提供します。主なプロパティ：

- jquants_refresh_token -> JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password -> KABU_API_PASSWORD（必須）
- kabu_api_base_url -> KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token -> SLACK_BOT_TOKEN（必須）
- slack_channel_id -> SLACK_CHANNEL_ID（必須）
- duckdb_path -> DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path -> SQLITE_PATH（デフォルト: data/monitoring.db）
- env -> KABUSYS_ENV（development/paper_trading/live）
- log_level -> LOG_LEVEL（DEBUG/INFO/...）

.env のパースには細かな対応（export プレフィックス、シングル/ダブルクォート、コメント除去など）があり、.env.local は .env より優先して上書きされます。ただし既存の OS 環境変数は保護されます。

自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py        # RSS 取得・前処理・保存・銘柄抽出
  - schema.py                # DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py              # ETL パイプライン（差分更新・日次ETL）
  - calendar_management.py   # 市場カレンダー管理（営業日判定・update job）
  - audit.py                 # 監査ログスキーマ（signal/order/execution トレーサビリティ）
  - quality.py               # 品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/                   # 戦略関連モジュール（拡張ポイント）
  - __init__.py
- execution/                  # 発注・約定ロジック（拡張ポイント）
  - __init__.py
- monitoring/                 # 監視関連（拡張ポイント）
  - __init__.py

補足:
- README はここに示した API を参照して拡張してください。
- 上位レイヤー（strategy, execution, monitoring）は骨組みを提供しており、具体的な戦略やブローカー連携はプロジェクト用途に応じて実装します。

---

## 開発 / テスト上の注意

- DuckDB 接続はスレッドやプロセスの扱いに注意してください。長期稼働サービスでは接続の管理方針を明確に。
- ETL は差分取得とバックフィルを行います。パラメータ（backfill_days, lookahead_days）で挙動を調整可能です。
- news_collector と jquants_client は外部ネットワーク依存なので、単体テストでは HTTP コールをモック推奨。
- audit.init_audit_schema は transactional オプションとタイムゾーン固定（UTC）を考慮しています。既存トランザクション内での呼び出しは注意。

---

もし README にサンプルスクリプトや CI / デプロイ手順、詳細な環境変数の一覧（.env.example 形式）を追加したい場合は、要望を教えてください。補足の README セクションを作成します。