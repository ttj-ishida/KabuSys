# KabuSys

日本株自動売買基盤ライブラリ（KabuSys）のリポジトリ README。  
この README はコードベース（src/kabusys）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けユーティリティ群です。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、財務、JPX カレンダー）
- DuckDB を利用したデータスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（前処理・SSRF対策・冪等保存・銘柄紐付け）
- マーケットカレンダー管理（営業日判定、次/前営業日の取得）
- 監査（audit）スキーマ（シグナル→発注→約定のトレーサビリティ）
- 各種ユーティリティ（環境変数ロード、設定管理、ログレベル管理 等）

設計上の特徴：
- API レート制限とリトライを組み込んだ堅牢なクライアント実装
- DuckDB に対する冪等な保存（ON CONFLICT）とトランザクション管理
- SSRF や XML Bomb 等への対策を組み込んだニュース収集
- 品質チェック（欠損・重複・スパイク・日付不整合）の実装

---

## 主な機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV / LOG_LEVEL の検証

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制御、リトライ、401時のトークン自動リフレッシュ
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル、品質チェックの統合

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS 取得、前処理、記事ID生成（正規化URL の SHA-256 先頭32文字）
  - SSRF・圧縮・サイズ制限・defusedxml による安全なパース
  - raw_news / news_symbols への冪等保存

- スキーマ管理（src/kabusys/data/schema.py）
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution / Audit 用）
  - init_schema / get_connection

- カレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、前/次営業日取得、期間内営業日リスト
  - calendar_update_job（夜間バッチでJPXカレンダー差分取得）

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions など監査テーブルの初期化 helper

- 品質チェック（src/kabusys/data/quality.py）
  - 欠損、スパイク、重複、日付不整合チェックと QualityIssue 抽象

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.9+（型アノテーションに | を使用しているため 3.10 以上が望ましい）
- system のパッケージマネージャが利用可能

1. 仮想環境を作成・有効化（任意だが推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール
   最低限必要な外部依存は `duckdb` と `defusedxml` です（標準ライブラリ以外）。
   ```
   pip install duckdb defusedxml
   ```
   ※ 実運用で Slack 等と連携する機能を追加する場合は別途パッケージが必要になる場合があります。

3. パッケージとして編集可能インストール（任意）
   リポジトリルートに pyproject.toml または setup.py がある想定で:
   ```
   pip install -e .
   ```

4. 環境変数の準備
   プロジェクトルートに `.env`（または `.env.local`）を作成します。自動ロードは以下を参照。

---

## 環境変数（主要なもの）

config.Settings で参照する主な環境変数と説明:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token() の元になります。

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード。

- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン（今後の拡張向け）。

- SLACK_CHANNEL_ID (必須)
  - Slack 通知先のチャンネル ID。

- DUCKDB_PATH (任意)
  - DuckDB ファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - 監視用 SQLite DB パス。デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)
  - 動作モード: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 値を `1` にすると .env の自動読み込みを無効にできます（テスト用）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=passw0rd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロード:
- リポジトリのプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` を読み込み、`.env.local` が存在すれば上書きします（OS 環境変数は保護されます）。

---

## 使い方（よく使う API とサンプル）

以下はパイプラインや初期化でよく使う API の例です。実行は Python スクリプトや REPL から行います。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)  # ファイルDBを作成して接続を返す
  # またはメモリDB:
  # conn = schema.init_schema(":memory:")
  ```

- 日次 ETL を実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from kabusys.config import settings
  from datetime import date

  conn = schema.get_connection(settings.duckdb_path)  # 事前に init_schema を実行しておく
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コードのセット（抽出時に参照）
  res = run_news_collection(conn, known_codes={"7203", "6758"})  # e.g. トヨタ、ソニー 等
  print(res)  # {source_name: saved_count, ...}
  ```

- J-Quants の個別利用（トークン取得・日足取得）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  # get_id_token() は settings.jquants_refresh_token を参照します
  token = get_id_token()
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 監査スキーマを初期化（監査専用DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 品質チェックの実行（個別或いは ETL 内から呼ばれる）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

設計上の注意:
- J-Quants クライアントは 120 req/min の制限を考慮した RateLimiter を実装しています。大量取得を行う際はレートに注意してください。
- fetch_* 系はページネーション対応です。401 発生時はトークン自動更新を行い1回リトライします。
- DB 書き込み関数は冪等性を保つため ON CONFLICT を利用しています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリルートに src/ がある想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数・設定管理
    - execution/                     -- 発注・実行関連モジュール（未展開）
      - __init__.py
    - strategy/                      -- 戦略関連（未展開）
      - __init__.py
    - monitoring/                    -- 監視関連（未展開）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - pipeline.py                  -- ETL パイプライン（差分更新、品質チェック）
      - calendar_management.py       -- カレンダー管理・営業日判定
      - audit.py                     -- 監査スキーマ（signal/order/execution）
      - quality.py                   -- データ品質チェック
- pyproject.toml or setup.py (プロジェクトルートで .env 自動読み込みの基準に利用)

---

## データベース（DuckDB）テーブル群（概要）

主要テーブル（抜粋）:

- Raw Layer
  - raw_prices
  - raw_financials
  - raw_news
  - raw_executions

- Processed Layer
  - prices_daily
  - market_calendar
  - fundamentals
  - news_articles
  - news_symbols

- Feature Layer
  - features
  - ai_scores

- Execution Layer
  - signals
  - signal_queue
  - orders
  - trades
  - positions
  - portfolio_performance

- Audit（監査）
  - signal_events
  - order_requests
  - executions

初期化は data.schema.init_schema(db_path) を利用してください。監査スキーマは data.audit.init_audit_schema/init_audit_db を利用します。

---

## 運用上の注意とベストプラクティス

- 環境変数は機密情報を含むため `.env` を git 管理しないでください（`.env.example` を用意して雛形のみを共有する運用が推奨されます）。
- 自動ロードを無効化したいテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ETL 実行時は ETLResult の has_errors / has_quality_errors をチェックし、アラートや手動介入を行ってください。
- ニュース収集では既知の銘柄コードリスト（known_codes）を持っておくとノイズを減らせます。
- DuckDB ファイルは定期的にバックアップを行ってください（特に監査ログなど消えない前提のデータ）。

---

## 追加の参考/拡張

- Slack 通知や kabuステーションとのインテグレーションは設定変数を利用できる設計になっています。実運用での連携は別途実装（SDK の導入や execution レイヤの完成）が必要です。
- モジュールはテスト可能性を考慮して id_token の注入や _urlopen のモック差し替えが可能です。CI での単体テスト作成が容易です。

---

もし README に追加してほしい内容（例: 実行用の systemd ユニット例、cron/airflow 連携例、より詳細な環境変数ドキュメント、サンプル .env.example）や、日本語のサンプル出力・スクリーンショット等があれば教えてください。