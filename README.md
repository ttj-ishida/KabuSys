# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、DuckDBスキーマ／監査ログなど、アルゴリズム取引に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買ワークフローを支えるモジュール群です。主に以下を含みます：

- J-Quants API を使った株価・財務・マーケットカレンダーの取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ定義と冪等な保存ロジック（ON CONFLICT）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS からのニュース収集と銘柄抽出（SSRF対策、XML脆弱性対策、トラッキングパラメータ除去）
- 監査ログ（signal → order_request → executions のトレーサビリティ）スキーマ

設計方針としては、再現性（fetched_at の記録）、冪等性、セキュリティ（SSRF/ XML 脆弱性対策）、可観測性（品質チェック／監査ログ）を重視しています。

---

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes 等）

- ETL（kabusys.data.pipeline）
  - 差分更新（最終取得日を元に新規分のみ取得）
  - バックフィル（後出し修正対策）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（正規化 URL の SHA-256）
  - _SSRFBlockRedirectHandler を用いたリダイレクト検査、gzip/サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化
  - インデックス、外部キー、制約を含む DDL を提供

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査用テーブル群と初期化
  - UTC タイムゾーン固定、トレーサビリティを担保

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比閾値）、日付不整合を検出

---

## 動作要件 / 前提

- Python 3.10 以上（PEP 604 の | 型などを利用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

プロジェクトルートに requirements.txt がある場合はそれに従ってください。ない場合は最低限をインストールしてください：

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# もし他に必要なパッケージがあれば追加でインストールしてください
```

---

## セットアップ手順

1. リポジトリをクローン

```bash
git clone <リポジトリURL>
cd <リポジトリ>
```

2. 仮想環境を作成して依存をインストール（上記参照）

3. パッケージを開発モードでインストール（任意）

```bash
pip install -e .
```

4. 環境変数の設定

KabuSys は .env / .env.local を自動でプロジェクトルートから読み込みます（OS 環境変数が優先）。自動読み込みを無効化したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

主な環境変数（必須となるものとデフォルト）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu ステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（本コードベースでの利用はコメント等による）
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

.env 例（.env.example を参考に作成してください）:

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

## 初期化 / 使用方法（簡単な例）

以下は最小限のサンプルコード例です。Python REPL やスクリプトで実行できます。

- DuckDB スキーマを初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 監査ログ用 DB を初期化（監査専用 DB を別途用意する場合）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/audit.duckdb")  # または settings.duckdb_path を使用
```

- J-Quants トークン取得 / データ取得

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
```

- ETL（日次）を実行

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

- RSS ニュース収集と保存

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄抽出で有効なコードの集合（省略すると紐付けは行わない）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: 新規保存件数}
```

- 品質チェックだけ実行する

```python
from kabusys.data.schema import init_schema
from kabusys.data.quality import run_all_checks
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## よくあるトラブルと注意点

- 環境変数の未設定は Settings._require により ValueError を投げます。エラーメッセージに従って .env を作成してください。
- 自動で .env を読み込むため、複数環境で動かす場合は .env.local 等で上書き可能です。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルの親ディレクトリは init_schema / init_audit_db が自動作成します。
- J-Quants のレート制限（120 req/min）と API レスポンスの仕様に合わせた設計になっています。
- ニュース収集は外部ネットワークアクセスを伴うため、SSRF・XML Bomb などの攻撃に対して幾つかの防御ロジック（defusedxml, ホストのプライベートアドレス排除, コンテンツサイズ制限）を実装していますが、実運用時はさらに運用監視・ホワイトリスト等の検討を推奨します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py          -- J-Quants API クライアント（取得 + 保存）
      - news_collector.py          -- RSS ニュース収集・保存ロジック
      - schema.py                  -- DuckDB スキーマ定義と初期化
      - pipeline.py                -- ETL パイプライン（差分取得・品質チェック）
      - calendar_management.py     -- マーケットカレンダー管理、営業日判定
      - audit.py                   -- 監査ログ用 DDL / 初期化
      - quality.py                 -- データ品質チェック
    - strategy/
      - __init__.py                -- 戦略層（未実装のエントリポイント）
    - execution/
      - __init__.py                -- 発注・約定処理（未実装のエントリポイント）
    - monitoring/
      - __init__.py                -- 監視（未実装のエントリポイント）
- pyproject.toml / setup.cfg 等（パッケージング設定があればここに）

---

## 開発・拡張のヒント

- strategy / execution / monitoring はフレームワークのエントリポイントとして用意されています。実際の売買ロジックやブローカー連携はこれらの下に実装してください。
- ユニットテストでは環境変数自動読み込みを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると良いです。
- DuckDB 接続は軽量でスレッドセーフな部分に注意しつつ、単一接続を共有するか用途に応じて接続を分けてください。
- news_collector._urlopen はテスト時にモックしやすいように独立した関数です。HTTP の模擬に利用してください。

---

この README はコードベース内のコメント・ドキュメント文字列に基づいて作成しています。実運用前に各モジュールの詳細と API 仕様を確認し、環境変数・認証情報の管理（シークレット管理）・ネットワーク制限・監視アラートを適切に整備してください。