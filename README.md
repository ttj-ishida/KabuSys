# KabuSys

日本株向け自動売買プラットフォームのライブラリ群。データ取得（J-Quants / RSS）、ETL、データ品質チェック、監査ログ、及び実行（発注）レイヤーの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群です：

- J-Quants API / RSS 等から市場データ・ニュースを取得して DuckDB に保存する（Raw → Processed → Feature の3層データモデル）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を実行する
- ニュース収集・銘柄抽出（記事ID は正規化URLの SHA-256 を利用）を行う
- 監査ログ（シグナル→発注→約定）を永続化しトレーサビリティを確保する
- 実運用を意識した設計（レート制限尊重、リトライ、ID トークン自動リフレッシュ、冪等保存、SSRF対策 等）

設計上の要点：
- J-Quants API のレート制限（120 req/min）に従う RateLimiter を実装
- HTTP エラーやネットワークエラーに対するリトライ（指数バックオフ、401時はリフレッシュを1回実施）
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で実装
- RSS 収集は SSRF 対策・XML パース安全化（defusedxml）・受信サイズ制限を実施

---

## 機能一覧

- 環境変数管理（.env の自動読み込み、必須値チェック）
- J-Quants API クライアント
  - ID トークン取得（自動リフレッシュ）
  - 株価日足・財務データ・市場カレンダーのページネーション対応取得
  - レート制限・リトライ制御
  - DuckDB への冪等保存 (raw_prices, raw_financials, market_calendar)
- RSS ニュース収集
  - URL 正規化、トラッキングパラメータ削除、記事ID生成（SHA-256）
  - SSRF 対策（スキーム・プライベートアドレスチェック、リダイレクト検査）
  - gzip 対応、受信サイズ上限、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存（チャンクINSERT、トランザクション）
- DuckDB スキーマ定義と初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックス作成
- 監査ログ（signal_events / order_requests / executions）の初期化（data.audit）
- ETL パイプライン（data.pipeline）
  - 差分更新、backfill、calendar の先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- データ品質チェックモジュール（data.quality）

---

## セットアップ手順

前提：
- Python 3.9+（型注釈に Path | None などの記法を使っています）
- Git リポジトリのルートにプロジェクトを置くことを想定（.env 自動読み込みに使用）

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布がある場合）pip install -e .

   主要依存：
   - duckdb: ローカルDB
   - defusedxml: XML パーサの安全対策

4. 環境変数の設定
   - プロジェクトルートに `.env` と `.env.local`（任意）を置けます。config モジュールは自動で .env → .env.local を読み込みます（OS 環境変数を上書きしません。`.env.local` は上書き可）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   必須環境変数（少なくとも開発時に必要なもの）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID : Slack 通知先チャネル ID

   任意（デフォルト値あり）：
   - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化するフラグ (値は任意)

   .env の例（.env.example を参照して作成してください）：
   - JQUANTS_REFRESH_TOKEN=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - 下記の「使い方」参照

---

## 使い方（サンプル）

以下は主要な利用方法のサンプルです。Python から直接呼び出すことを想定しています。

1) DuckDB スキーマを初期化する
- data.schema.init_schema を使うと必要なテーブルとインデックスを作成します。

例：
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査ログ（order/event）用テーブルを追加する
- audit.init_audit_schema を呼ぶと監査用テーブルとインデックスを追加します。

例：
```python
from kabusys.data import audit, schema
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

3) 日次 ETL を実行する
- デフォルトで今日をターゲットに ETL を実行。品質チェックも行います。

例：
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は以下を順に実行します：
- 市場カレンダー ETL（先読み）
- 株価日足 ETL（差分 + backfill）
- 財務データ ETL（差分 + backfill）
- 品質チェック（data.quality） — 検出結果は ETLResult.quality_issues に格納

4) RSS ニュース収集ジョブを実行する
- デフォルトで定義された RSS ソースから記事を取得し raw_news に保存します。

例：
```python
from kabusys.data import news_collector, schema

conn = schema.init_schema("data/kabusys.duckdb")
# 既知の銘柄コードセットを渡すと news_symbols の紐付けも行われる
known_codes = {"7203", "6758"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) J-Quants API を直接利用する（ID トークン取得・データ取得）
```python
from kabusys.data import jquants_client as jq
# ID トークンは内部キャッシュを使う（必要時自動リフレッシュ）
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
# または手動で id_token を渡すことも可能
id_token = jq.get_id_token()
records = jq.fetch_financial_statements(id_token=id_token, ...)
```

---

## 主要モジュール説明 / ディレクトリ構成

リポジトリは src/package レイアウトになっています。主要ファイルは以下の通り。

- src/kabusys/
  - __init__.py                : パッケージ初期化（__version__）
  - config.py                  : 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - news_collector.py        : RSS ニュース収集・正規化・DB保存（SSRF対策等）
    - schema.py                : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py              : ETL（差分更新・backfill・品質チェック）の実装
    - audit.py                 : 監査ログテーブルの定義・初期化
    - quality.py               : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py              : 戦略関連（未実装ファイル群のプレースホルダ）
  - execution/
    - __init__.py              : 発注／実行関連（プレースホルダ）
  - monitoring/
    - __init__.py              : 監視関連（プレースホルダ）

各モジュールの役割：
- data.schema: 全テーブル（raw / processed / feature / execution）の DDL を保持し、初期化を行う。
- data.jquants_client: API への HTTP ロジック、ページネーション対応、取得結果の DuckDB への保存関数を提供。
- data.news_collector: RSS 取得→前処理→ID生成→raw_news/news_symbols 保存の ETL を提供。
- data.pipeline: 日次 ETL の orchestration と差分更新ロジックを実装。
- data.quality: ETL 後の品質チェックを行い、重大度付きの Issue を返す。
- data.audit: シグナルから約定に至る監査ログを保持するテーブルを定義する。

---

## 環境変数一覧（要/推奨）

必須（実運用で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知先）

任意 / デフォルトあり:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化したいときに設定

config.Settings を通じてこれらの値にアクセスできます（設定未済の場合は ValueError が発生します）。

---

## 運用上の注意

- J-Quants のレート制限とリトライポリシーを尊重していますが、大量の並列呼び出しは避けてください。モジュールはグローバルな _RateLimiter を使用しています。
- DuckDB のファイルは単一プロセスでの書き込み時に問題となる場合があります。複数ワーカーでの運用は注意してください（排他制御等）。
- RSS 収集は外部サイトにアクセスするため、SSRF 対策や受信サイズ制限を施しています。独自ソースを追加する場合は URL の検証に注意してください。
- データの完全性・品質は data.quality のチェック結果で監視してください。ETL はチェックでエラーが出ても継続する設計ですが、重大なエラーはアラートを出す運用が必要です。
- .env に機密情報（トークンやパスワード）を保存する場合は、リポジトリにコミットしないように注意してください。

---

## 開発 / テスト

- 自動 .env 読み込みは config.py 内でプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に行います。テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑制できます。
- 単体テスト用に jquants_client 内の HTTP 呼び出しや news_collector._urlopen などをモックしやすいように設計されています（関数やグローバルキャッシュを差し替え可能）。

---

## ライセンス / 貢献

（この README にはライセンスや貢献規約は含まれていません。必要に応じて LICENSE ファイル・CONTRIBUTING.md をプロジェクトルートに追加してください。）

---

質問やドキュメントの補足が必要であればお知らせください。README の補足（例: .env.example、CLI スクリプト、運用チェックリスト）も作成できます。