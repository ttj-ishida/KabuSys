# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」の仕様に準拠しています。  
リリース日はコミット・マージ日などに合わせて調整してください。

※この CHANGELOG はリポジトリ内の現在のコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: `__version__ = "0.1.0"`
  - 公開モジュール: data, strategy, execution, monitoring（各サブパッケージの __init__.py を配置）

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装
    - ロード優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: カレントファイル位置から親ディレクトリを探索し、`.git` または `pyproject.toml` を基準に判定
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パース実装
    - コメント行・空行をスキップ
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理を考慮した値の抽出
    - クォートなしの場合、`#` が直前にスペースまたはタブある場合のみコメントと扱う等の細かい挙動
  - .env 読み込み時の上書き制御
    - `override` フラグにより既存の環境変数上書きの可否を制御
    - `protected`（OS 環境変数のコピー）を用いて上書きを防止する仕組み
  - Settings クラスにより型付きプロパティで設定値を提供
    - J-Quants: `jquants_refresh_token`（必須: `JQUANTS_REFRESH_TOKEN`）
    - kabuステーション API: `kabu_api_password`（必須: `KABU_API_PASSWORD`）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須: `SLACK_BOT_TOKEN`）、`slack_channel_id`（必須: `SLACK_CHANNEL_ID`）
    - データベース: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - システム設定: `env`（`development|paper_trading|live` のバリデーション）、`log_level`（`DEBUG|INFO|WARNING|ERROR|CRITICAL` のバリデーション）、および `is_live` / `is_paper` / `is_dev` ブール補助プロパティ
  - 必須環境変数未設定時に分かりやすい例外を送出

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Data layer 構成（3〜4 層）に基づくテーブル設計を実装:
    - Raw Layer
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer
      - features, ai_scores
    - Execution Layer
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル定義に型チェック／制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY 等）を含む
  - 頻出クエリに備えたインデックス定義を追加
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など
  - テーブル作成順を依存関係に基づいて管理（外部キーを考慮）
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスに対してディレクトリ自動作成（メモリ DB の場合はスキップ）
      - 全テーブル・インデックスを作成（冪等）
      - 初期化済みの DuckDB 接続を返す
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を取得（スキーマ初期化は行わない）

### Changed
- 初回リリースのため特になし

### Fixed
- 初回リリースのため特になし

### Removed
- 初回リリースのため特になし

### Security
- 初回リリースのため特になし

---

補足:
- strategy / execution / monitoring サブパッケージはプレースホルダーとして存在しており、今後アルゴリズム・発注・監視ロジックを追加する設計になっています。
- .env のパースや自動ロードの挙動はユニットテストや CI 環境での再現性を考慮して設計されています（自動ロードの無効化フラグ等）。
- DuckDB のスキーマは将来的な分析・戦略実行を想定した設計になっており、外部キーやインデックスを付与してパフォーマンスと整合性を重視しています。