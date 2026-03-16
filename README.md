# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からマーケットデータと財務データを取得して DuckDB に保存し、ETL（差分取得・バックフィル）、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などの基盤機能を提供します。

主な利用想定:
- データ収集（株価、財務、マーケットカレンダー）
- DuckDB によるスキーマ管理（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（signal → order_request → executions のトレース）
- (将来的に) 戦略層・発注連携（kabu API など）

---

## 機能一覧

- 環境変数・.env 自動読み込み（プロジェクトルートの `.env`, `.env.local` を自動読み込み、CWD 非依存）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務四半期データ取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レート制限（120 req/min）に基づくスロットリング
  - 冪等的保存（DuckDB への INSERT ... ON CONFLICT DO UPDATE）
  - リトライ（指数バックオフ、対象: 408/429/5xx）と 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias のトレース）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義・外部キー考慮のテーブル作成順を提供
  - 監査ログ用テーブル（signal_events / order_requests / executions）の初期化
- ETL パイプライン
  - 差分取得（DB の最終取得日を基に自動算出）
  - backfill_days による過去再取得で API の後出し修正を吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括処理（個別ジョブも呼べる）
  - ETL 結果を ETLResult オブジェクトで返却（詳細な結果・問題リスト・エラー一覧）
- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値、デフォルト 50%）
  - 主キー重複チェック
  - 日付整合性チェック（未来日付・非営業日のデータ）
  - 全チェックをまとめて実行して問題を一覧で返す
- 監査ログ（Audit）
  - UUID ベースで signal → order_request → execution を追跡可能
  - 発注の冪等キー（order_request_id）サポート
  - UTC タイムスタンプ保存、削除禁止前提の設計

---

## セットアップ手順

前提: Python がインストールされていること（推奨: 3.9+ 等）。DuckDB を使用します。

1. リポジトリをクローン / 配置
2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要な依存パッケージをインストール
   - 本コードベースは duckdb を使用します。セットアップ方法の例:
     ```
     pip install duckdb
     # 開発時: pip install -e .
     ```
   - 実運用では HTTP クライアント等の追加依存がある可能性があります。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を作成すると、自動で読み込まれます（自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット）。
   - 必須の環境変数（コード内 Settings 参照）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabu ステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）
   - オプション:
     - KABUSYS_ENV            — 環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — SQLite（監視用）パス（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python REPL / スクリプトでの基本的な例です。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB スキーマを初期化して接続を取得
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は Path オブジェクトを返す
  conn = init_schema(settings.duckdb_path)
  ```

  メモ: テストや一時実行ではインメモリ DB を使えます:
  ```python
  conn = init_schema(":memory:")
  ```

- 監査ログテーブルを初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```
  または専用 DB を作成する場合:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants クライアントを直接使ってデータを取得・保存
  ```python
  from kabusys.data import jquants_client as jq
  # トークンは settings.jquants_refresh_token を使って自動取得される
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched={len(records)} saved={saved}")
  ```

- 日次 ETL の実行（推奨）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
  print(result.to_dict())
  ```

  run_daily_etl は以下を順に実行します:
  1. 市場カレンダー ETL（先読み）
  2. 株価日足 ETL（差分 + backfill）
  3. 財務データ ETL（差分 + backfill）
  4. 品質チェック（オプションで無効化可能）

  返り値 ETLResult には各フェーズの取得件数・保存件数、品質問題リスト、エラー一覧が含まれます。

- 品質チェックだけを実行する
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- テスト用に id_token を注入して API 呼び出しを制御可能
  ```python
  token = jq.get_id_token("your_refresh_token")
  records = jq.fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  ```

---

## 実装上の主要ポイント（開発者向けメモ）

- 環境ロード
  - 自動読み込みは .git または pyproject.toml を探索してプロジェクトルートを特定し、その下の `.env` / `.env.local` を読み込みます。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- J-Quants クライアント
  - レート制限: 120 req/min（モジュール内 _RateLimiter が固定間隔スロットリング）
  - リトライ: 最大 3 回、指数バックオフ（base=2s）、対象は 408/429/5xx。429 は Retry-After を尊重。
  - 401 受信時: トークンを自動リフレッシュして 1 回だけリトライ（allow_refresh=False で無効化）
  - ページネーション: pagination_key を用いたループで全件取得
  - 保存時は fetched_at を UTC ISO8601（Z）で記録し、INSERT ... ON CONFLICT DO UPDATE で冪等性を確保

- ETL
  - 差分更新のデフォルト単位は営業日 1 日。未取得範囲は DB の最終取得日から自動計算。
  - backfill_days（デフォルト 3）で数日前から再取得して API の後出し修正を吸収。
  - run_daily_etl は各ステップで例外を捕捉し、可能な限り処理を継続して結果を返す（Fail-Fast ではない）。

- 品質チェック
  - 各チェックは QualityIssue オブジェクトのリストを返却。重大度（severity）は "error" / "warning"。
  - スパイク閾値はデフォルト 50%（変更可能）。

---

## ディレクトリ構成（サンプル）

本 README が対象とするコードベースの主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（fetch/save）
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（run_daily_etl 等）
      - quality.py             # データ品質チェック
      - audit.py               # 監査ログ（signal / order_request / executions）
      - pipeline.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のリポジトリには README / LICENSE / pyproject.toml 等が含まれる想定です）

---

## テスト・開発時のヒント

- 環境の自動読み込みを無効化してユニットテストを実行したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB をインメモリでテストすると高速で副作用も残りません:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- jquants_client の ID トークンや fetch の戻り値をモック／注入してユニットテストを行う設計になっています（id_token を引数で渡せる）。

---

必要に応じて README を拡張して、インストール要件（Python バージョンや依存パッケージ）、CI 設定、実運用での注意点（API の利用制限、鍵の管理、監査ログの運用ルールなど）を追記してください。