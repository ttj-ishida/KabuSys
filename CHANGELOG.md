# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースはコードベースから推測して作成しています。

※ バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づいています。

## [Unreleased]
### 追加
- なし（初期リリースのみ）

## [0.1.0] - 2026-03-15
初期リリース。日本株向け自動売買システムの基盤となる設定管理・データスキーマ・パッケージ構成を追加。

### 追加
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
  - public API として "data", "strategy", "execution", "monitoring" をエクスポート（__all__）。

- 環境変数 / 設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して特定（カレントワーキングディレクトリに依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テストなどで使用）。
    - OS 環境変数を保護するために、既存の環境変数は .env（override=False）で上書きされない。`.env.local` は override=True で上書き可能だが保護リストを尊重。
  - .env 解析の強化:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート値のエスケープ処理を考慮したパース（バックスラッシュエスケープ対応）。
    - クォート無し値に対するインラインコメント認識（`#` の前が空白/タブの場合にコメント扱い）。
  - 必須設定を取得するヘルパー _require を実装（未設定時は ValueError を送出）。
  - 主要な設定プロパティを追加:
    - J-Quants: jquants_refresh_token（必須）
    - kabuステーション API: kabu_api_password（必須）、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須）、slack_channel_id（必須）
    - データベースパス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
    - システム設定: env（KABUSYS_ENV、許可値: development/paper_trading/live のバリデーション）、log_level（LOG_LEVEL の検証: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパープロパティ: is_live, is_paper, is_dev

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - 3層（+Execution）アーキテクチャに基づくスキーマを追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な制約を設定:
    - 主キー（PRIMARY KEY）、外部キー（FOREIGN KEY）、CHECK 制約（値のレンジ・列値集合など）を多数定義
    - 外部キーの ON DELETE 動作を設定（CASCADE / SET NULL 等）
  - 検索パフォーマンスを考慮したインデックス定義を追加（銘柄×日付やステータス検索に合わせたインデックス群）。
  - テーブル作成順を明示して依存関係を考慮（DDL の順序管理）。
  - 公開 API:
    - init_schema(db_path): 指定したパスの DuckDB を初期化し全テーブル・インデックスを作成。親ディレクトリが無ければ自動作成。":memory:" でインメモリ DB 対応。
    - get_connection(db_path): 既存の DuckDB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。
  - duckdb ライブラリを利用して実装。

- サブパッケージのプレースホルダ
  - src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/data/__init__.py、src/kabusys/monitoring/__init__.py を追加（将来的な機能実装のためのパッケージ構成）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 削除
- なし（初回リリース）

### セキュリティ
- なし（初回リリース）