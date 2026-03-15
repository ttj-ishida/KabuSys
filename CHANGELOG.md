# CHANGELOG

すべての非互換変更はここに記録します。本ファイルは Keep a Changelog の慣習に従います。  
バージョン番号はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システムのコア基盤を実装しました。

### Added
- パッケージ初期化
  - パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を追加。
  - `__all__` に主要サブパッケージを公開：data, strategy, execution, monitoring。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは `__file__` の親ディレクトリ群から `.git` または `pyproject.toml` を探索して特定。
  - 自動ロードを無効化するフラグ：`KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 読み込み優先順位：OS 環境変数 > `.env.local` > `.env`（`.env.local` は上書き）。
  - .env パース機能を強化：
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を正しく抽出。
    - クォートなしの値に対するインラインコメント判定（直前が空白/タブの場合）に対応。
  - `.env` 読み込み時の上書き制御：`protected` セットを使って OS 環境変数を保護。
  - Settings クラスを実装し、プロパティ経由で各種設定を取得可能：
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB, SQLite） / 環境種別（development, paper_trading, live）/ ログレベル（DEBUG, INFO, ...）/ is_live/is_paper/is_dev 判定
  - 必須環境変数取得時に未設定なら明示的な例外（ValueError）を投げる `_require` を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API への共通 HTTP リクエスト処理を実装（JSON デコード検査、30s タイムアウト）。
  - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を実装。
  - 冪等な ID トークンキャッシュを実装し、401 受信時に自動でトークンをリフレッシュして 1 回だけリトライする仕組みを導入。
  - リトライロジックを実装（指数バックオフ、最大 3 回）。リトライ対象は 408/429/5xx（429 は Retry-After ヘッダを優先）。
  - API 用の高レベル関数を追加：
    - get_id_token(refresh_token: Optional[str]) → idToken を取得（POST）。
    - fetch_daily_quotes(...) → 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements(...) → 財務（四半期 BS/PL）をページネーション対応で取得。
    - fetch_market_calendar(...) → JPX マーケットカレンダーを取得。
  - DuckDB への保存用ユーティリティ（冪等）を追加：
    - save_daily_quotes(conn, records) → raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE。取得時刻（fetched_at）は UTC ISO8601 で記録し Look-ahead Bias のトレースを可能に。
    - save_financial_statements(conn, records) → raw_financials テーブルへ冪等保存。
    - save_market_calendar(conn, records) → market_calendar テーブルへ冪等保存（holidayDivision を is_trading_day / is_half_day / is_sq_day に変換）。
  - データ変換ユーティリティを追加：
    - _to_float / _to_int：空値や不正値を None に落とし、_to_int は小数部が存在する場合は変換を拒否する安全な変換ロジックを実装。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を実装。
  - 主なテーブル（一部列挙）：
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - バリデーション制約（CHECK、PRIMARY KEY、FOREIGN KEY）を付与してデータ整合性を確保。
  - 頻出クエリ向けのインデックスを定義（コード×日付、ステータス検索、外部キー参照用等）。
  - 初期化/接続 API を提供：
    - init_schema(db_path) → DB ファイルを作成（必要なら親ディレクトリ作成）し、DDL を実行して接続を返す（冪等）。
    - get_connection(db_path) → 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール（kabusys.data.audit）
  - シグナル→発注→約定までを UUID 連鎖で完全トレース可能にする監査用テーブル群を実装。
  - テーブル群：
    - signal_events（戦略が生成したシグナルと棄却理由などを記録）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う。limit/stop のチェック制約あり）
    - executions（証券会社の約定情報。broker_execution_id をユニーク冪等キーとして記録）
  - すべての TIMESTAMP を UTC で保存するために初期化で `SET TimeZone='UTC'` を実行。
  - 監査用インデックスを複数定義（シグナル検索、状態検索、外部コールバック紐付け等）。
  - init_audit_schema(conn) / init_audit_db(db_path) API を提供し、既存接続へ監査テーブルを追加可能。

- パッケージ構成
  - data パッケージに各モジュールを配置（jquants_client, schema, audit など）。
  - strategy、execution、monitoring パッケージは初期プレースホルダとして存在。

### Changed
- 該当なし（初回リリース）。

### Fixed
- 該当なし（初回リリース）。

### Deprecated
- 該当なし（初回リリース）。

### Removed
- 該当なし（初回リリース）。

### Security
- J-Quants のトークンは環境変数経由で取得する設計。自動ロードの無効化フラグと OS 環境変数保護（protected set）によりテスト時や運用時の誤上書きを防止。

---

既知の注意点・設計上のポイント（補足）
- J-Quants API 呼び出しは内部でレートリミットとリトライを厳格に守る設計だが、運用環境におけるネットワークや API ポリシーの変更に注意すること。
- DuckDB スキーマは外部キー制約や CHECK を多用しているため、外部システムからのデータ投入時は前処理を行って整合性を保つこと。
- audit テーブルは削除を想定しない設計（ON DELETE RESTRICT）で監査証跡を保持する。

（以降のリリースでは、strategy 実装、execution のブローカー連携、monitoring のメトリクス/アラート等を追加していく予定です。）