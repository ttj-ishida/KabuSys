# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリースはセマンティックバージョニングに従います。  
- 不要な過去履歴は含めず、コードベースから推測可能な変更点・初期リリースの内容を記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回公開リリース。日本株の自動売買システム用ライブラリの基礎機能を提供します。

### Added
- パッケージのエントリポイントを追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - エクスポートモジュール: `data`, `strategy`, `execution`, `monitoring`
- 環境設定管理モジュール (`kabusys.config`)
  - `.env` / `.env.local` をプロジェクトルート（.git または pyproject.toml）から自動読み込み（優先順: OS 環境 > .env.local > .env）
  - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサ:
    - `export KEY=val` 形式対応
    - シングル／ダブルクォート対応（バックスラッシュでのエスケープ処理を考慮）
    - インラインコメントの取り扱い（クォート有無で異なる動作）
  - 必須環境変数取得ユーティリティ `_require` と設定オブジェクト `Settings` を提供
    - 必須キー（例）: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パスのデフォルト: `DUCKDB_PATH="data/kabusys.duckdb"`, `SQLITE_PATH="data/monitoring.db"`
    - 環境検証: `KABUSYS_ENV` は `development|paper_trading|live`、`LOG_LEVEL` は `DEBUG|INFO|WARNING|ERROR|CRITICAL` を検証
    - ヘルパープロパティ: `is_live`, `is_paper`, `is_dev`
- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API ベース: `https://api.jquants.com/v1`
  - レート制御:
    - レート制限を守る固定間隔スロットリング（デフォルト 120 req/min → 最小間隔 0.5s）
  - リトライポリシー:
    - 最大 3 回のリトライ（指数バックオフ、base=2.0）
    - リトライ対象: HTTP 408/429、及び 5xx
    - 429 の場合は `Retry-After` ヘッダを優先
    - ネットワークエラー（URLError/OSError）に対するリトライ
  - 認証の取り扱い:
    - リフレッシュトークンから ID トークンを取得する `get_id_token`
    - モジュールレベルの ID トークンキャッシュを共有（ページネーション間で再利用）
    - 401 受信時は自動的にトークンをリフレッシュして 1 回だけ再試行（再帰防止のため一部呼び出しでは更新を禁止）
  - データ取得関数（ページネーション対応）:
    - `fetch_daily_quotes(...)` — 株価日足（OHLCV）
    - `fetch_financial_statements(...)` — 財務（四半期 BS/PL）
    - `fetch_market_calendar(...)` — JPX カレンダー（祝日・半日・SQ）
  - DuckDB 保存用関数（冪等性を考慮した upsert 実装）:
    - `save_daily_quotes(conn, records)` → raw_prices に INSERT ... ON CONFLICT DO UPDATE
    - `save_financial_statements(conn, records)` → raw_financials に upsert
    - `save_market_calendar(conn, records)` → market_calendar に upsert
  - Look-ahead バイアス対策:
    - 取得時刻を UTC の `fetched_at` フィールドに保存
  - 型変換ユーティリティ:
    - `_to_float` / `_to_int`（空値・不整合値は None）
    - `_to_int` は "1.0" のような表現を許容するが小数部がある場合は None を返す
- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - 3 層（Raw / Processed / Feature）＋Execution 層のテーブルを定義
  - 主なテーブル（抜粋）:
    - Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature: `features`, `ai_scores`
    - Execution: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - インデックス定義（クエリパターンを想定して多数追加）
  - 公開 API:
    - `init_schema(db_path)` — ディレクトリ自動作成、スキーマを冪等で作成して接続を返す
    - `get_connection(db_path)` — 既存 DB への接続（スキーマ初期化は行わない）
- 監査ログ（トレーサビリティ）サポート (`kabusys.data.audit`)
  - シグナル→発注→約定の一貫したトレースを可能にする監査テーブルを定義
  - テーブル:
    - `signal_events`（戦略が生成した全シグナルを保存。棄却・エラーも記録）
    - `order_requests`（冪等キー order_request_id を持つ発注要求ログ）
    - `executions`（証券会社からの約定情報）
  - すべての TIMESTAMP を UTC で保存（`init_audit_schema` 内で `SET TimeZone='UTC'` を実行）
  - 公開 API:
    - `init_audit_schema(conn)` — 既存接続へ監査テーブルを追加
    - `init_audit_db(db_path)` — 監査専用 DB を初期化して接続を返す
- パッケージ内に空のサブパッケージ雛形を追加
  - `kabusys.execution`, `kabusys.strategy`, `kabusys.monitoring`（将来の実装用のプレースホルダ）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- DuckDB の初期化 (`init_schema`) は db_path の親ディレクトリが存在しない場合に自動で作成します。ファイルパスに `":memory:"` を渡すとインメモリ DB を使用します。
- 自動で .env を読み込む振る舞いはデフォルトで有効です。テストや CI で自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API を利用するためには `JQUANTS_REFRESH_TOKEN` の設定が必須です。その他、kabuステーションや Slack を使う機能はそれぞれの必須環境変数が必要です（設定されていない場合は起動時にエラーとなります）。
- 監査テーブルは削除しない前提（ON DELETE RESTRICT）で設計しています。監査ログは基本的に追記のみとなる想定です。

---

（注）この CHANGELOG は与えられたソースコードから推測して作成したものであり、実際のリポジトリ運用ルールやリリース日、エントリの粒度はプロジェクト方針に合わせて調整してください。