# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
J-Quants / RSS 等から市場データやニュースを収集・ETL し、DuckDB に格納して戦略・発注層へ供給するためのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 日次株価（OHLCV）・四半期財務データ・JPX カレンダーの取得
  - レートリミット（120 req/min）遵守の RateLimiter
  - リトライ（指数バックオフ、最大 3 回）、401 受信時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録、Look-ahead Bias への配慮
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を収集して前処理（URL 除去・空白正規化）
  - URL 正規化・SHA-256 ベースの記事 ID により冪等性を保証
  - SSRF / XML Bomb 等への対策（スキーム検証、プライベートホスト拒否、defusedxml、受信サイズ上限）
  - DuckDB へのバルク挿入（INSERT ... RETURNING）と銘柄コード抽出・紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義と索引
  - 監査ログ（signal / order_request / executions）用スキーマの初期化機能

- ETL パイプライン
  - 差分更新（最終取得日を基にバックフィル）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を表す ETLResult

- データ品質チェック（quality）
  - 欠損データ / スパイク / 重複 / 日付整合性チェック
  - QualityIssue のリストを返し、重大度に応じた判断が可能

---

## セットアップ手順

前提:
- Python 3.9+（コードは型注釈に Union / | 型を用いているため、少なくとも 3.10 が好ましい）
- ネットワーク接続（J-Quants / RSS フィードアクセス）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   プロジェクトに requirements ファイルや pyproject.toml があればそれに従ってください。
   （将来的に pip install -e . 等でインストールする想定です）

4. 環境変数設定
   - プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（既定で OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot Token
- SLACK_CHANNEL_ID — 通知先の Slack チャンネル ID

オプション（デフォルト値あり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）ファイル（デフォルト: data/monitoring.db）

---

## データベース初期化

DuckDB スキーマを作成するには `kabusys.data.schema.init_schema` を使用します。

例（Python スクリプトまたは REPL）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH のデフォルトを参照
conn = init_schema(settings.duckdb_path)
```

監査ログ（order_requests / executions 等）を追加で初期化する場合:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

メモリ DB を使う場合:
```python
conn = init_schema(":memory:")
```

---

## 使い方（代表的な API と実行例）

- J-Quants ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を利用して取得
```

- デイリー ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトは本日を対象
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# known_codes を渡すと記事から抽出した 4 桁コードのみ紐付けを行う
known_codes = {"7203", "6758"}  # 例: トヨタ、ソニー 等の known codes セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 個別データ取得（J-Quants から日足をフェッチ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
records = fetch_daily_quotes(code="7203", date_from=date(2024, 1, 1), date_to=date(2024, 2, 1))
saved = save_daily_quotes(conn, records)
```

- 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

注意点:
- jquants_client は内部でレートリミッタやリトライを行いますが、API 利用規約（レート）には従ってください。
- news_collector は外部 URL 取得時に SSRF 対策やサイズ制限を行います。fetch_rss は HTTP エラーをそのまま送出することがあります。

---

## 環境変数（一覧）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化します

.env ファイルのパースは shell ライクな簡易仕様に対応し、クォート・エスケープやコメント処理を考慮しています。`.env.local` は `.env` を上書きする優先度で読み込まれます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py            — RSS ニュース収集・前処理・保存
    - schema.py                    — DuckDB スキーマ定義と初期化
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - audit.py                     — 監査ログ用スキーマ（signal/events/order_requests）
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                  — 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                  — 監視・メトリクス（拡張ポイント）

その他:
- .env (推奨) / .env.local
- data/ (デフォルトで DuckDB ファイル等が格納される)

---

## 開発メモ / 注意事項

- DuckDB はインストールしておく必要があります（pip install duckdb）。
- XML 解析には defusedxml を用いており、RSS の脆弱性対策をしています。
- news_collector の fetch_rss はリダイレクト先も検査して内部アドレスへアクセスしないようにしています。
- ETL は冪等性を重視します。raw データの保存は ON CONFLICT を使うため再実行が安全です。
- ETL の品質チェックは Fail-Fast ではなく、問題を収集して呼び出し元で判断できる設計です。
- KABUSYS_ENV を `live` に設定する場合は十分な安全対策（発注ロジックの確認、環境分離）を行ってください。

---

もし README に追記したいサンプルスクリプト、CI 設定、または具体的な戦略 / execution 層の実装テンプレートが必要であれば教えてください。必要に応じてサンプルコードや .env.example を作成します。