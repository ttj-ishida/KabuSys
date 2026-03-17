# KabuSys

日本株自動売買システムのライブラリ群（データ取得・ETL・品質チェック・監査ログ等）

このリポジトリは日本株を対象としたデータ基盤と自動売買に必要な下位モジュール群を含みます。主に J-Quants API からの市場データ取得、RSS によるニュース収集、DuckDB を用いたスキーマ定義・永続化、ETL パイプライン、データ品質チェック、監査ログの初期化機能などを提供します。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、リトライ・指数バックオフ、401 自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層に分かれたテーブル定義
  - 冪等に作成可能（CREATE TABLE IF NOT EXISTS / ON CONFLICT ...）

- ETL パイプライン
  - 差分更新（最終取得日からの再取得、バックフィル対応）
  - 市場カレンダー先読み、品質チェックとの連携
  - run_daily_etl による日次 ETL 実行

- ニュース収集（RSS）
  - RSS 取得、前処理（URL 除去・空白正規化）、記事ID: 正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、受信サイズ上限、gzip 解凍対策
  - DuckDB への冪等保存（INSERT ... RETURNING / ON CONFLICT DO NOTHING）
  - 記事と銘柄コードの紐付け（news_symbols）

- データ品質チェック
  - 欠損（OHLC）・スパイク（前日比）・重複（主キー）・日付不整合（未来日・非営業日）検出
  - QualityIssue 型で検出結果を返却

- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブルを初期化
  - 発注トレーサビリティ（UUID の階層）を担保

- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取得ラッパ（settings）

---

## 必要条件（前提）

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクトの packaging / requirements.txt がある場合はそちらを参照してください。最低限のインストール例は以下参照）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 追加で必要なパッケージがあればインストール
```

---

## 環境変数（主なもの）

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（CWD に依存せず __file__ を基準にルートを探索）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意/デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化

例 (.env):
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=kabustation_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成する
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
```

2. 依存パッケージをインストール
（プロジェクトに requirements ファイルがない場合は少なくとも下記をインストール）
```bash
pip install duckdb defusedxml
```

3. 環境変数を設定
- プロジェクトルートに `.env` を作成（上記参照）
- 自動ロードが不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をエクスポート

4. DuckDB スキーマ初期化（例）
- Python スクリプトで実行

init_db.py の例:
```python
from kabusys.data import schema
db = schema.init_schema("data/kabusys.duckdb")
print("DB initialized:", db)
```

または対話的に:
```python
>>> from kabusys.data import schema
>>> conn = schema.init_schema("data/kabusys.duckdb")
```

5. 監査ログの初期化（必要なら）
```python
from kabusys.data import audit, schema
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

---

## 使い方（主要な API）

以下は典型的なワークフローと利用例です。各関数はモジュールに直接インポートして使用します。

1. DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2. J-Quants からのデータ取得 / ETL 日次実行
```python
from kabusys.data import pipeline

# 日次 ETL を実行（target_date は省略で今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は以下を順に実行します:
- 市場カレンダー ETL（先読み）
- 株価日足 ETL（差分・バックフィル）
- 財務データ ETL（差分・バックフィル）
- 品質チェック（オプション）

3. RSS ニュース収集
```python
from kabusys.data import news_collector

# sources: {name: url}。省略時は DEFAULT_RSS_SOURCES を使う
articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

# DuckDB に保存
new_ids = news_collector.save_raw_news(conn, articles)

# 既知銘柄セット known_codes を用意して紐付け
known_codes = {"7203", "6758", "8306"}
news_collector._save_news_symbols_bulk(conn, [(nid, "7203") for nid in new_ids])  # 内部関数利用例
# 通常は run_news_collection を使うとまとめて実行される
```

または高レベルの一発実行:
```python
from kabusys.data import news_collector
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

4. J-Quants トークン取得（低レベル）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

5. 設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

---

## 実運用上の注意点 / 設計上のポイント

- API レート制限に厳密に従う実装（120 req/min）。大量取得時は _RateLimiter によるスロットリングが入ります。
- 401 エラー時は自動的にリフレッシュトークンで id_token を再取得して 1 回だけ再試行します。
- データ保存はできる限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されているため、ETL は再実行可能です。
- ニュース収集では SSRF や XML Bomb、gzip 展開後の大容量チェックなどを実装して安全性を確保しています。
- 環境変数は .env と .env.local の順で読み込まれ、OS 環境変数が最優先されます。テスト時に自動読み込みを無効化できます。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に配置されています。主なファイル:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得 + 保存）
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義 / 初期化
    - pipeline.py              — ETL パイプライン（差分更新・品質チェック）
    - audit.py                 — 監査ログテーブル初期化
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py              — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py              — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py              — 監視関連（拡張ポイント）

（フルファイル一覧はリポジトリ参照）

---

## 今後の拡張ポイント / TODO

- 発注実行（execution）・ポートフォリオ管理の具体的なブローカー連携実装
- Slack 通知連携（config にある Slack トークン関連を使う）
- CI / テストケース、モック可能な HTTP レイヤの追加（現在は一部をモック可能に設計済）
- パッケージ化 / requirements.txt とインストール手順の整備
- 海外市場や他データソースの追加

---

## ライセンス / 著作権

（この README にはライセンス情報が含まれていません。リポジトリの LICENSE ファイルを参照してください。）

---

必要であれば、README に含める具体的な CLI 実行スクリプト例や systemd / cron での定期実行例、.env.example のテンプレートの追記も作成します。どの例が欲しいか教えてください。