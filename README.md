# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants や RSS などからデータを取得して DuckDB に保存し、ETL・品質チェック・監査ログなどを提供します。

このリポジトリはライブラリ形態で、戦略（strategy）・発注（execution）・監視（monitoring）レイヤを統合するためのデータ基盤（data）と設定（config）を中心に実装されています。

---

## 主な特徴（機能一覧）

- 環境設定
  - .env ファイルまたは環境変数から設定を自動読み込み（.git または pyproject.toml をプロジェクトルート判定）
  - 必須変数の取得に Settings クラスを提供
  - 自動ロードを無効にするフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）と固定間隔スロットリング
  - リトライ（指数バックオフ、408/429/5xx、最大 3 回）
  - 401 時にトークン自動リフレッシュ（1 回）
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集、テキスト前処理、トラッキングパラメータ除去
  - SSRF・XML Bomb 対策（defusedxml、リダイレクト/ホスト検証、受信サイズ制限）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - DuckDB への冪等保存（INSERT ... RETURNING）と銘柄紐付け

- データスキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化
  - インデックス定義、外部キーを考慮した作成順序

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日に基づく差分）、バックフィル、保存、品質チェック
  - 日次 ETL エントリ (`run_daily_etl`) と個別ジョブ（価格・財務・カレンダー）

- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの差分更新バッチ、営業日判定ユーティリティ（next/prev/get/is_sq_day）

- 品質チェック（kabusys.data.quality）
  - 欠損、重複、日付不整合、前日比スパイク検出
  - QualityIssue オブジェクト列挙と集約実行 (`run_all_checks`)

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定に至るトレース用テーブル群の初期化
  - UUID ベースの冪等・監査設計、UTC タイムスタンプ固定

- プレースホルダ
  - strategy/, execution/, monitoring/ のパッケージは用意されています（具体実装は各自拡張）。

---

## システム要件

- Python 3.10 以上（PEP 604 の型注釈 `X | Y` を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じて pyproject.toml / requirements.txt を追加して下さい。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - 例（UNIX 系）:
     ```bash
     git clone <repo-url>
     cd <repo-dir>
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 必要なパッケージをインストールします。
   ```bash
   pip install duckdb defusedxml
   # 開発用にパッケージとして使う場合:
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 例 .env（最低限の例）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here

     # kabuステーション API
     KABU_API_PASSWORD=your_kabu_password
     # 省略可（デフォルト http://localhost:18080/kabusapi）
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack（通知用）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789

     # DBパス（任意）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行環境
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python から初期化できます（`DUCKDB_PATH` を明示しても良い）:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（簡易サンプル）

- Settings の取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  print(settings.env, settings.log_level)
  ```

- DuckDB スキーマ作成（既存ならスキップ）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")

  # 既知銘柄コードセットを与えると記事に含まれる銘柄を紐付ける
  known_codes = {"7203", "6758", "9984"}
  result = run_news_collection(conn, known_codes=known_codes)
  print(result)  # ソースごとの新規保存件数
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックを手動実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

- 監査スキーマの初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

---

## 注意点 / 実装上のポイント

- 自動環境変数読み込み
  - `kabusys.config` はプロジェクトルートを基準に `.env` / `.env.local` を自動的に読み込みます。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API
  - トークン自動更新、ページネーション対応、レート制御、リトライ制御が組み込まれています。大量リクエスト時はレート制限に注意してください。
- ニュース収集のセキュリティ
  - RSS 取得時に SSRF 対策（スキーム/ホスト検証、リダイレクト検査）、XML の安全パーシング（defusedxml）、レスポンスサイズ制限を実装しています。
- DuckDB の使用
  - スキーマは冪等に作成されます。既存 DB に対しては `get_connection` を用いて接続できます。
- 空のパッケージ
  - strategy/, execution/, monitoring/ は雛形のみ（拡張対象）です。各プロジェクトで実戦用の戦略ロジック・発注ラッパー等を実装してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py

プロジェクトルートには通常 .git / pyproject.toml（パッケージ管理）や `.env` が配置されます。

---

## 今後の拡張案（参考）

- strategy 層に複数の戦略実装（バージョン管理）
- execution 層に証券会社ごとのブローカーアダプター（kabuステーション・API 統合）
- モニタリング（Slack 通知、Prometheus メトリクス）
- CI での品質チェック自動化（ETL 結果 / quality レポート）

---

質問や README に追記してほしい項目があれば教えてください（例: 実行例の追加、CI 設定、Docker 実行例など）。