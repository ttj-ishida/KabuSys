# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants API や RSS を使ったデータ収集、DuckDB を用いたスキーマ定義・ETL、品質チェック、監査ログ管理などを提供します。

---

## プロジェクト概要

KabuSys は以下を主な目的とする Python パッケージです。

- J-Quants API から株価（日足）、財務データ、マーケットカレンダーを安全に収集するクライアント
- RSS フィードからニュース記事を収集して DuckDB に保存するニュースコレクタ
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution / Audit）の定義・初期化
- 日次 ETL パイプライン（差分取得・保存・品質チェック）の実行
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注〜約定の監査ログ（トレーサビリティ）を保つための監査スキーマ

設計上のポイント:
- API レート制御（J-Quants: 120 req/min）とリトライ・トークン自動リフレッシュ
- RSS 収集における SSRF・XML BOM 等の対策、レスポンスサイズ制限
- DuckDB へは冪等（ON CONFLICT）で保存
- 監査ログは削除せずタイムスタンプ・ステータスで経緯を残す

---

## 主な機能一覧

- data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - DuckDB への保存: save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - レートリミット制御・リトライ・401時のトークン自動更新
- data.news_collector
  - RSS 取得（fetch_rss）、記事前処理（URL 除去、空白正規化）、記事保存（save_raw_news）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、gzip 解凍制限、トラッキングパラメータ除去
  - 銘柄コード抽出（extract_stock_codes）と news_symbols への一括登録
- data.schema
  - DuckDB スキーマ定義（raw / processed / feature / execution）と init_schema()
- data.pipeline
  - 差分取得ロジックを備えた ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - 品質チェックとの統合（quality モジュール）
- data.quality
  - 欠損チェック、スパイク検出、重複チェック、日付不整合チェック
  - run_all_checks() でまとめて実行
- data.audit
  - 監査ログ用テーブル群の初期化（init_audit_schema / init_audit_db）
- config
  - .env（または環境変数）読み込み、自動ロード、必須変数チェック（Settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子などを使用）
- DuckDB を利用するためネイティブ依存がある場合はその環境を整えてください

1. リポジトリをクローンしてインストール（開発モード）
   - 推奨: 仮想環境を使用してください
   - 例:
     ```
     git clone <repo-url>
     cd <repo-dir>
     pip install -e .
     ```
   - 依存パッケージ（主なもの）:
     - duckdb
     - defusedxml

   直接インストールする場合:
   ```
   pip install duckdb defusedxml
   ```

2. 環境変数 / .env を準備する
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUS_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   - .env の記述例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（簡易例）

以下はパッケージをインポートして各機能を使う最小例です。実運用ではログ設定や例外処理、スケジューラ（cron）などを組み合わせてください。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルなければ作成、:memory: も可
   ```

2. 監査ログスキーマの追加
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # 既存接続へ監査テーブルを追加
   ```

3. J-Quants トークン取得（手動）
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings に JQUANTS_REFRESH_TOKEN が設定されている必要あり
   ```

4. 日次 ETL の実行（run_daily_etl）例
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しなければ本日
   print(result.to_dict())
   ```

5. RSS ニュース収集の実行例
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   saved = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
   print(saved)
   ```

6. 個別保存関数の利用例
   - fetch_* 関数でデータを取得し、save_* 関数で DuckDB に保存します。
   - 例: fetch_daily_quotes → save_daily_quotes（どちらも jquants_client モジュール）

注意点:
- jquants_client は内部でレート制御・リトライを行います（120 req/min, 最大3回リトライ）。401 は自動リフレッシュを試みます。
- news_collector は SSRF 対策、XML の安全パース（defusedxml）、レスポンスサイズ制限（10MB）などを行います。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id
  - settings.duckdb_path, settings.sqlite_path, settings.env, settings.log_level, settings.is_live / is_paper / is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（全テーブル作成）
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None) -> dict[source -> saved_count]
  - extract_stock_codes(text, known_codes)

- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...), run_financials_etl(...), run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, run_quality_checks=True, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## ディレクトリ構成

（パッケージの主要ファイルと役割の一覧）

- src/kabusys/
  - __init__.py  - パッケージ初期化、バージョン情報
  - config.py    - 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得 + 保存 + レート制御/リトライ）
    - news_collector.py     - RSS 取得・前処理・DB保存・銘柄紐付け
    - schema.py             - DuckDB スキーマ定義と init_schema
    - pipeline.py           - ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py              - 監査ログ用テーブル定義・初期化
    - quality.py            - データ品質チェック
  - strategy/
    - __init__.py           - 戦略関連（拡張ポイント）
  - execution/
    - __init__.py           - 実行（注文送信・ポジション管理）関連（拡張ポイント）
  - monitoring/
    - __init__.py           - 監視・メトリクス関連（拡張ポイント）

---

## 運用上の注意・ベストプラクティス

- 環境変数は機密情報を含むため、リポジトリに直接コミットしないでください。`.env.example` を参照して `.env` を作成してください。
- DuckDB ファイルは定期的にバックアップしてください（特に監査ログを保存している場合）。
- J-Quants のレート制限に従い、短時間で大量に API を叩かないようにしてください。ライブラリはレート制御を行いますが、上限を超えるリトライや同時実行は避けてください。
- news_collector は外部の RSS を多数取得するため、ネットワークのリトライ・タイムアウト設定やエラーハンドリングを組み合わせてください。
- 本ライブラリは複数プロセスで同時に同一 DuckDB ファイルへ書き込む用途には注意が必要です（DuckDB の同時書き込み特性を理解してください）。

---

## 開発・テスト

- 自動で .env を読み込む挙動をテスト用に無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 単体テストを行う場合、DuckDB のインメモリ（":memory:"）を使うと簡単です。
- モジュール内のネットワーク呼び出し（_urlopen や jquants_client._request など）はモック可能に設計されています。ユニットテストでは外部呼び出しをモックしてください。

---

## ライセンス / 貢献

- （ここにライセンス情報を記載してください）
- バグ報告・改善提案・プルリクエスト歓迎します。貢献ガイド（CONTRIBUTING.md）があればそちらに従ってください。

---

README は基本的な利用手順を示しています。実際の運用ではログ設定、例外ハンドリング、スケジューリング、監視・アラート連携（Slack 通知等）を組み合わせて運用してください。必要であれば各モジュールの使い方サンプルや CLI スクリプトの記載も追記します。