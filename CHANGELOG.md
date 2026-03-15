# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
タグ/バージョンはソース内の __version__ に基づきます。

なお、以下は提示されたコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-15

### Added
- パッケージ基礎
  - 初期リリース。パッケージ名は `kabusys`、バージョン `0.1.0`。
  - パッケージ公開用のモジュールエクスポートを定義（`__all__ = ["data", "strategy", "execution", "monitoring"]`）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む機能を追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。これによりカレントワーキングディレクトリに依存せず自動読み込みが可能。
  - 自動 .env ロードの順序: OS環境 > .env.local > .env。OS 環境変数は保護され上書きされない（保護セットを実装）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。
  - `.env` パーサーの強化:
    - 空行・コメント行を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応し、対応する閉じクォートまで正しく解析。
    - クォート無し値のインラインコメント扱い（`#` の前が空白/タブの場合）に対応。
  - .env 読み込み関数に `override` と `protected` パラメータを実装し、挙動を細かく制御可能。

- Settings クラス（環境変数の高レベル API）
  - `Settings` クラスを提供し、プロパティ経由でアプリ設定を取得可能。
  - J-Quants / kabuステーション / Slack / データベースパス等の必須・既定設定をプロパティ化:
    - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`（未設定時は ValueError を送出）。
    - kabu API のベース URL のデフォルト: `http://localhost:18080/kabusapi`。
    - データベース既定パス: DuckDB は `data/kabusys.duckdb`、SQLite は `data/monitoring.db`（`~` 展開対応）。
  - システム環境（`KABUSYS_ENV`）のバリデーション（許容値: `development`, `paper_trading`, `live`）。不正な値は ValueError。
  - ログレベル（`LOG_LEVEL`）のバリデーション（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。
  - 利便性プロパティ: `is_live`, `is_paper`, `is_dev` を提供。

- データスキーマ（kabusys.data.schema）
  - DuckDB 用のスキーマ定義と初期化ロジックを追加（Raw / Processed / Feature / Execution レイヤーを定義）。
  - 定義済テーブル（主なもの）:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して合理的な型・CHECK 制約・PRIMARY KEY・外部キーを設定してデータ整合性を担保。
  - 頻出クエリパターンを想定したインデックスを多数追加（例: 銘柄×日付スキャン、ステータス検索など）。
  - スキーマ初期化関数:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定した DuckDB ファイルのディレクトリを自動作成（":memory:" はそのまま利用）。
      - 全テーブル・インデックスを作成（冪等）。
      - 初回接続のための利便性を提供。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない）。
  - スキーマ設計は DataSchema.md に基づく（コメント記載）。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定までトレーサビリティを担保する監査テーブル群を追加。
  - トレーサビリティ階層や設計原則文書化（UUID を用いた連鎖、削除禁止、UTC タイムスタンプ、updated_at の運用等）。
  - 監査用テーブル:
    - `signal_events`（戦略が生成したシグナルの全記録。リスクで棄却されたものも含む）
    - `order_requests`（冪等キーである `order_request_id` を持つ発注要求ログ、各種 CHECK 制約を含む）
    - `executions`（証券会社からの約定ログ、broker_execution_id をユニークキーとして扱う）
  - インデックスを多数追加（signal_id やステータス、broker_order_id 等での検索を高速化）。
  - 初期化関数:
    - `init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None`
      - 渡した接続に対して監査テーブルを追加（冪等）。実行時に `SET TimeZone='UTC'` を行い全タイムスタンプを UTC で保存。
    - `init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 監査専用 DB を作成し接続を返す。DB ファイルの親ディレクトリ自動作成を行う。
  - スキーマはトレーサビリティと冪等性を重視した設計（外部キーは ON DELETE RESTRICT などを採用）。

- パッケージ構成
  - `execution`, `strategy`, `monitoring`, `data` などのモジュール・パッケージ初期ファイルを配置し、今後の実装のための骨組みを用意。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- センシティブな設定（API トークンやパスワード）は環境変数を必須にしており、設定漏れ時は起動時に明確な例外（ValueError）を投げることで安全性を向上。

---

注記:
- DuckDB（Python バインディング）を利用します。実行環境に duckdb が必要です。
- audit スキーマはすべての TIMESTAMP を UTC で保存する前提です。アプリ側で updated_at を更新する運用を必要とします。
- .env パーサーはシェルの完全な互換性を保証するものではありませんが、一般的な export/quote/comment のパターンを考慮しています。