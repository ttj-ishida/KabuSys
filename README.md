# KabuSys

日本株自動売買システムのコアライブラリ (読み取り専用ドキュメント)

このリポジトリ内のモジュール群は、データ収集（J-Quants / RSS）、ETL、データ品質チェック、監査ログ、カレンダー管理、発注ワークフロー基盤などを提供します。実際の発注処理は外部ブリッジ（kabuステーション等）と連携して行う想定です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下を目的とします。

- J-Quants API から株価・財務・マーケットカレンダーを取得するクライアント
- RSS からニュースを収集して DuckDB に保存するニュースコレクタ
- DuckDB を用いた三層データプラットフォーム（Raw / Processed / Feature）スキーマと初期化機能
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計方針として冪等性、レート制御、リトライ、SSRF対策、メモリDoS対策（受信上限）などを踏まえた実装がなされています。

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env, .env.local を自動ロード（無効化可）
  - 必須変数チェック

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期）取得
  - マーケットカレンダー取得
  - Rate limiter、リトライ、401時の自動トークンリフレッシュ
  - DuckDB へ冪等に保存する save_* 関数

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、安全な XML パーシング（defusedxml）
  - URL 正規化・ID 作成（SHA-256 先頭32文字）
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - 受信サイズ上限、gzip 解凍対応
  - DuckDB へ冪等保存（INSERT ... RETURNING）

- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、init_schema() による初期化

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、品質チェックの統合 run_daily_etl()
  - 個別 ETL 実行 (run_prices_etl, run_financials_etl, run_calendar_etl)
  - 品質チェック（kabusys.data.quality）との統合

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、期間内営業日一覧取得
  - calendar_update_job() による夜間差分更新

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブル初期化
  - init_audit_db() による専用 DB 初期化（UTC 固定）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合などのチェック関数

---

## セットアップ手順

ここでは基本的な開発/実行環境のセットアップ手順を示します。

1. Python 環境を用意（推奨: 3.9+）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 必須:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （このリポジトリに pyproject.toml / requirements.txt があればそちらを利用してください）

3. 環境変数の準備
   - ルートディレクトリに .env または .env.local を配置できます。
   - 自動ロードはデフォルトで有効（kabusys.config がプロジェクトルートを探索して読み込みます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 最低限必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化（ローカル DB を作る）
   - 例:
     - python の REPL やスクリプトで:
       ```
       from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")
       ```
     - 監査ログ専用 DB を初期化する:
       ```
       from kabusys.data.audit import init_audit_db
       audit_conn = init_audit_db("data/kabusys_audit.duckdb")
       ```
5. ログ設定
   - LOG_LEVEL 環境変数でログレベルを制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 使い方（基本例）

以下は典型的な利用例です。実行は Python スクリプトまたは Jupyter 等から行います。

- DuckDB スキーマを初期化して日次 ETL を実行する例:
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB を初期化して接続を取得（ファイルは自動的に親ディレクトリを作成）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL を実行（対象日省略で今日が対象）
  result = run_daily_etl(conn)

  # 結果を表示（ETLResult.to_dict() が利用可能）
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行例:
  ```
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")

  # known_codes を渡すことで記事中の銘柄（4桁）を抽出して紐付ける
  known_codes = {"7203", "6758", "9984"}  # 任意のコードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants の id_token を直接取得する例:
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照して取得
  print(token)
  ```

- ETL の個別実行（株価のみ等）:
  ```
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- 監査ログ用 DB 初期化:
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（モニタリング用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化 (1)

kabusys.config.Settings クラスを通じて設定にアクセスできます:
```
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## ディレクトリ構成

主要なファイル・モジュールを示します（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / .env 読み込み・設定クラス
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント (fetch/save)
    - news_collector.py            -- RSS ニュース収集 & 保存
    - schema.py                    -- DuckDB スキーマ定義 / init_schema
    - pipeline.py                  -- ETL パイプライン (run_daily_etl 等)
    - calendar_management.py       -- マーケットカレンダー管理
    - audit.py                     -- 監査ログスキーマ / init_audit_db
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略関連モジュール（未実装/プレースホルダ）
  - execution/
    - __init__.py                  -- 発注実行関連（未実装/プレースホルダ）
  - monitoring/
    - __init__.py                  -- 監視・メトリクス（未実装/プレースホルダ）

（上記はリポジトリ内の主要モジュールのみ。各ファイルに詳細な docstring と設計方針が記載されています）

---

## 注意点・設計上のポイント

- 冪等性:
  - jquants_client の save_* 関数や news_collector の保存処理は ON CONFLICT を用いるなどして幾度でも安全に実行できるよう設計されています。

- レート制御・リトライ:
  - J-Quants API に対しては 120 req/min のレート制御とリトライロジック（指数バックオフ、401 自動リフレッシュ等）があります。

- セキュリティ:
  - news_collector は defusedxml を使用して XML 爆弾を防ぎ、SSRF 対策（スキーム検証・プライベートIP 排除）を実装しています。
  - RSS の受信は最大サイズで制限され、gzip 解凍後もチェックします。

- 品質チェック:
  - ETL 後に複数の品質チェックを実行できます（欠損、スパイク、重複、日付不整合）。重大度の高い問題は呼び出し側で対処してください（ETL は可能な限り継続して実行する設計）。

---

## 開発・拡張のヒント

- テスト:
  - jquants_client の _urlopen や news_collector のネットワーク呼び出しは差し替え（モック）しやすいよう設計されています。
- 外部サービス連携:
  - Slack 通知や kabuステーションとのブリッジは別モジュールで実装して連携させる想定です（設定は settings 経由で取得）。
- 実運用:
  - 本番環境では KABUSYS_ENV=live をセットし、ログや監視、取引実行の厳格なハンドリングを追加してください。

---

必要であれば、README にサンプル .env.example、より詳しい API 使用例（関数別の引数説明）、あるいは運用手順（cron / Airflow / Kubernetes ジョブの例）を追加できます。どの情報を優先して拡張しますか？