# KabuSys

日本株自動売買システムのコアライブラリ群（データ取得・ETL・スキーマ・監査・品質チェックなど）。

このリポジトリは、J-Quants / kabuステーション 等の外部サービスから市場データを取得し、DuckDB に保存・整形して戦略・実行に渡すための基盤機能を提供します。設計はデータのトレーサビリティ（監査）とデータ品質、冪等性（Idempotency）を重視しています。

---

## 主要な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）に準拠する固定間隔スロットリング
  - 再試行（指数バックオフ、最大 3 回）、401 受信時のトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を防止

- データスキーマ（DuckDB）
  - 3〜4 層のレイヤ構成（Raw / Processed / Feature / Execution）を定義
  - ON CONFLICT DO UPDATE により冪等な保存をサポート
  - 主要クエリに対するインデックスを定義

- ETL パイプライン
  - 差分更新（最後に取得した日付から不足分を取得）
  - backfill による後出し修正の吸収
  - 市場カレンダーの先読み（デフォルト: 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行可能

- データ品質チェック
  - 欠損（OHLC 欄）、重複、スパイク（前日比閾値）、日付整合性を検出
  - 問題は QualityIssue オブジェクトで集約（severity により呼び出し側で処理決定）

- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 のフローを UUID で連鎖して追跡
  - 発注の冪等キー（order_request_id）やステータス管理を設計

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（必要に応じて無効化可能）
  - 必須環境変数チェックと型整合性（env, log level）

---

## セットアップ手順

前提:
- Python 3.10 以上（コード内で `X | Y` 型ヒントを使用）
- Git が利用可能

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   Linux/macOS:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   本リポジトリで使用される主要な外部依存は duckdb です。pip でインストールします。
   ```
   pip install duckdb
   ```
   （他に必要なパッケージがある場合はプロジェクトの requirements.txt / pyproject.toml を参照してください。）

4. 環境変数設定
   プロジェクトルートに `.env`（や `.env.local`）を置くと自動で読み込まれます。
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 bot token
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   オプション（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）

   例 `.env`（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

---

## 使い方

以下は基本的な利用方法の抜粋です。各モジュールはライブラリとしてインポートして利用します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 監査ログ（audit）スキーマの初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)
  ```

- J-Quants のトークン取得（手動）
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 日次 ETL を実行（差分取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # 戻り値は ETLResult
  print(result.to_dict())
  ```

- 個別 ETL ジョブの実行
  - 株価差分 ETL:
    ```python
    from kabusys.data.pipeline import run_prices_etl
    from datetime import date

    fetched, saved = run_prices_etl(conn, target_date=date.today())
    ```
  - 財務データ ETL:
    ```python
    from kabusys.data.pipeline import run_financials_etl
    fetched, saved = run_financials_etl(conn, target_date=date.today())
    ```
  - カレンダー ETL:
    ```python
    from kabusys.data.pipeline import run_calendar_etl
    fetched, saved = run_calendar_etl(conn, target_date=date.today())
    ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 自動環境ロードの制御
  - デフォルトでは package import 時にプロジェクトルートの `.env` / `.env.local` を読み込みます（`.git` または `pyproject.toml` を起点に探索）。
  - テストなどで無効化するには環境変数を設定:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## API / 設計上の注意点

- Python バージョン: 3.10 以上（`X | Y` 型ヒントを使用）
- J-Quants クライアント:
  - レートリミットを内部で管理（120 req/min）
  - 再試行（最大 3 回）、429 の場合は Retry-After を優先
  - 401 の場合は設定済みリフレッシュトークンから ID トークンを再取得して 1 回だけ再試行
  - ID トークンはモジュールレベルでキャッシュされ、ページネーション間で共有
- DuckDB スキーマ:
  - 初期化は `init_schema()` を使うこと（冪等的にテーブル・インデックスを作成）
  - 監査テーブルは `init_audit_schema()`（既存接続へ追加）
- ETL:
  - 各ステップは独立して例外を捕捉し、1 ステップ失敗でも他を続行する設計
  - 品質チェックで検出された問題はすべて収集され、呼び出し側が重大度に応じて停止/通知を決定

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数）
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, 個別ジョブ）
    - quality.py
      - データ品質チェック（QualityIssue, run_all_checks 等）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）と初期化
    - pipeline.py / audit.py / quality.py：ETL と監査・品質に関連するロジック
  - strategy/
    - __init__.py（戦略のための名前空間）
  - execution/
    - __init__.py（発注実行のための名前空間）
  - monitoring/
    - __init__.py（監視・モニタリング関連の名前空間）
- README.md（本ドキュメント）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - パッケージ（config.py）は import 時にプロジェクトルートを .git / pyproject.toml から探索して `.env` を読み込みます。プロジェクトルートの位置が正しいか、ファイル名が正しいか確認してください。
  - 自動ロードを無効化している場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認してください。

- DuckDB への接続／ファイルが作成されない
  - `init_schema(settings.duckdb_path)` を呼んだときに親ディレクトリが自動で作成されますが、パスに権限がない等の問題がないか確認してください。

- J-Quants API が 401 を返す
  - `JQUANTS_REFRESH_TOKEN` が無効、または期限切れの可能性があります。`get_id_token()` を呼んで正しいトークンが取得できるか確認してください。

---

以上が README の概要です。必要であれば以下も作成できます：
- .env.example の具体例
- サンプルスクリプト（CLI 形式で ETL を定期実行する runner）
- 開発向けのテスト手順 / CI 設定例

追加で欲しいセクションがあれば教えてください。