# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  
安定版のセマンティックバージョニングを採用します。

## [Unreleased]


## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージ初期構成を追加（kabusys 0.1.0）。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョン `0.1.0` とモジュールエクスポート（data, strategy, execution, monitoring）を定義。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に再帰的に探索して特定（カレントワーキングディレクトリに依存しない実装）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用途を想定）。
    - 読み込み順序: OS環境変数 > .env.local > .env。`.env.local` は既存の値を上書き可能（ただし OS 環境変数として存在するキーは保護）。
  - .env のパース処理を強化:
    - 空行・コメント行（# で始まる行）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートで囲まれた値をサポートし、バックスラッシュによるエスケープ処理を考慮して対応する閉じクォートまで正しくパース。
    - クォート無し値では、`#` が直前にスペース/タブがある場合のみコメント開始と判定（一般的な .env の解釈に合わせる）。
    - 無効な行は安全にスキップ。
  - 設定取得用の Settings クラスを提供（インスタンス: `settings`）。
    - J-Quants / kabuステーション / Slack / データベースパス 等のプロパティを定義。
    - 必須環境変数未設定時は明示的な ValueError を送出（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。
    - データベースパスは Path 型で返却（デフォルト: DuckDB -> `data/kabusys.duckdb`, SQLite -> `data/monitoring.db`）。
    - システム環境（`KABUSYS_ENV`）は `development`, `paper_trading`, `live` のいずれかに制限し、不正な値はエラーにする。
    - ログレベル（`LOG_LEVEL`）は `DEBUG/INFO/WARNING/ERROR/CRITICAL` のいずれかに制限。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Data Lake の 3 層 + 実行層に対応するテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、NOT NULL 制約、CHECK 制約、PRIMARY KEY、外部キー制約を設定（例: side の CHECK、価格/サイズの非負チェックなど）。
  - パフォーマンスのためのインデックス群を定義（銘柄×日付スキャンやステータス検索を想定したインデックス）。
  - スキーマ初期化 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスの親ディレクトリを自動作成（":memory:" はインメモリ DB をサポート）。
      - すべてのテーブルとインデックスを作成（既存ならスキップ、冪等）。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を呼ぶことを想定）。

- モジュールプレースホルダを追加:
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py
  - これによりパッケージ構造を明示し、将来的な機能拡張のためのエントリポイントを確保。

### Notes
- 初期リリースでは主要なビジネスロジック（戦略、発注ロジック、モニタリング機能など）は未実装で、基盤（設定読み込み、DB スキーマ、パッケージ構成）を提供することに注力しています。
- DuckDB スキーマは外部キーや CHECK 制約を多く含むため、外部システムからデータを投入する場合は制約違反に注意してください。
- .env の自動ロードはプロジェクトルートを探索して行うため、パッケージ配布後や CI 環境でのテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してロードを制御することを推奨します。

### Known issues
- なし（初回リリース）。今後のリリースでユニットテスト、ドキュメント、エラーハンドリングの強化を予定。

