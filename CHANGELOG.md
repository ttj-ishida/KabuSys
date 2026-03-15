# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

イテレーション: Unreleased → 0.1.0

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-15
初期リリース。日本株自動売買システムの基盤モジュール群を提供します。

### Added
- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - パッケージの公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` で宣言。

- 環境設定管理 (`src/kabusys/config.py`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジックを実装：`_find_project_root()` は `.git` または `pyproject.toml` を探索してプロジェクトルートを特定（CWD に依存しない）。
  - .env パーサーを実装：`_parse_env_line()` はコメント、`export KEY=val` 形式、シングル／ダブルクォート（エスケープ含む）、およびインラインコメントの扱いをサポート。
  - 自動ロードの優先順位を実装：OS環境変数 > `.env.local` > `.env`。`.env.local` は `.env` 上書き。OS 環境変数は保護され上書きされない。
  - 自動読込無効化オプション：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による無効化をサポート（テスト用途）。
  - 必須環境変数取得ユーティリティ：`_require(key)` は未設定時に明確な `ValueError` を投げ `.env.example` を参照する旨をメッセージに含める。
  - Settings クラスを提供（プロパティ経由で設定を取得）
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（`env`, `log_level`, `is_live`, `is_paper`, `is_dev`）を取得可能。
    - `env` と `log_level` は固定された有効値集合でバリデーションを行う（不正な値は `ValueError`）。

- データ層スキーマ (`src/kabusys/data/schema.py`)
  - DuckDB 用のスキーマ定義と初期化機能を追加。
  - Raw / Processed / Feature / Execution の四層構造テーブルを定義（各DDLは冪等で CREATE TABLE IF NOT EXISTS を使用）。
    - Raw レイヤー: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed レイヤー: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature レイヤー: `features`, `ai_scores`
    - Execution レイヤー: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに適切なデータ型、チェック制約（負値防止、列長チェック、ENUM 代替の CHECK 等）および主キーを設定。
  - パフォーマンスを考慮したインデックス群を定義（銘柄×日付スキャン、ステータス検索、外部キー結合支援など）。
  - スキーマ作成順を外部キー依存に配慮して定義。
  - DB 初期化ユーティリティを実装：
    - `init_schema(db_path)`：DuckDB ファイルを初期化し全テーブルとインデックスを作成（parent ディレクトリを自動作成、`:memory:` サポート）。初回用のスキーマ作成に使用。
    - `get_connection(db_path)`：既存 DB へ接続（スキーマ初期化は行わない）。

- 監査ログ（Audit）スキーマ (`src/kabusys/data/audit.py`)
  - 監査/トレーサビリティ用テーブルを定義・初期化するモジュールを追加。
  - トレーサビリティモデルをドキュメント化（business_date → strategy_id → signal_id → order_request_id → broker_order_id の連鎖）。
  - テーブル定義
    - `signal_events`：戦略が生成したすべてのシグナルを記録（棄却・エラー含む）。`decision` 列に多数のステータスを明示。
    - `order_requests`：冪等キー `order_request_id` を持つ発注要求ログ。`order_type` に応じた価格チェック（limit/stop/market に対する制約）を添付。`updated_at` はアプリ側で更新する想定。
    - `executions`：証券会社からの約定情報を保存。`broker_execution_id` をユニーク（冪等キーとして扱う）。
  - すべての TIMESTAMP を UTC で保存する方針。`init_audit_schema` の中で `SET TimeZone='UTC'` を実行。
  - 監査向けインデックス群を定義（signal の日付/銘柄検索、status キュー検索、broker_order_id/broker_execution_id での参照等）。
  - 初期化関数を提供：
    - `init_audit_schema(conn)`：既存の DuckDB 接続に監査テーブルとインデックスを追加（冪等）。
    - `init_audit_db(db_path)`：監査専用 DB を作成し初期化した接続を返す（parent ディレクトリ自動作成、`:memory:` サポート）。

- パッケージ構成
  - モジュールプレースホルダとして `src/kabusys/execution/__init__.py`, `src/kabusys/strategy/__init__.py`, `src/kabusys/data/__init__.py`, `src/kabusys/monitoring/__init__.py` を追加（後続実装のための準備）。

### Changed
- 特になし（初期リリース）。

### Fixed
- 特になし（初期リリース）。

### Deprecated
- 特になし。

### Removed
- 特になし。

### Security
- 環境変数の自動ロードで OS 環境変数が保護されるように設計（`.env` による上書きを防止）。必要に応じて開発側が明示的に override する挙動を持つ。

---

注意事項・実装上の補足
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後やパッケージ化後の実行環境での挙動に配慮しています。自動ロードを完全に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 関連の初期化関数は冪等であり、既存テーブルやインデックスが存在する場合はスキップします。ローカルファイルを指定した場合、親ディレクトリが自動作成されます。
- 監査ログは削除しない前提で設計しています（外部キーは ON DELETE RESTRICT）。updated_at はアプリ側で更新日時を制御してください。

（以降のリリースでは戦略実装、注文実行ロジック、モニタリング機能、Slack 通知等の追加を予定）