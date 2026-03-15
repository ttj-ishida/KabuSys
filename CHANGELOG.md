# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基本骨格と設定・データ層を実装。

### 追加
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージメタ情報を追加（__version__="0.1.0", __all__ に主要モジュールを公開）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動ロードの実装
    - プロジェクトルートを .git または pyproject.toml から特定する _find_project_root() を実装（cwd に依存しない探索）。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途）。
    - OS に既にある環境変数は保護され、.env.local の override 時も保護されたキーは上書きされない。
  - .env パーサーの実装（_parse_env_line）
    - 空行・コメント（#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートを扱い、バックスラッシュによるエスケープを正しく処理。
    - 非クォート値の行内コメント処理（'#' の扱いは直前がスペース/タブの場合のみコメントとして扱う）。
  - .env 読み込みでのファイル読み取りエラーは warnings.warn により警告出力するように実装（例外でプロセスを止めない）。
  - Settings プロパティによる必須設定の取得（未設定時は ValueError を送出する _require() を実装）。
  - 各種設定プロパティを実装:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3層（Raw / Processed / Feature）と Execution 層をカバーするテーブル群を DDL 文字列で定義。
  - Raw レイヤー:
    - raw_prices, raw_financials, raw_news, raw_executions（各テーブルに適切な型・チェック制約・PRIMARY KEY を定義）
  - Processed レイヤー:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols（外部キー制約を含む）
  - Feature レイヤー:
    - features, ai_scores（特徴量・AI スコア格納）
  - Execution レイヤー:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（状態列・チェック制約・外部キー・ステータス列など）
  - 各テーブルに対してデータ整合性を保つ CHECK 制約や PRIMARY/FOREIGN KEY を設定（例: price >= 0、size > 0、side/check 制約等）。
  - news_symbols に対する ON DELETE CASCADE、orders -> signal_queue の外部キーは ON DELETE SET NULL など、削除ポリシーを明示。
  - パフォーマンス向けインデックスの定義（頻出クエリに備えた index 作成文を列挙）。
  - init_schema(db_path) を実装
    - DuckDB データベースを初期化して全テーブル・インデックスを作成（冪等、既存テーブルはスキップ）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" を指定してインメモリ DB を使用可能。
    - 実行後に duckdb 接続オブジェクトを返す。
  - get_connection(db_path) を実装（スキーマ初期化は行わず既存 DB への接続のみ）。

- パッケージ空パッケージ初期化ファイル
  - src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/data/__init__.py、src/kabusys/monitoring/__init__.py を追加（将来的な機能拡張用のプレースホルダ）。

### 注意（動作・設計）
- .env 読み込みはプロジェクトルート検出に依存するため、配布後も __file__ から親ディレクトリを辿る実装になっており、実行時のカレントディレクトリに依存しない設計。
- 環境変数の保護機構により、OS 環境変数は意図せず上書きされない挙動（.env.local の override は行うが、既存 OS 環境変数は保護される）。
- スキーマの CREATE 文は idempotent（IF NOT EXISTS を利用）であり、繰り返し初期化可能。

--- 

このリポジトリの次のステップ（例）
- 各サブモジュール（execution, strategy, monitoring, data）に具体的な実装を追加
- 単体テスト・CI 設定、型チェック、Lint などの導入
- マイグレーション機構（スキーマバージョン管理）や運用向けの設定拡張

（注）本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。