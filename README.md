# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けライブラリです。J-Quants API や RSS を用いて市場データ・財務データ・ニュースを収集・保管し、ETL／品質チェック、マーケットカレンダー管理、監査ログ用スキーマなどの基盤機能を提供します。

主な設計方針は「冪等性」「トレーサビリティ」「セキュリティ（SSRF/XML攻撃対策等）」「API レート制御と堅牢なリトライ」です。

## 主な機能一覧

- J-Quants API クライアント
  - 株価（日足 / OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の遵守（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT を利用）

- RSS ニュース収集（news_collector）
  - RSS から記事を取得し raw_news に保存（記事ID は正規化 URL の SHA-256 ハッシュ先頭32文字）
  - defusedxml による XML 攻撃防御、SSRF 対策（スキーム・ホスト検証、リダイレクト検査）
  - レスポンス最大サイズ制限（デフォルト 10MB）や gzip 解凍後サイズチェック
  - 銘柄コード抽出（4桁の銘柄コード、既知コードセットと突合）

- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日を参照して未取得分のみ取得）
  - backfill による直近再取得で API 側の後出し修正を吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行し QualityIssue を返却

- マーケットカレンダー管理（calendar_management）
  - market_calendar の差分更新ジョブ
  - 営業日判定 / 前後の営業日取得 / 期間内営業日リスト取得（DB 値優先、未登録日は曜日フォールバック）

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス定義と冪等な初期化 API（init_schema / init_audit_schema）

- 監査ログ（audit）
  - signal → order_request → execution の UUID 連鎖によるトレーサビリティ
  - 発注要求の冪等キー（order_request_id）や約定（executions）テーブルを提供

- データ品質チェック（quality）
  - 欠損値検出、前日比スパイク検出、重複チェック、日付不整合チェック
  - 問題は QualityIssue オブジェクトとして返却（severity: error/warning）

## 必要な環境変数

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD      : kabuステーション API 用パスワード（発注周りを使う場合）
  - SLACK_BOT_TOKEN        : Slack 通知に使用するボットトークン
  - SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID

- 任意（デフォルトあり）
  - KABU_API_BASE_URL      : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV            : 環境 ("development", "paper_trading", "live")（デフォルト: development）
  - LOG_LEVEL              : ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化（テスト時に便利）

注意: package の起動時にプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で自動ロードします（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セットアップ手順

1. Python 環境（推奨: 3.9+）を用意します。

2. リポジトリをクローンしてパッケージをインストール（開発モード推奨）:
   ```
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```

3. 必要な依存パッケージ（例）:
   - duckdb
   - defusedxml
   これらは setuptools/pyproject に記載されている想定です。手動インストールする場合:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を用意する（.env をプロジェクトルートに配置）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   .env.example を元に .env を作成してください（リポジトリに例がある前提）。

5. DuckDB スキーマ初期化:
   Python スクリプトや REPL から以下を実行して DB を初期化します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # 監査ログを別 DB に分ける場合:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

## 使い方（簡単な例）

- 日次 ETL の実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- マーケットカレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集と銘柄紐付け
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 事前に取得した有効コード集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.quality import run_all_checks

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- J-Quants の ID トークン取得（テストや直接 API 呼び出しに）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()
  ```

## 注意事項・設計上のポイント

- API レート制御とリトライ
  - J-Quants クライアントは 120 req/min を順守する設計（固定間隔で待機）とリトライ（最大 3 回）を実装しています。
  - 401 が返った場合はリフレッシュトークンを使って自動的に ID トークンを更新し 1 回リトライします。

- 冪等性
  - raw データ保存は ON CONFLICT（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）で重複を排除し、再実行に耐える設計です。

- セキュリティ
  - news_collector は defusedxml を利用して XML 攻撃を防止し、SSRF を防ぐためにスキーム・ホストの検査とリダイレクト時の検証を行います。
  - レスポンスサイズ上限や gzip 解凍後のサイズチェックでメモリ DoS を軽減します。

- テスト容易性
  - 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト時に .env の自動読み込みを抑制）。

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - jquants_client.py             -- J-Quants API クライアント（取得 / 保存）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl など）
    - news_collector.py             -- RSS 収集・保存・銘柄紐付け
    - calendar_management.py        -- マーケットカレンダー管理
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログ（signal/order_request/executions）
  - strategy/
    - __init__.py                   -- 戦略層（将来的な拡張ポイント）
  - execution/
    - __init__.py                   -- 発注実行層（将来的な拡張ポイント）
  - monitoring/
    - __init__.py                   -- 監視・メトリクス（将来的な拡張ポイント）

※ 実行可能な CLI スクリプトはこのコードベースには含まれていません。上記 API を用いてジョブスクリプトやスケジューラ（cron / Airflow 等）から呼び出してください。

---

問題報告・改善提案や README に追加してほしい項目があれば教えてください。README をプロジェクトの実行例（systemd / Docker / GitHub Actions の設定など）に合わせて拡張することもできます。