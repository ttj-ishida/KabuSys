# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-15

初回公開リリース — 日本株自動売買システムの骨組みと基盤機能を追加。

### 追加
- パッケージ初期化
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。
  - バージョン: `0.1.0`
  - パブリックモジュール一覧: `data`, `strategy`, `execution`, `monitoring`

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト等用）。
    - OS の既存環境変数を保護するための protected キーセットを使用し、`.env.local` は上書き可能だが protected キーは上書きしない。
  - .env パーサを実装:
    - 空行・コメント行（先頭 `#`）を無視。
    - `export KEY=val` 形式に対応。
    - 値にクォート（シングル／ダブル）を含む場合のエスケープシーケンスに対応し、対応する閉じクォートまで正しくパース（インラインコメントは無視）。
    - クォートなしの場合、`#` がスペースまたはタブの直前にある場合のみ以降をコメントとして扱う。
    - 無効行はスキップ。
  - エラーハンドリング:
    - .env ファイルの読み込みに失敗した場合は警告を発行して続行。
  - Settings で取得する主な設定項目:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
    - kabuステーション API: `KABU_API_PASSWORD`（必須）、`KABU_API_BASE_URL`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `SLACK_BOT_TOKEN`、`SLACK_CHANNEL_ID`（共に必須）
    - DB パス: `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）、`SQLITE_PATH`（デフォルト: `data/monitoring.db`）
    - システム設定: `KABUSYS_ENV`（`development`, `paper_trading`, `live` のいずれか。デフォルト: `development`）、`LOG_LEVEL`（`DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`。デフォルト: `INFO`）
  - 便宜プロパティ:
    - `is_live`, `is_paper`, `is_dev`（環境判定）

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md に準拠した三層（Raw / Processed / Feature）+ Execution レイヤーのテーブル定義を追加。
  - Raw Layer（生データ）テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer テーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer テーブル:
    - features, ai_scores
  - Execution Layer テーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、CHECK 制約、PRIMARY / FOREIGN KEY を設定（外部キーの ON DELETE 挙動も指定）。
  - 検索パターンに基づくインデックスを複数定義（銘柄×日付検索、ステータス検索、orders/trades 関連など）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスで DuckDB データベースを初期化し、全テーブルとインデックスを作成。既存テーブルはスキップ（冪等）。
      - db_path がファイル指定の場合、親ディレクトリを自動作成。
      - `":memory:"` を指定するとインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を取得（スキーマ初期化は行わない。初回は init_schema を使用すること）。

- パッケージ構成
  - プレースホルダとして以下モジュールを追加（空の __init__.py を配置）:
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

### 変更
- 初回リリースのため既存コードからの変更はなし（初期追加のみ）。

### 修正
- .env パースとロード処理での頑健性を向上（エスケープ、コメント規則、保護キー、ロード順序等の設計を反映）。

### 既知の注意点 / マイグレーション
- 初めてデータベースを使う場合は必ず init_schema() を呼んでスキーマを作成してください。例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 自動環境変数読み込みをテストで抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings の必須環境変数が未設定の場合は ValueError を送出します。実行前に .env または OS 環境に必要値を設定してください。
- DuckDB を使用するため、実行環境に duckdb パッケージが必要です。

### セキュリティ
- .env 上書きの際、OS 環境変数を保護する仕組みを導入（.env の上書き時に既存 OS 環境変数を除外または protected として扱う）。

---

今後のリリースでは、strategy / execution / monitoring の実装、AI スコア算出パイプライン、発注処理の具現化、モニタリング UI などを追加していく予定です。