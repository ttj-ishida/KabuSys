CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
詳細: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュールを追加。
  - パッケージバージョン: 0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動で読み込む仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定: __file__ を起点に上位ディレクトリから .git または pyproject.toml を検索
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを実装
    - 空行・コメント行を無視
    - export KEY=val 形式に対応
    - シングル／ダブルクォートを扱い、バックスラッシュでのエスケープに対応
    - クォートなしの右側のコメントは '#' の前がスペース／タブの場合のみコメントとして扱う
  - .env 読み込みの上書きルール
    - override フラグを利用し、OS 環境変数を protected（上書き不可）として保護
  - Settings クラスによるプロパティ式設定取得を提供
    - 必須設定を検証し未設定時は ValueError を送出（_require）
    - 主なプロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 補助プロパティ: is_live, is_paper, is_dev

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - 3層構造のスキーマ定義（Raw / Processed / Feature / Execution）
  - 主なテーブル（例）
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル定義にチェック制約（非負、主キー、外部キー、列チェック等）を付与
  - 頻出クエリに備えたインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - DB ファイルの親ディレクトリを自動作成
      - 全テーブル／インデックスを冪等的に作成
      - ":memory:" を指定してインメモリ DB を使用可能
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ単純接続（初回スキーマ作成は行わない）

- パッケージ構成
  - モジュールプレースホルダ: src/kabusys/execution, src/kabusys/strategy, src/kabusys/monitoring（__init__.py を含む）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

注意事項 / マイグレーション
- 初回セットアップ手順（推奨）
  1. 環境変数または .env を用意する（.env.example を参照）
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
     - 必要に応じて DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV を設定
  2. スキーマ初期化: from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)
  3. 自動 .env ロードを無効化したいテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

実装上の注記（利用者向け）
- .env パーサの挙動:
  - クォート内はバックスラッシュエスケープを解釈し、インラインコメントはクォートの外でのみ有効
  - export プレフィックスを許容
- Settings は値の妥当性チェック（ENV 値、ログレベルなど）を行い、不正値で ValueError を送出するため、呼び出し側で例外処理を検討してください
- init_schema は既存テーブルがあればそれを上書きせずスキップするため、安全に何度でも実行可能（冪等）

既知の制限
- 現時点では各サブパッケージ（strategy, execution, monitoring）の実装は含まれておらず、プレースホルダとなっています。
- DuckDB 依存のため環境に duckdb パッケージが必要です。

貢献者
- 初期実装: (プロジェクト作成者)