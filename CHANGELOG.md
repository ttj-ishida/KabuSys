CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（現在のリリースに対する未リリースの変更はありません）

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = 0.1.0）。
- パッケージ公開インターフェースを定義（src/kabusys/__init__.py）。モジュール群: data, strategy, execution, monitoring をエクスポート。
- 環境変数／設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。プロジェクトルート判定には .git または pyproject.toml を使用するため、CWD に依存しない設計。
  - 自動ロードを無効にするためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env。既存の OS 環境変数は protected として上書きされない。
  - 高度な .env パーサーを実装:
    - 空行・コメント行（先頭 #）を無視。
    - "export KEY=val" 形式をサポート。
    - シングル/ダブルクォートで囲まれた値を正しく扱い、バックスラッシュによるエスケープを処理。
    - クォート無しの場合、インラインコメントの扱いを文脈（直前がスペース/タブか）により適切に判定。
  - 必須環境変数取得ヘルパー _require() を提供。未設定時は ValueError を送出。
  - Settings クラスを公開（settings インスタンス）:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベース: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - 環境モード判定プロパティ: is_live, is_paper, is_dev
- DuckDB スキーマ定義／初期化モジュールを追加（src/kabusys/data/schema.py）。
  - データレイヤーを想定した 3+1 層スキーマ定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型チェック（DECIMAL、BIGINT、BOOLEAN 等）および CHECK 制約や PRIMARY/FOREIGN KEY を設定。
  - 頻出クエリに備えたインデックスを定義（例: prices_daily(code, date), features(code, date), signal_queue(status) など）。
  - スキーマ作成は冪等（CREATE TABLE IF NOT EXISTS）で実装。
  - init_schema(db_path) を提供:
    - 指定した DuckDB ファイルの親ディレクトリが存在しない場合は自動作成。
    - 全テーブルとインデックスを作成し、初期化済みの duckdb 接続を返す。
    - ":memory:" を指定してインメモリ DB を使用可能。
  - get_connection(db_path) を提供: 既存 DB への接続を返す（スキーマ初期化は行わない）。
- パッケージ構造の雛形ファイルを追加:
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
  - これらは将来的な機能拡張のための名前空間を確保。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Security
- 環境変数の自動ロード時、既に存在する OS 環境変数を protected として上書きしない仕様により、誤ってローカル .env によって重要な OS 環境設定が上書きされるリスクを低減。

Notes / 備考
- Settings の必須値が不足している場合は起動時に早期にエラーを出す設計で、運用時のミス検出を容易にしています。
- DuckDB スキーマは外部キー依存順に作成されるため、初回のスキーマ初期化で参照整合性が確保されます。
- 今後のリリースでは各サブパッケージ（data/strategy/execution/monitoring）に具体的なデータ取り込み・特徴量算出・戦略ロジック・発注連携・監視機能を追加予定です。