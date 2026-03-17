# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントはローカル開発者・運用者向けにプロジェクト概要、機能、セットアップ・使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータパイプラインと自動売買（戦略・発注・監査）を支えるライブラリ群です。主に以下を目的とします。

- J-Quants API などから株価・財務・マーケットカレンダーを取得して DuckDB に格納する ETL パイプライン
- RSS からニュースを収集して記事と銘柄の紐付けを行うニュースコレクタ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマの管理
- 発注周り・戦略・モニタリングのためのパッケージ構造（拡張ポイント）

設計上の特徴として、API レート制御、リトライ、冪等性（ON CONFLICT）、SSRF 対策や XML の安全パースなど信頼性・安全性に配慮しています。

---

## 主な機能一覧

- データ取得
  - J-Quants から株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得（ページネーション対応）
  - API レート制限（120 req/min）・リトライ・トークン自動リフレッシュを実装
- データ保存（DuckDB）
  - raw / processed / feature / execution / audit の多層スキーマを提供
  - ON CONFLICT を使った冪等保存
- ETL / パイプライン
  - 差分更新、バックフィル日数調整、カレンダー先読み、品質チェック
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS 取得、コンテンツ前処理、記事IDは正規化URLのSHA-256（先頭32文字）
  - SSRF/XXE対策、受信サイズ制限、DuckDB へのバルク挿入
  - 記事→銘柄コードの紐付け
- 品質チェック
  - 欠損データ、スパイク、主キー重複、日付不整合などを検出する一連のチェック
- 監査ログ
  - signal_events / order_requests / executions 等の監査スキーマを提供
- 設定管理
  - .env / .env.local / OS 環境変数の取り込み（自動ロード）・必須チェック（Settings オブジェクト）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   - このパッケージは project root を `.git` または `pyproject.toml` から検出します。

2. Python 環境の準備（例: venv）
   - python >= 3.9 を想定
   - 仮想環境作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（代表例）
   - 必須: duckdb, defusedxml
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数の準備
   - プロジェクトルートに `.env` （および開発用に `.env.local`）を置くと自動で読み込まれます（CWD に依存せず、パッケージファイル位置を基準に探索）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略時は上記デフォルト)
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb   (任意)
     - SQLITE_PATH=data/monitoring.db    (任意)
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)

   - 例（.env）
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C1234567890
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG

5. データベース初期化
   - DuckDB スキーマを作成:
     - Python REPL またはスクリプトで:
       from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")
   - 監査スキーマを既存接続に追加:
       from kabusys.data.audit import init_audit_schema
       init_audit_schema(conn)
   - 監査専用 DB を作る場合:
       from kabusys.data.audit import init_audit_db
       audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な API と実行例）

以下は代表的な使い方の抜粋です。実際の運用スクリプトはアプリケーション側で組み立ててください。

- 設定を読む（Settings）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live などを参照

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - result は ETLResult オブジェクト（取得数・保存数・quality_issues・errors などを含む）

- 個別 ETL ジョブ
  - run_prices_etl(conn, target_date)
  - run_financials_etl(conn, target_date)
  - run_calendar_etl(conn, target_date)
  - これらは引数で id_token を注入可能（テスト容易性）

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=my_known_codes_set)
  - fetch_rss, save_raw_news などの個別関数も利用可能

- J-Quants トークン取得
  - from kabusys.data.jquants_client import get_id_token
  - id_token = get_id_token()  # settings.jquants_refresh_token を自動利用

- 品質チェックを単体で実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=some_date)

- 監査スキーマ初期化（既に init_schema で作った conn を渡す）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)

- ロギング設定
  - settings.log_level を参照してアプリ側で logging.basicConfig(level=...)

注意事項:
- J-Quants API はレート制限（120 req/min）に合わせた内部 RateLimiter とリトライロジックを持ちます。
- get_id_token はリフレッシュトークンから ID トークンを取得し、401 時には自動リフレッシュを試みます。
- ニュース収集では SSRF 対策や XML の安全なパース（defusedxml）を行っています。

---

## ディレクトリ構成

主要なソースファイルと想定構成は以下の通りです。一部モジュール（strategy, execution, monitoring）は拡張ポイントとして空の __init__.py が配置されています。

- src/kabusys/
  - __init__.py                  (パッケージ定義、__version__)
  - config.py                    (環境変数 / Settings)
  - data/
    - __init__.py
    - jquants_client.py          (J-Quants API クライアント、保存ロジック)
    - news_collector.py          (RSS → raw_news, news_symbols)
    - schema.py                  (DuckDB スキーマ定義と init_schema / get_connection)
    - pipeline.py                (ETL パイプライン・run_daily_etl 等)
    - audit.py                   (監査ログスキーマの定義と初期化)
    - quality.py                 (データ品質チェック)
  - strategy/
    - __init__.py                (戦略関連の拡張ポイント)
  - execution/
    - __init__.py                (発注・約定管理の拡張ポイント)
  - monitoring/
    - __init__.py                (モニタリング機能の拡張ポイント)

その他:
- .env, .env.local               (環境ごとの設定ファイル、プロジェクトルートに配置)
- data/                          (デフォルトの DB 保存先ディレクトリなど)

---

## 運用上のポイント / ベストプラクティス

- 環境分離: KABUSYS_ENV を `development` / `paper_trading` / `live` から選択し、本番用設定は安全に管理してください。
- シークレット管理: .env にアクセストークンを置く場合は Git 管理を避け、`.env.local` を使いローカルのみで管理すること。
- 自動 .env ロード: パッケージはプロジェクトルート（.git または pyproject.toml）を自動検出して .env を読み込みます。テストで読み込みを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB バックアップ: DuckDB ファイルは定期的にバックアップしてください。監査ログは削除しない前提です。
- テスト: ETL・ニュース取得などは id_token を引数で注入できるため、外部呼び出しをモックしてユニットテストしやすい構造になっています。

---

必要があれば、README に「API リファレンス」「運用スクリプト例」「.env.example のテンプレート」などを追加します。どの部分を詳しく拡張しましょうか？