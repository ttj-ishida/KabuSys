# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETLパイプライン、データ品質チェック、ニュース収集、DuckDBスキーマ管理、監査ログなどを提供し、戦略・発注層と連携して自動売買システムを構築するための基盤を含みます。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX カレンダーを取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - フェッチ時刻（fetched_at）を記録して Look-ahead Bias を防止
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス、外部キー、制約を含む冪等な初期化
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、バックフィル対応）
  - 市場カレンダー先読み、品質チェック統合
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合を検出
  - 問題は QualityIssue オブジェクトで返却（error/warning）
- ニュース収集（RSS）
  - RSS 取得、URL 正規化（utm 等除去）、記事 ID を SHA-256 で生成し冪等保存
  - SSRF / XML Bomb / gzip ファイルサイズ制限などセキュリティ対策
  - 記事と銘柄コードの紐付け機能
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティ用テーブル群
  - UUID とタイムスタンプにより完全な監査証跡を保持

---

## 要求環境 / 依存

- Python 3.10 以上（型ヒントに | を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）を多用

プロジェクトに requirements.txt / pyproject.toml がある想定です。存在しない場合は上記パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - もし pyproject.toml / requirements.txt があればそれを使ってください。なければ最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発時にパッケージとして編集可能にインストールする場合:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID: 通知先チャネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 実行環境 (development / paper_trading / live)（デフォルト: development）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   - 例 `.env`（簡易）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=secret_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

5. データベース初期化
   - DuckDB スキーマを作成:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
     ```
   - 監査ログ専用 DB を作成する場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```
   - または既存接続に監査テーブルだけ追記:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 使い方（主要ユースケース）

- 設定値取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- J-Quants の ID トークン取得（明示的）
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェックを含む）
  ```python
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別 ETL 実行例（株価のみ）
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集（RSS）と銘柄紐付け
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  ```

- データ品質チェックを単独で実行
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data import calendar_management as cm, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  cm.calendar_update_job(conn)
  is_trading = cm.is_trading_day(conn, date.today())
  next_day = cm.next_trading_day(conn, date.today())
  ```

注意:
- ETL / API 呼び出しはネットワークと API レート制限の影響を受けます。
- テスト時に自動 .env ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py        # RSS ニュース収集・前処理・DB 保存
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py   # 市場カレンダー関連（営業日判定、更新ジョブ）
    - audit.py                 # 監査ログ（signal / order_request / executions）
    - quality.py               # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

README に記載の無い実装部分（戦略層、実行層、監視層）は拡張ポイントとして設計されています。

---

## 運用上の注意 / ベストプラクティス

- 環境分離: 本番（live）とペーパートレード（paper_trading）、開発（development）を `KABUSYS_ENV` で区別して運用してください。
- シークレット管理: .env はリポジトリにコミットしないでください。`.env.example` を参照用に置き、実際の値はセキュアに管理してください。
- DuckDB ファイルは定期バックアップを推奨します。
- J-Quants の API レートや利用規約を遵守してください。
- ニュース収集や外部 URL 取得時は SSRF・XML 攻撃対策が組み込まれていますが、運用環境でも監視を行ってください。
- ETL 実行はロギングを有効にして、障害時に原因を解析できるようにしてください。

---

## 貢献・拡張

- 戦略（strategy）モジュール、発注・実行（execution）モジュール、監視（monitoring）周りはプラグイン的に拡張可能です。Pull Request や Issue にて提案ください。
- 新しいデータソース（RSS や API）を追加する場合は、news_collector の設計原則（正規化・冪等性・セキュリティ）に従って実装してください。

---

必要であれば、セットアップ用スクリプト例や pyproject.toml / requirements.txt のテンプレート、簡易デプロイ手順（systemd / cron / container）も用意できます。どの情報がさらに欲しいか教えてください。