# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
J-Quants / kabuステーション 等の外部 API と連携してデータ収集、ETL、データ品質チェック、ニュース収集、監査ログ（発注〜約定トレース）などを提供します。

現時点のバージョン: 0.1.0

---

## 概要

KabuSys は次の層を備えたデータ/実行基盤を提供します。

- Raw layer：外部 API から取得した生データ（株価・財務・ニュース・約定 等）
- Processed / Feature layer：整形済み市場データや戦略用特徴量
- Execution / Audit layer：シグナル → 発注 → 約定 のトレーサビリティを確保する監査テーブル
- ETL・品質管理：差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集：RSS からの安全なニュース取得と銘柄紐付け

設計上のポイント：
- DuckDB をデータ永続化基盤として利用（ファイルまたはメモリ）
- J-Quants API はレートリミット・リトライ・トークン自動リフレッシュ対応
- ニュース収集は SSRF / XML Bomb / Gzip Bomb 等の安全対策を実施
- ETL は冪等（ON CONFLICT）・差分更新・バックフィルをサポート
- 監査ログは全操作を UUID 連鎖でトレース可能に設計

---

## 主な機能一覧

- J-Quants クライアント
  - 日足（OHLCV）、四半期財務、マーケットカレンダーの取得
  - レートリミット制御、再試行（指数バックオフ）、401 の自動トークン更新
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新・バックフィル・カレンダー先読み
  - デイリー ETL の一括実行（prices / financials / calendar）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュースコレクター
  - RSS から記事を取得、テキスト前処理、記事ID（正規化 URL の SHA-256）生成
  - SSRF / private host チェック、受信サイズ制限、gzip 解凍の安全対策
  - raw_news への冪等保存と銘柄コード抽出・紐付け
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、期間内営業日取得、夜間更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブルと初期化ユーティリティ

---

## 必要条件

- Python 3.9+
- 主要依存（例）:
  - duckdb
  - defusedxml
  - （標準ライブラリ：urllib, datetime, logging 等）

※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存を明記してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトして仮想環境を作成します：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. 依存パッケージをインストールします（例）：

```bash
pip install duckdb defusedxml
# またはプロジェクト整備済みなら
# pip install -e .
```

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数（主なもの）：
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack チャネル ID

オプション：
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（"1" 等）
- KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB のスキーマを初期化します。Python から呼び出して DB とテーブルを作成します。

```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリが無ければ作成されます）
conn = schema.init_schema("data/kabusys.duckdb")

# またはインメモリ
# conn = schema.init_schema(":memory:")
```

監査ログ（audit）用スキーマは別関数で初期化できます：

```python
from kabusys.data import audit

# 既存の conn に監査スキーマを追加する（トランザクションあり）
audit.init_audit_schema(conn, transactional=True)

# 監査専用 DB を作る場合
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要なユースケース）

以下はライブラリ API を直接呼ぶ例です。CLI は現状用意されていないため、スクリプトやバッチで Python を使って呼び出します。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 株価 ETL の個別実行（差分取得）

```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- マーケットカレンダー夜間更新ジョブ

```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
```

- ニュース収集ジョブ（RSS）

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources: {source_name: rss_url} を渡せます。省略時はデフォルトソースを使用
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count}
```

- J-Quants の ID トークン直接取得（テスト用）

```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## 設定・環境変数の動作

- 自動 .env 読み込み順序: OS 環境変数 > .env.local > .env
- テストや特殊な環境で自動読み込みを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- settings（kabusys.config.Settings）経由で各種設定を取得できます。
  - 取得されるパス（例）: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH など
  - KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかに制約されています
  - LOG_LEVEL は標準的なログレベル文字列のみ許容されます

---

## 注意点・設計上の挙動

- J-Quants API クライアントはレート制限（120 req/min）に従い固定間隔でスロットリングします。大量取得時は時間がかかります。
- API から 401 が返った場合、自動でリフレッシュトークンを使って ID トークンを取得して1回だけリトライします。
- ニュース取得では、URL 正規化（トラッキングパラメータ除去）を行いその SHA-256（先頭32文字）を記事IDとします。これにより冪等保存を保証します。
- DuckDB に対する INSERT は可能な限り ON CONFLICT（冪等）を使って重複や追記を扱います。
- 品質チェックは Fail-Fast ではなく全チェックを実行して問題一覧を返します。呼び出し元で閾値に応じて ETL を停止するか判断してください。

---

## ディレクトリ構成

（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境設定 / .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集
    - schema.py                — DuckDB スキーマ定義 / init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — マーケットカレンダー管理
    - audit.py                 — 監査ログ定義 / 初期化
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py              — 戦略関連（将来的に拡張）
  - execution/
    - __init__.py              — 発注・ブローカー連携（将来的に拡張）
  - monitoring/
    - __init__.py              — 監視 / メトリクス（将来的に拡張）

---

## 開発・運用上のヒント

- テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して外部 .env の影響を避けると安定します。
- DuckDB は単一ファイルで軽量に運用できます。バックアップはファイルコピーで可能です。
- J-Quants のリクエストはページネーションに対応しています。大量取得や全銘柄取得を行う場合はレート制御に留意してください。
- ニュースの RSS 取得はソースごとに独立してエラーハンドリングされます。1ソースの失敗が他ソースの収集を妨げません。

---

## 貢献・ライセンス

この README はコードベースのドキュメント生成を目的としています。実際にパッケージ化・配布する際は pyproject.toml / setup.cfg の整備、テストスイート、CI 設定、依存の固定（requirements.txt）等を追加してください。

ご質問や補足したい箇所があれば教えてください。README の追加改善（使い方の具体的なスクリプト例や運用手順の詳細化、CLI の追加案など）も対応します。