# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株のデータ収集・ETL・品質チェック・監査ログ・発注基盤のためのライブラリ群です。J-Quants API や RSS ニュースからデータを取得して DuckDB に蓄積し、戦略（strategy）→実行（execution）→監視（monitoring）へつなぐための共通処理群を提供します。

主な設計方針
- データ取得は冪等（ON CONFLICT）で安全に保存
- API 呼び出しはレート制限とリトライ（指数バックオフ）を実装
- Look-ahead bias を避けるため取得時刻（UTC）を記録
- RSS 収集は SSRF / XML Bomb / 大容量レスポンス対策を実装
- データ品質チェックを行い問題を検出して可視化可能

---

## 機能一覧
- 環境設定読み込み
  - .env/.env.local 自動ロード（プロジェクトルートを基準）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）
- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期BS/PL）、JPX カレンダー取得
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar）
- RSS ニュース収集（data/news_collector.py）
  - RSS 取得・XML パース（defusedxml）
  - URL 正規化・トラッキング除去・記事ID（SHA-256先頭32文字）
  - SSRF 対策（リダイレクト先検査 / private IP 拒否 / スキーム検証）
  - 大容量レスポンス・gzip 解凍上限チェック
  - DuckDB へ冪等保存（raw_news, news_symbols）
- データスキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL 定義
  - init_schema(db_path) で DB を初期化
- ETL パイプライン（data/pipeline.py）
  - 差分更新（最終取得日判定 + backfill）
  - 市場カレンダー・株価・財務の一括 ETL（run_daily_etl）
  - 品質チェック呼び出し
- マーケットカレンダー管理（data/calendar_management.py）
  - 営業日判定、前後営業日検索、夜間カレンダー更新ジョブ
- 品質チェック（data/quality.py）
  - 欠損、スパイク、重複、日付不整合チェック
  - QualityIssue オブジェクトで詳細を返す
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions テーブルの初期化
  - 監査トレースのための DDL とインデックス
- strategy/, execution/, monitoring/ 用のパッケージプレースホルダ（拡張領域）

---

## 動作要件（推奨）
- Python 3.10+
  - 型注釈に `X | None`（PEP 604）を使用しているため 3.10 以上が必要です
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス：J-Quants API、および各種 RSS フィードへの outbound HTTP(S)

依存のインストール（例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 必要に応じて他パッケージを追加
```

---

## 環境変数（主要）
以下はコード内で参照される主な環境変数です。プロジェクトルートの `.env` / `.env.local` を用意することを推奨します。

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動ロード制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します（テスト用途などで便利）。

.env のパースはシェルライク（export KEY=val, quotes, inline comments）に対応しています。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# または requirements.txt があれば: pip install -r requirements.txt
```

3. 環境変数ファイルを用意
- プロジェクトルートに `.env`（および必要に応じて .env.local）を作成し、上記必須変数を設定します。
- 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化
Python インタプリタからまたはスクリプトで実行します:
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

5. 監査ログスキーマ（必要に応じて）
```python
import duckdb
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn)
```

---

## 使い方（代表的な例）

- J-Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # .env の JQUANTS_REFRESH_TOKEN を使用して取得
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# 初期化済みのDBに接続（初回は init_schema を呼ぶ）
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

- RSS ニュース収集ジョブを実行
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes を与えると記事と銘柄の紐付けも行う
known_codes = {"7203", "6758", "8306"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- データ品質チェックを直接実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## よくあるトラブルシューティング
- .env が読み込まれない
  - プロジェクトルートが .git または pyproject.toml を基準に判定されます。自動ロードを無効にしている（KABUSYS_DISABLE_AUTO_ENV_LOAD）場合は手動で環境変数を設定してください。
- J-Quants リクエストが 401（Unauthorized）
  - get_id_token がリフレッシュトークンから idToken を取得します。refresh token が無効な可能性があります。設定を確認してください。
- ネットワークエラー / レート超過
  - jquants_client は 120 req/min の制限に従うように実装されていますが、API 側の制限で 429 が返ることがあります。ログと Retry-After ヘッダを参照してください。
- DuckDB ファイルの権限エラー
  - ディレクトリが存在するか、書き込み権限があるか確認してください。init_schema は親ディレクトリを自動作成しますが、権限不足だと失敗します。

---

## ディレクトリ構成（抜粋）
プロジェクトの主要ソースツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - news_collector.py             — RSS ニュース収集・保存
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — 市場カレンダー管理
    - audit.py                      — 監査ログ（signal/events/executions）
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略モジュール（拡張領域）
  - execution/
    - __init__.py                   — 発注/実行モジュール（拡張領域）
  - monitoring/
    - __init__.py                   — 監視モジュール（拡張領域）

---

## 拡張・開発メモ
- strategy/ と execution/、monitoring/ は拡張ポイントです。戦略の生成したシグナルは audit/order_requests を経由して発注・監査される想定です。
- テスト時の便利機能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により .env 自動読み込みを無効化できます。
- DB スキーマは DuckDB を前提に作られており、インメモリ ":memory:" でもテスト可能です（init_schema(":memory:")）。

---

この README はコードベースの主要機能をまとめた簡易ドキュメントです。さらに詳しい設計（DataPlatform.md 等）や API 使用例はプロジェクト内の設計文書を参照してください。