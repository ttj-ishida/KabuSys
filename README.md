# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、監査ログ用スキーマなど、戦略実行に必要な基盤機能を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で安全に保存
- API レート制限・リトライ・トークン自動リフレッシュを実装
- ニュース収集は SSRF / XML Bomb / メモリ DoS 等に対する防御を実装
- データ品質チェックを行い、問題を検出して監査できるようにする
- 発注〜約定に至る監査ログを専用スキーマで保存（トレーサビリティ確保）

---

## 機能一覧

- 環境変数／設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須設定の取得とバリデーション（KABUSYS_ENV, LOG_LEVEL 等）
  - settings オブジェクト経由でアクセス可能

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、四半期財務データ、JPX カレンダー取得
  - 固定間隔レート制御（120 req/min）
  - 指数バックオフのリトライ（408/429/5xx）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_*）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理（URL除去・空白正規化）
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256 ハッシュ）
  - SSRF 回避、gzip 制限、defusedxml による安全な XML パース
  - raw_news / news_symbols テーブルへの冪等保存（チャンク INSERT、RETURNING 利用）

- データベーススキーマ管理（kabusys.data.schema）
  - DuckDB 用の Raw / Processed / Feature / Execution 層の DDL を定義
  - init_schema(db_path) で自動作成（冪等）
  - get_connection(db_path) で既存 DB に接続

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日に基づく自動計算、backfill 対応）
  - カレンダー先読み、株価／財務の差分取得と保存
  - 品質チェックの実行（quality モジュール）と結果集約
  - run_daily_etl により一括実行・結果取得

- 品質チェック（kabusys.data.quality）
  - 欠損データ・重複・スパイク（前日比）・日付不整合チェック
  - QualityIssue オブジェクトで問題を返却（severity: error/warning）
  - run_all_checks でまとめて実行

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブル
  - init_audit_schema(conn) で既存 DuckDB 接続に追加する初期化関数
  - 監査トレースのための制約、タイムゾーンやインデックス対応

---

## 動作環境（推奨）

- Python 3.10+
- 必要な主要依存ライブラリ（例）
  - duckdb
  - defusedxml
  - （その他、実際の配布パッケージの requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - プロジェクトルートには .git または pyproject.toml のいずれかがあることを期待します（自動 .env ロード用）。

2. 仮想環境作成・依存インストール
   - 例：
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     # または開発時:
     pip install -e .
     ```

3. 環境変数の設定
   - 環境変数は OS 環境、またはプロジェクトルートの .env / .env.local から自動読み込みされます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

   推奨する主要環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite / 監視 DB パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（省略時: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（省略時: INFO）

   例 .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化
   - DuckDB スキーマを作成:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # ファイルパス文字列または Path オブジェクト
     ```

   - 監査ログスキーマを同じ接続に追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（簡易例）

- settings を使った設定参照:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  ```

- 日次 ETL 実行（run_daily_etl）:
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants からの個別データ取得:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して id_token を取得
  records = fetch_daily_quotes(id_token=token, code="7203", date_from=..., date_to=...)
  ```

- 品質チェックだけを実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意:
- run_daily_etl 等の関数はエラーハンドリングを内部で行い、可能な限り処理を継続します。戻り値の ETLResult からエラーや品質問題の有無を確認してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にすることができます。

---

## 開発者向け設計メモ（要点）

- jquants_client
  - レート制御: 120 req/min 固定（_RateLimiter）
  - リトライ: 最大 3 回、指数バックオフ、429 の場合は Retry-After を優先
  - 401 の場合はリフレッシュトークンから id_token を再取得して 1 回だけ再試行
  - データ取得時に fetched_at を UTC で記録して look-ahead bias を防止

- news_collector
  - URL 正規化で UTM 等のトラッキングパラメータを除去
  - 記事ID: 正規化 URL の SHA-256 を先頭32文字切り出しで生成（冪等性）
  - SSRF 対策: スキーム検証、リダイレクト先のプライベート IP チェック、受信サイズ上限
  - XML パースは defusedxml を使用

- データ品質チェック（quality）
  - 各チェックはすべての問題を収集して返す（Fail-Fast ではない）
  - SQL はバインドパラメータを使用してインジェクションを避ける

- 監査ログ（audit）
  - order_request_id を冪等キーとして扱い二重発注を防止
  - すべての TIMESTAMP は UTC 保存を想定（init_audit_schema は TimeZone を UTC に設定）

---

## ディレクトリ構成

（主要ファイル／モジュールの抜粋）

```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      schema.py
      quality.py
      audit.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

主要モジュール説明:
- kabusys.config: 環境変数・設定管理（settings）
- kabusys.data.schema: DuckDB スキーマ作成・接続
- kabusys.data.jquants_client: J-Quants API クライアント & DuckDB 保存ユーティリティ
- kabusys.data.news_collector: RSS ニュース収集と DB 保存
- kabusys.data.pipeline: ETL ワークフロー（差分取得・保存・品質チェック）
- kabusys.data.quality: データ品質チェック
- kabusys.data.audit: 監査ログ用スキーマ初期化

---

## 補足・運用上の注意

- 本ライブラリはデータ取得や発注には本番 API / 資格情報を必要とします。運用（live）環境では特に慎重に設定・確認を行ってください。
- KABUSYS_ENV に応じて実行モード（development / paper_trading / live）を切り替えられます。is_live / is_paper / is_dev プロパティで判定可能です。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップや運用時の永続化戦略を検討してください。
- セキュリティ：.env に機密情報を含める際はアクセス制御に留意してください。CI / CD 等ではシークレットマネージャーを使うことを推奨します。

---

必要であれば、README にサンプル .env.example、ユニットテストの実行方法、CI 設定例（GitHub Actions）なども追記できます。どの情報を追加したいか教えてください。