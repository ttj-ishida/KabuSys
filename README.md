# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買基盤のためのライブラリ群です。J-Quants 等の外部データソースから市場データを取得し、DuckDB に蓄積、ETL／品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注〜約定のトレース）など、運用に必要な基盤機能を提供します。

主な設計方針:
- 冪等性（ON CONFLICT / INSERT RETURNING）を重視
- APIレート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead Bias 対策（fetched_at を UTC で記録）
- セキュリティ対策（RSS の SSRF 防止・defusedxml 利用・レスポンスサイズ制限）

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git/.pyproject.toml で判定）
  - 必須環境変数チェック（settings オブジェクト）
  - 無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - 固定間隔レートリミッタ（120 req/min）
  - リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存用ユーティリティ（save_*）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理（URL 除去／空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検証）
  - gzip / サイズ上限（10MB）対応
  - DuckDB への冪等保存（INSERT ... RETURNING）／銘柄抽出・紐付け

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、初期化用 init_schema()/get_connection()

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): カレンダー取得 → 株価差分取得（バックフィル対応） → 財務差分取得 → 品質チェック
  - 差分更新（最終取得日を参照）、backfill_days による後出し修正の吸収
  - 品質チェック連携（quality モジュール）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job(): 夜間バッチで JPX カレンダー差分更新

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出（前日比）、重複チェック、日付不整合チェック
  - QualityIssue オブジェクトで詳細を返す（severity: error/warning）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルにより発注から約定までを UUID 連鎖でトレース
  - init_audit_schema / init_audit_db

## セットアップ手順

※ 以下は一般的な手順です。プロジェクト独自の packaging/requirements ファイルがある場合はそちらを参照してください。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. Python 環境（推奨）
   - 本ライブラリは Python 3.10+ を想定しています（PEP 604 の型記法 | を使用）。
   - 仮想環境作成例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

3. 依存ライブラリをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - defusedxml
   - pip でインストール:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - その他:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - KABU_API_BASE_URL (kabu API ベースURL, デフォルト http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=passwd
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用 DB を別ファイルで分けたい場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

## 使い方（主要な API / 実行例）

- ETL（日次一括）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- J-Quants から日足取得（テスト／デバッグ用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(quotes))
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for it in issues:
      print(it.check_name, it.severity, it.detail)
  ```

- マーケットカレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  print(is_trading_day(conn, date(2026,1,1)))
  print(next_trading_day(conn, date(2026,1,1)))
  ```

注意:
- network / credential 関連は実運用前に十分にテストしてください。
- J-Quants のレート制限や API 仕様変更に注意してください。

## ディレクトリ構成

（主要ファイル／モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（取得/保存）
      - news_collector.py           # RSS ニュース収集器（SSRF 対策等）
      - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py      # マーケットカレンダー管理
      - schema.py                   # DuckDB スキーマ定義・初期化
      - audit.py                    # 監査ログ（発注〜約定のトレーサビリティ）
      - quality.py                  # データ品質チェック
    - strategy/
      - __init__.py                 # 戦略層（実装場所）
    - execution/
      - __init__.py                 # 発注／実行層（実装場所）
    - monitoring/
      - __init__.py                 # 監視／メトリクス（実装場所）

その他:
- .env / .env.local                 # (任意) 環境変数ファイル（プロジェクトルートに配置）
- pyproject.toml / setup.cfg 等     # パッケージ設定（存在する場合）

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動読み込みを無効化)

## トラブルシューティング / 注意事項

- Python バージョン: 3.10 以上が必要です（型アノテーションの構文を使用）。
- DuckDB ファイルの書き込み権限を確認してください（親ディレクトリ自動作成は行いますが権限は必要です）。
- RSS フィード側のサイズや gzip の不正に対しては保護がありますが、大量フィード収集時はレートやネットワークの制約に注意してください。
- J-Quants の API トークンは有効期限や権限に注意してください。get_id_token はリフレッシュトークンから idToken を取得します（config.settings.jquants_refresh_token を使用）。
- 本リポジトリに含まれない実装（strategy / execution / monitoring）の詳細は別途実装／拡張が必要です。

---

ご要望があれば以下の追加を作成します:
- requirements.txt / pyproject.toml の推奨設定例
- より詳しい運用ガイド（スケジューリング例、バックテスト連携、Slack 通知例）
- テスト実行例（ユニットテスト／モックの説明）