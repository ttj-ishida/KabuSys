# CHANGELOG

すべての注目すべき変更はここに記載します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
- 初期リリース (v0.1.0) を追加予定。実装内容の追加・修正はここに記載します。

## [0.1.0] - 2026-03-15
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む設定管理モジュールを実装。
  - プロジェクトルート検出: 現在のファイル位置から親ディレクトリを上位へ探索し、`.git` または `pyproject.toml` を基準にプロジェクトルートを特定する仕組みを追加。これにより CWD に依存せず自動ロードが可能。
  - .env パーサー（詳細かつ堅牢なパース実装）:
    - 空行・コメント行（行頭 `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートされた値のバックスラッシュエスケープを考慮して正しく復元。
    - クォートなし値については inline コメント（`#`）を適切に無視（直前が空白/タブの場合にコメント扱い）。
  - .env 読み込みの優先順位:
    - OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで自動ロードを無効化可能（テスト用途想定）。
    - プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 自動ロード時の保護機能:
    - OS 環境変数は保護対象（protected）とし、`.env.local` であっても既存の OS 環境変数を上書きしない仕組みを実装（ただし override=True の場合でも保護対象は上書きされない）。
  - 必須設定の取得用ユーティリティ `_require` を実装し、未設定時に明確な ValueError を送出。
  - Settings クラスを提供し、環境変数からアプリ設定をプロパティ経由で取得可能に：
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - システム設定: `env`（`development|paper_trading|live` の検証）、`log_level`（`DEBUG|INFO|WARNING|ERROR|CRITICAL` の検証）および環境判定補助 `is_live`/`is_paper`/`is_dev` を追加。
  - 不正な環境値に対して明確なエラー（ValueError）を投げるバリデーションを実装。

- データスキーマと DB 初期化 (src/kabusys/data/schema.py)
  - DuckDB を用いた多層データモデル（Raw / Processed / Feature / Execution）用の DDL を実装。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する厳密な型チェック・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を定義。
  - 頻出クエリに備えたインデックス群を定義（例: code×date インデックス、status インデックス等）。
  - 外部キー依存を考慮したテーブル作成順を管理。
  - 公開 API:
    - init_schema(db_path): DuckDB ファイル（または ":memory:"）を初期化して全テーブル・インデックスを作成。親ディレクトリがなければ自動作成。作成は冪等（既存はスキップ）。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を呼ぶこと）。
  - 初期化・接続に関するドキュメンテーション文字列を充実させ、使い方を明確化。

- モジュールプレースホルダ
  - execution, strategy, data, monitoring パッケージの __init__ を追加（将来的な拡張のためのプレースホルダ）。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- なし（初回リリースのため）。

### セキュリティ (Security)
- なし（該当する特記事項はなし）。

### マイグレーション / 注意事項
- 初回利用時は必ず init_schema() を呼び出して DuckDB のスキーマを作成してください。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）が未設定だと Settings のプロパティ呼び出しで ValueError が発生します。`.env.example` を参照して `.env` を準備してください。
- 自動的に .env をロードする仕組みはデフォルトで有効です。テストなどで自動ロードを抑止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB ファイルパスのデフォルトは `data/kabusys.duckdb`（duckdb）および `data/monitoring.db`（sqlite）です。必要に応じて環境変数で変更してください。

---

※ ここに記載された変更は、提供されたソースコードから推測してまとめた初期リリースの内容です。リポジトリに付随する追加ドキュメントや将来のコミットによって詳細が異なる場合があります。