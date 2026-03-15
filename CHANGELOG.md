# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このリポジトリの初期リリース情報はコードベースの内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース（推定）。パッケージメタ情報・環境設定・DuckDB スキーマ・監査ログなどの基盤機能を追加。

### 追加 (Added)
- パッケージ基本情報
  - src/kabusys/__init__.py にパッケージ説明とバージョン `0.1.0`、公開モジュールリスト（data, strategy, execution, monitoring）を追加。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの検出: __file__ から親ディレクトリを辿り `.git` または `pyproject.toml` を基準にルートを特定（CWD 非依存）。
    - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト向け）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`.env.local` は上書き（override=True）。
    - .env パースの強化:
      - `export KEY=val` 形式に対応。
      - シングル/ダブルクォート内でのバックスラッシュエスケープを考慮したパース。
      - クォートなし値のインラインコメント扱いは直前が空白/タブの場合のみ認識。
    - ファイル読み込みエラー時は警告を出力して読み込みをスキップ。
    - protected set を用いて OS 環境変数を上書きから保護。
  - Settings クラスによる型付き・検証付き設定アクセスを提供:
    - 必須設定取得時に未設定なら例外を送出する `_require()` を利用。
    - J-Quants / kabuステーション / Slack / データベースパス等のプロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - duckdb/sqlite のデフォルトパス（`data/kabusys.duckdb`, `data/monitoring.db`）を提供し Path 型で返す。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性検証（許容値: development / paper_trading / live、DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパープロパティ。

- データベーススキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマを層構造（Raw / Processed / Feature / Execution）で定義。
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions（取得した生データを保持）。
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（整形済みデータ）。
    - Feature layer: features, ai_scores（戦略/AI用特徴量・スコア）。
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（シグナル・注文・約定・ポジション管理）。
  - 列に対する型/制約（CHECK, PRIMARY KEY, FOREIGN KEY）を豊富に設定してデータ整合性を担保。
  - パフォーマンス改善のためのインデックスを複数定義（銘柄×日付検索、ステータス検索、外部キー結合パターン等）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定 DB ファイルを作成（親ディレクトリ自動作成）し、全テーブル・インデックスを冪等的に作成して接続を返す。
      - ":memory:" によるインメモリ DB をサポート。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存の DuckDB へ接続を返す（スキーマ初期化は行わない。初回には init_schema を推奨）。

- 監査ログ（トレーサビリティ）機能 (src/kabusys/data/audit.py)
  - シグナルから約定までのフローを UUID 連鎖でトレースする監査テーブルを追加。
    - テーブル: signal_events, order_requests, executions
    - 設計上の特徴:
      - order_request_id を冪等キーとして二重発注防止。
      - すべてのテーブルに created_at / updated_at（必要に応じてアプリ側で更新）を持たせ監査証跡を保証。
      - 監査ログは削除しない前提で FOREIGN KEY は ON DELETE RESTRICT を採用。
      - すべての TIMESTAMP は UTC で保存（init_audit_schema は `SET TimeZone='UTC'` を実行）。
      - order_requests に対する状態遷移（例: pending → sent → filled / partially_filled / cancelled / rejected / error）を想定。
      - order_requests では order_type ごとの価格必須チェック（limit/stop/market の整合性）を実装。
  - インデックスを複数定義（シグナルの日付・銘柄検索、status によるキュー走査、broker_order_id / broker_execution_id による紐付けなど）。
  - 公開 API:
    - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
      - 既存接続に監査用テーブル・インデックスを冪等的に追加。UTC 時刻保存を設定。
    - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 監査用 DB ファイルを作成（親ディレクトリ自動作成）、監査スキーマを初期化して接続を返す。

- モジュールプレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（パッケージ構造の準備）。

### 変更 (Changed)
- なし（初回リリースに相当するため）。

### 修正 (Fixed)
- なし（初回リリースに相当するため）。

### 注意事項 / 移行メモ
- 初回リリース想定のため、運用前に以下を確認してください:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定すること。Settings の各プロパティは未設定時に ValueError を投げます。
  - 開発・検証時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動 .env 読み込みを無効化できます。
  - DuckDB の初期化は data.schema.init_schema() を使用してください。監査ログを別 DB に保持する場合は data.audit.init_audit_db() を使用できます。既存 DB に監査テーブルを追加する場合は init_audit_schema(conn) を呼び出してください。
  - 監査テーブルは削除されない前提の設計です。テーブル・インデックス追加は冪等です。

---

この CHANGELOG はコードベースのコメント・実装から推測して作成しています。必要に応じてリリース日・追加情報を更新してください。