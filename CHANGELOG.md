# CHANGELOG

すべての重要な変更を記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

テンプレート:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

## [0.1.0] - 2026-03-15
初期リリース。日本株自動売買（KabuSys）ライブラリの基盤的な実装を追加。

### Added
- パッケージのメタ情報を追加
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" とパブリック API (__all__) を定義。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定値を読み込む自動ロード機構を実装。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を基準）。これによりカレントワーキングディレクトリに依存しない動作を実現。
  - .env ファイルの柔軟なパーサを実装:
    - コメント行（#）と空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートで囲まれた値のエスケープ処理に対応（バックスラッシュエスケープを考慮）。
    - 非クォート値でのインラインコメント処理（直前が空白/タブの場合に # をコメントと認識）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。OS 環境変数を保護するための protected キーセットを導入。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - 必須環境変数未設定時に ValueError を送出する _require 関数を実装し、Settings クラスで使用。
  - Settings クラスを実装し、主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack 関連: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: duckdb（デフォルト data/kabusys.duckdb）, sqlite（デフォルト data/monitoring.db）
    - 環境種別: KABUSYS_ENV（development, paper_trading, live のバリデーション）
    - ログレベル: LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL のバリデーション）
    - ユーティリティプロパティ: is_live, is_paper, is_dev
- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - DataLayer 構成に基づくテーブル群を定義（Raw / Processed / Feature / Execution 各レイヤー）:
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー、外部キー、CHECK 制約（例: 非負チェック、側 (buy/sell) の列挙制約、サイズ正数チェック 等）を設定。
  - 頻出クエリに備えたインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
  - テーブル作成順を外部キー依存関係に配慮して管理。
  - init_schema(db_path) を実装:
    - 指定した DuckDB ファイルを初期化し、すべてのテーブルとインデックスを作成（冪等）。
    - db_path が ":memory:" でない場合は親ディレクトリを自動作成。
    - 初期化済みの duckdb 接続オブジェクトを返す。
  - get_connection(db_path) を実装（スキーマ初期化は行わず既存 DB に接続するユーティリティ）。
- モジュール雛形を追加
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（パッケージ構造の骨組み）。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 必須トークンや認証関連設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）は Settings で必須とし、未設定時は ValueError を投げることで安全性を確保（明示的に設定を要求）。

---

注意事項・移行メモ:
- リポジトリ配布後も環境変数の自動ロードが働くため、テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードの影響を無効化できます。
- 初回利用時は init_schema() を呼んで DuckDB スキーマを初期化してください。既存 DB に接続する場合は get_connection() を使用してください。
- .env.example を参照して必要な環境変数を設定してください（ライブラリは必須項目の未設定時にエラーになります）。