# KabuSys

KabuSys は日本株向けの自動売買データプラットフォームおよびETL/監査基盤ライブラリです。  
J-Quants API や RSS フィードからデータを取得し、DuckDB に保存・品質チェック・特徴量生成を行い、戦略／発注層へ渡すための基盤機能を提供します。

主な設計思想：
- データの冪等保存（ON CONFLICT を利用）
- Look-ahead バイアス回避のため取得時刻（UTC）を記録
- API のレート制御・リトライ・トークン自動更新
- ニュース収集における SSRF/GZIP/XML 攻撃対策
- 監査ログ（信号→発注→約定のトレース）を強力にサポート

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX 市場カレンダー取得
  - レートリミット制御 / リトライ（指数バックオフ） / 401時のトークン自動リフレッシュ
- ニュース収集モジュール
  - RSS から記事取得、URL正規化、トラッキングパラメータ除去
  - 記事IDは正規化URLのSHA-256（先頭32文字）
  - SSRF対策・応答サイズ制限・gzip展開保護・defusedxmlによるXML解析
  - DuckDB への冪等挿入（INSERT ... RETURNING を活用）
  - 記事→銘柄（news_symbols）紐付け機能（テキストから4桁銘柄コード抽出）
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit（監査）レイヤのテーブル群
  - インデックス定義、監査テーブル初期化ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日からの差分＋backfill）で効率的にデータ取得
  - 市場カレンダー先読み、品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を ETLResult オブジェクトで返却（品質問題やエラーの一覧含む）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等でビジネストレースを保証

---

## 必要条件 / 依存パッケージ

- Python 3.10 以上（型注釈で PEP 604 等を使用）
- 必須ライブラリ
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発時はプロジェクトルートで:
pip install -e .
```

（プロジェクトをパッケージ化している場合は setup/pyproject に従ってインストールしてください）

---

## 環境変数 / 設定

設定は環境変数（またはプロジェクトルートの `.env` / `.env.local`）から読み込まれます。自動ロードはデフォルトで有効です（ルート検出: .git または pyproject.toml のあるディレクトリ）。テストなどで自動ロードを無効にするには以下を設定します:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（README 用サンプル）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を用意
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install duckdb defusedxml
```

2. .env ファイルを作成して必要な環境変数を設定

3. DuckDB スキーマを初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```
上の例はデフォルトのパス `data/kabusys.duckdb` にファイルを作成します。":memory:" を指定するとインメモリ DB になります。

4. （監査ログを別DBで管理する場合）監査スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.db")
conn.close()
```

---

## 使い方

以下は主要操作のサンプルです。実運用ではログ設定や例外ハンドリングを適切に行ってください。

- J-Quants の ID トークン取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使ってトークンを取得
```

- 株価・財務・カレンダーの差分 ETL（日次 ETL）を実行:
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 個別ジョブ（例: 株価 ETL のみ実行）:
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を与えると記事→銘柄紐付け処理が行われる (set[str])
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count, ...}
```

- DuckDB 接続の取得:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

---

## 注意事項 / 実装上のポイント

- J-Quants API は 120 req/min のレート制限を想定。内部で固定間隔の RateLimiter を用いています。
- HTTP エラー（408/429/5xx）は指数バックオフで再試行します。401 を受け取った場合はトークンを自動でリフレッシュして1回リトライします。
- ニュース収集は SSRF・XML Bomb・gzip Bomb 等を考慮して実装されています。fetch_rss は http/https 以外のスキームやプライベートIP へのアクセスを拒否します。
- DB への保存は基本的に冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）で実装されています。
- settings では .env の自動読み込みを行います。自動読み込みはプロジェクトルートを .git または pyproject.toml から探索して行われます。

---

## ディレクトリ構成

本リポジトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py           -- J-Quants API クライアント & DuckDB 保存関数
      - news_collector.py           -- RSS ニュース収集・正規化・保存
      - pipeline.py                 -- ETL パイプライン（差分更新＋品質チェック）
      - schema.py                   -- DuckDB スキーマ定義・初期化
      - audit.py                    -- 監査ログテーブル定義・初期化
      - quality.py                  -- 品質チェック（欠損・スパイク・重複・日付不整合）
    - strategy/                      -- 戦略実装（拡張ポイント）
      - __init__.py
    - execution/                     -- 発注・ブローカー連携（拡張ポイント）
      - __init__.py
    - monitoring/                    -- 監視関連（拡張ポイント）
      - __init__.py

---

## 今後の拡張ポイント（提案）

- 戦略層（strategy）に特徴量生成・モデル推論を追加
- execution 層で kabu ステーション等のブローカーAPIラッパを実装し、発注フローと監査ログの連携を強化
- CI 用のテストスイート（DuckDB の :memory: を活用）を整備
- Slack 通知やメトリクス収集（Prometheus 等）との連携

---

もし README に追加したい内容（例: CI の設定、実運用でのデプロイ手順、具体的なサンプルスクリプト）があれば教えてください。必要に応じてサンプルコマンドやテンプレート .env.example も作成します。