# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべてのリリースはセマンティックバージョニングに基づきます。

## [0.1.0] - 2026-03-15

初回公開リリース。日本株の自動売買システム「KabuSys」の基盤となるパッケージ構成・設定管理・DuckDBスキーマを実装しました。

### 追加
- パッケージ基盤
  - パッケージルート `kabusys` を追加。__version__ を "0.1.0" に設定し、公開モジュールとして data, strategy, execution, monitoring を __all__ に定義。
  - strategy、execution、monitoring のモジュール名で空のパッケージを用意（今後の拡張箇所）。

- 環境変数・設定管理 (`kabusys.config`)
  - .env ファイルや環境変数から設定を読み出す自動ロード機能を実装。
    - プロジェクトルートは __file__ 位置から親ディレクトリを遡って `.git` または `pyproject.toml` を基準に検出（CWDに依存しない実装）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート（テスト用途など）。
    - OS側の既存環境変数は保護され、`.env.local` の上書きから除外される仕組みを実装。
  - .env パーサを実装（細かい挙動を考慮）
    - 空行・コメント行（# で始まる）を無視。
    - `export KEY=val` 形式に対応。
    - シングルクォート／ダブルクォートで囲まれた値をサポートし、バックスラッシュによるエスケープ処理を考慮して正しく解析。
    - クォート無し値のインラインコメント扱いは、`#` の直前がスペース／タブの場合のみコメントとみなすなど現実的なルールを採用。
  - Settings クラスを実装し、アプリの主要設定をプロパティ経由で取得可能にした。
    - J-Quants、kabuステーション API、Slack、データベースパス（DuckDB / SQLite）、およびシステム設定（環境種別、ログレベル判定）を含むプロパティを提供。
    - 必須環境変数が未設定の場合は `_require()` により ValueError を送出して明示的に失敗する仕様。
    - KABUSYS_ENV の値検証（development / paper_trading / live のみ許可）。
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可）。
    - 利便性プロパティ: is_live, is_paper, is_dev。

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - Data Lake / ETL を考慮した 3 層＋実行層のスキーマを実装（DDL を定義）。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型制約（NOT NULL / CHECK / PRIMARY KEY）を設定。
  - 外部キー制約を設定（例: news_symbols → news_articles ON DELETE CASCADE、orders.signal_id → signal_queue ON DELETE SET NULL、trades.order_id → orders ON DELETE CASCADE）。
  - 頻出クエリに対応するインデックスを複数定義（銘柄×日付検索、ステータス検索、orders.signal_id 等）。
  - 公開関数:
    - init_schema(db_path): DuckDB データベースを初期化し、すべてのテーブルとインデックスを作成。冪等に実行可能。db_path の親ディレクトリが存在しない場合は自動作成。":memory:" によるインメモリ DB をサポート。
    - get_connection(db_path): 既存の DuckDB 接続を返す（スキーマ初期化は実行しない。初回は init_schema を使用）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の注意点 / マイグレーション
- Settings の必須プロパティを参照すると ValueError が発生するため、ライブラリを利用する前に必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後や特定の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化して手動で環境設定を行うことを推奨します。
- DuckDB スキーマは現状のDDLを前提としているため、後続リリースでスキーマ変更がある場合は適切なマイグレーションを用意します（現状は初期作成のみ）。

### セキュリティ
- 環境変数の上書きポリシーにより、OS環境変数はデフォルトで保護されます。`.env`/`.env.local` に秘密情報を置く際は適切なファイル保護を行ってください。

今後の予定:
- strategy / execution / monitoring の具体実装（戦略算出・発注ロジック・監視機能）を追加予定。  
- スキーマのバージョン管理およびマイグレーション機能の追加検討。