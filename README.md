# KabuSys

日本株向け自動売買基盤ライブラリ (KabuSys)

このリポジトリは、日本株のデータ収集（J-Quants / RSS）、ETL、データ品質チェック、監査ログなどを備えた自動売買プラットフォームのコアライブラリ群です。DuckDB をデータ層に用い、冪等性・トレーサビリティ・セキュリティ対策（SSRF/圧縮爆弾対策等）を考慮して設計されています。

Version: 0.1.0

---

## 概要（Project overview）

KabuSys は以下の責務を持つモジュール群を提供します。

- J-Quants API から株価（日足/OHLCV）、財務情報、取引カレンダーを取得するクライアント（自動トークン刷新・リトライ・レートリミット対応）
- RSS フィードからニュースを収集し前処理・正規化して保存するニュースコレクタ（SSRF対策・トラッキング除去）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェックを含む日次処理）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（シグナル→発注→約定までのトレースを保証するテーブル群）

設計上のポイント：
- 冪等性（ON CONFLICT / INSERT ... RETURNING を多用）
- Look-ahead bias 防止（fetched_at / UTC の厳格な記録）
- 外部入力の安全性（XML パーサの hardening、SSRF 検査、レスポンスサイズ制限）
- DuckDB による高速なローカル解析と永続化

---

## 主な機能一覧（Features）

- J-Quants クライアント
  - ID トークンの自動更新（refresh token → id token）
  - レートリミット（120 req/min）順守
  - リトライ（指数バックオフ、最大 3 回、401 の場合はトークン再取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存 save_... 系関数

- ニュース収集
  - RSS フィード取得（gzip 対応）
  - URL 正規化（utm 等トラッキング除去）
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）
  - SSRF 防止（スキーム検査・DNS 解決によるプライベートIP排除・リダイレクト検査）
  - raw_news / news_symbols テーブルへの冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出ロジック（4桁の数値と known_codes）

- スキーマ / 初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema, init_audit_schema により自動作成（冪等）

- ETL パイプライン
  - run_daily_etl: カレンダー・株価・財務の差分取得、品質チェック
  - バックフィル（日次差分の再取得）対応
  - 品質チェックを独立実行し、問題を一覧で返す設計

- 品質チェック
  - 欠損（OHLC）検出
  - スパイク（前日比）検出
  - 重複（PK 重複）検出
  - 日付不整合（未来日付・非営業日データ）検出

- 監査ログ
  - signal_events / order_requests / executions 等により発注フローをトレース

---

## セットアップ手順（Setup）

前提:
- Python 3.10 以上（型注釈で | を利用）
- Git（.git または pyproject.toml をプロジェクトルートとして検出）

1. リポジトリをクローンし、開発用仮想環境を作成・有効化します。

   bash:
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストールします（最低限の依存）。

   bash:
   - pip install duckdb defusedxml

   補足:
   - 本コードは標準ライブラリの urllib を使用しているため requests は必須ではありません。
   - 実運用では Slack 連携やその他のクライアントを使う場合、別途対応パッケージを追加してください。

3. 環境変数の準備 (.env)

   プロジェクトルート（.git のあるディレクトリか pyproject.toml がある場所）に `.env` を置くと自動読み込みされます（環境変数優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settings クラスで require されるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - DUCKDB_PATH, SQLITE_PATH はデフォルトを持つ

4. DuckDB スキーマ初期化:

   Python REPL / スクリプト例:
   ```
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルに永続化
   # またはインメモリ:
   # conn = init_schema(":memory:")
   ```

---

## 使い方（Usage）

以下は代表的な操作のサンプルです。

- J-Quants からデータを取得・保存（ETL の実行）

  Python スクリプト例:
  ```
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 今日を対象に ETL を実行
  print(result.to_dict())
  ```

  オプション:
  - run_daily_etl(..., target_date=some_date) で任意の日付を指定
  - id_token を直接渡してテストすることも可能

- 単体で株価取得・保存

  ```
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集

  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes: 有効な銘柄コードのセット（抽出に使用）
  known_codes = {"7203", "6758", "9984"}
  result = run_news_collection(conn, known_codes=known_codes)
  print(result)  # {source_name: saved_count, ...}
  ```

- 品質チェック単体実行

  ```
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査ログ初期化（監査用テーブルを追加）

  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

---

## 環境変数と自動読み込みの挙動

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` と `.env.local` があれば自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - 自動読み込みを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings（kabusys.config.settings）が環境変数を提供します。必須変数がなければ ValueError が発生します。

---

## ディレクトリ構成（Directory structure）

リポジトリの主要ファイル・モジュールは以下の通りです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集・保存
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - audit.py                     -- 監査ログ（signal/order/execution）
      - quality.py                   -- データ品質チェック
    - strategy/
      - __init__.py                  -- 戦略層（拡張場所）
    - execution/
      - __init__.py                  -- 発注実装（ブローカ連携）
    - monitoring/
      - __init__.py                  -- 監視・メトリクス（拡張場所）

各モジュールは責務ごとに分離されており、テストしやすいようにトークン注入や _urlopen の差し替えポイント等が用意されています。

---

## 注意事項 / 運用メモ

- J-Quants の API レート制限（120 req/min）を尊重してください。本クライアントは固定間隔スロットリングで保護しますが、運用負荷が高い場合はさらに調整が必要です。
- ニュース収集では外部フィードの挙動（巨大レスポンス、gzip bomb、リダイレクト）に対する防御を組み込んでいますが、未知のケースに備えてログ監視を行ってください。
- DuckDB のファイルはアプリケーションによって排他制御されていることを確認してください（複数プロセスからの同時書き込みは運用設計に注意）。
- audit テーブルは UTC タイムゾーンで timestamp を保存する設計です（init_audit_schema は TimeZone='UTC' をセットします）。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すると .env 自動ロードを抑止できます。news_collector の _urlopen 等はモック可能です。

---

## 参考 / 開発を始めるために

- まずはローカルで DuckDB を初期化し、run_daily_etl を実行してみてください。ログレベルを DEBUG にすると内部挙動（トークン刷新、リトライ、保存行数など）が確認できます。
- strategy / execution / monitoring の各パッケージは骨格のみなので、個別の戦略ロジックやブローカーAPIラッパーはここに実装してください。

---

もし README に含めたい追加情報（CI、テスト実行方法、pyproject.toml / packaging 手順、具体的な Slack 通知フローの例など）があれば教えてください。それに合わせて追記を作成します。