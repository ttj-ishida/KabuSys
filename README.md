# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買/データ基盤ライブラリです。J-Quants API から株価・財務・マーケットカレンダーを取得し、DuckDB に保存・管理します。ニュース収集・データ品質チェック・監査ログ（発注→約定のトレーサビリティ）など、運用を考慮した各種ユーティリティを備えています。

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レートリミット（120 req/min）順守 / 再試行ロジック（指数バックオフ） / トークン自動リフレッシュ
  - フェッチ時刻（fetched_at）を UTC で記録し Look-ahead Bias を回避
  - DuckDB へ冪等保存（ON CONFLICT を使用）

- ETL パイプライン
  - 差分取得（最終取得日を基に必要分のみ取得）
  - バックフィル機能で API の後出し修正に対応
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集（RSS）
  - RSS から記事を取得して前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
  - SSRF 対策、gzip サイズ制限、XML の安全パース（defusedxml）
  - 銘柄コード抽出・news_symbols への紐付け処理

- マーケットカレンダー管理
  - JPX カレンダーの差分更新バッチ
  - 営業日／前後営業日算出（DB のデータを優先、未登録日は曜日フォールバック）

- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティを保持
  - 発注の冪等キー（order_request_id）や各種ステータス管理

- DuckDB ベースのスキーマ定義（Raw / Processed / Feature / Execution 層）

---

## 要件

- Python 3.10 以上（型ヒントに `|` を使用）
- 必要パッケージ（主要なもの）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging など

インストール例:
```bash
python -m pip install duckdb defusedxml
```

（プロジェクト配布時に requirements.txt や pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／配置し、Python 環境を準備する。

2. 環境変数を設定する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabuステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN        : Slack 通知を行う場合
     - SLACK_CHANNEL_ID       : Slack 送信先チャンネルID
   - 任意 / デフォルト:
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | ...（デフォルト: INFO）
     - DUCKDB_PATH : データベースファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite（デフォルト: data/monitoring.db）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトで `kabusys.data.schema.init_schema()` を呼んで DB とテーブルを作成します。

   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

4. （任意）監査ログ用 DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な API／ジョブ）

ここでは代表的な操作のコード例を示します。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  - run_daily_etl は市場カレンダー取得→株価・財務データ差分取得→品質チェックを順に実行します。
  - ETLResult を返し、取得/保存件数や品質問題・エラー情報が含まれます。

- 市場カレンダーの夜間更新ジョブを実行する
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved", saved)
  ```

- RSS ニュース収集（単一ソース）
  ```python
  from kabusys.data.news_collector import fetch_rss, save_raw_news
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = save_raw_news(conn, articles)
  print("new articles:", len(new_ids))
  ```

- ニュース一括収集（run_news_collection）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: {'7203', '6758', ...}）
  stats = run_news_collection(conn, known_codes={'7203','6758'})
  print(stats)
  ```

- J-Quants のトークン取得（内部で自動的に使われますが明示的にも取得可能）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を元に発行
  ```

- 監査テーブル初期化（既存接続に対して追加）
  ```python
  from kabusys.data import audit, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn, transactional=True)
  ```

---

## 設計・安全上のポイント

- API レート制御（120 req/min）とリトライ（408/429/5xx）を実装済み。
- トークン自動リフレッシュを行い、401 受信時に 1 回だけ再試行します。
- DuckDB への保存は冪等化（ON CONFLICT DO UPDATE/DO NOTHING）されています。
- ニュース取得は defusedxml を使った安全な XML パース、SSRF 対策（スキーム検証・プライベートIP拒否）、レスポンスサイズ制限（10MB）を実装。
- データ品質チェックを行い、ETL 実行後に欠損・重複・スパイク・将来日付などを検出可能。
- 監査ログは UTC タイムゾーンで統一し、削除しない前提の設計（FK は ON DELETE RESTRICT 等）です。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) — Slack bot トークン
- SLACK_CHANNEL_ID (必須 for Slack) — Slack チャネル ID
- DUCKDB_PATH — DuckDB データファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で .env を読み込ませたくない場合に 1 を設定

設定値は kabusys.config.settings 経由で参照できます。

---

## ディレクトリ構成

（リポジトリの一部を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（fetch/save）
      - news_collector.py        # RSS ニュース収集・保存
      - schema.py                # DuckDB スキーマ定義・初期化
      - pipeline.py              # ETL パイプライン（run_daily_etl など）
      - calendar_management.py   # カレンダー管理・夜間更新ジョブ
      - audit.py                 # 監査ログ（signal/order_request/execution）
      - quality.py               # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

この README は主要モジュールと API の利用方法をまとめたものです。個々の関数やクラスには docstring（日本語注釈含む）が付与されていますので、詳細はソースコード／docstring を参照してください。

---

## トラブルシューティング / 注意点

- DuckDB の接続は軽量ですが、同一ファイルへ複数プロセスで同時書き込みする場合は注意してください（ロック等の影響）。
- J-Quants の API 仕様変更やレスポンスフォーマット変更があれば、jquants_client 内のパースロジックや保存先スキーマを更新する必要があります。
- news_collector のネットワーク呼び出しは外部サイトへ接続します。企業ネットワークやテスト環境ではアクセス制限（プロキシ、ファイアウォール）に注意してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると安全です。

---

必要であれば、README に動作確認手順（サンプルデータを用いたフル ETL 実行例）や、CI / デプロイ手順、さらに詳細な環境変数テンプレート（.env.example）を追加します。どの情報を優先して追記しますか？