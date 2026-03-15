# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買基盤のコア機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。
  - パッケージ公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` として宣言。

- 環境設定管理 (`src/kabusys/config.py`)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない動作。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用）。
  - .env パーサ実装
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理対応。
    - コメント（#）の扱いは文脈に応じて適切に除外。
  - .env 読み込みでの上書き制御（override フラグ）と OS 環境変数保護（protected セット）。
  - Settings クラスを公開（`settings` インスタンス）。
    - J-Quants・kabuステーション・Slack・データベースパスなど主要設定プロパティを提供。
    - 必須設定取得時は未設定で ValueError を送出（例: `JQUANTS_REFRESH_TOKEN`, `SLACK_BOT_TOKEN` 等）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）。
    - デフォルトの DB パス: DuckDB `data/kabusys.duckdb`, SQLite `data/monitoring.db` を指定。

- J-Quants API クライアント (`src/kabusys/data/jquants_client.py`)
  - API 呼び出しユーティリティを実装（HTTP リクエスト、JSON デコード、エラーハンドリング）。
  - レート制御
    - 固定間隔スロットリングで 120 req/min を遵守する `_RateLimiter` を実装。
  - リトライとバックオフ
    - ターゲットステータス（408, 429, >=500）に対して最大 3 回のリトライ（指数バックオフ）。
    - 429 の場合は `Retry-After` ヘッダを優先。
    - ネットワークエラー（URLError / OSError）にもリトライを実装。
  - トークン管理
    - リフレッシュトークンから ID トークンを取得する `get_id_token` を実装（POST）。
    - モジュールレベルの ID トークンキャッシュを保持し、401 受信時に 1 回だけ自動リフレッシュして再試行。
  - ページネーション対応のデータ取得関数を実装
    - `fetch_daily_quotes`（株価日足）
    - `fetch_financial_statements`（四半期財務）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
    - 各関数はページネーションキーを追跡し、重複防止（seen_keys）で終了判定。
    - 取得件数をログ出力。
  - DuckDB への保存ユーティリティを実装（冪等）
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - 挿入は ON CONFLICT DO UPDATE を使用して冪等性を保証。
    - 取得時刻（fetched_at）は UTC ISO8601（Z）で記録し、Look-ahead Bias 防止に配慮。
    - PK 欠損レコードはスキップして警告ログを出力。
  - 値変換ユーティリティ
    - `_to_float` / `_to_int` を実装し、不正値や空値は None を返す。`_to_int` は小数を厳密に扱い不正切り捨てを防止。

- DuckDB スキーマ定義と初期化 (`src/kabusys/data/schema.py`)
  - DataLayer に基づく包括的な DDL を実装（Raw / Processed / Feature / Execution 層）。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・主キーを多用してデータ品質を担保（CHECK、PRIMARY KEY、FOREIGN KEY）。
  - 頻出クエリに対するインデックスを定義（コード・日付検索、ステータス検索など）。
  - `init_schema(db_path)` により DuckDB の DB ファイルを作成・初期化し接続を返す（ディレクトリ自動作成、冪等）。
  - `get_connection(db_path)` を提供（既存 DB への接続、スキーマ初期化は行わない）。

- 監査ログ / トレーサビリティ (`src/kabusys/data/audit.py`)
  - シグナルから約定に至る監査テーブル群を実装（UUID 連鎖による完全トレーサビリティ）。
    - signal_events（戦略が生成したすべてのシグナルを記録）
    - order_requests（発注要求、order_request_id を冪等キーとして定義。limit/stop のチェック制約あり）
    - executions（証券会社からの約定情報、broker_execution_id をユニークキーとして冪等性を担保）
  - 監査用インデックスを整備（signal 検索、status 検索、broker_id 紐付け等）。
  - `init_audit_schema(conn)` により既存 DuckDB 接続へ監査テーブルを追加（UTC タイムゾーンを設定）。
  - `init_audit_db(db_path)` で監査専用 DB を作成・初期化するユーティリティを提供。
  - 設計上の方針を明記（TIMESTAMP は UTC、監査ログは基本的に削除しない、updated_at はアプリ側で更新等）。

- モジュール構成
  - 空のパッケージ初期化ファイルを配置（`execution`, `strategy`, `monitoring`, `data`）して拡張性を確保。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### 廃止 (Deprecated)
- 該当なし

### 削除 (Removed)
- 該当なし

### セキュリティ (Security)
- 該当なし（既知のセキュリティ問題はなし。ただし機密情報（トークン等）は .env や環境変数で安全に管理することを推奨）

---

注:
- 実装は設計原則（レート制限厳守、再試行・トークン自動更新、Look-ahead Bias 防止、冪等処理、監査トレーサビリティ）に従っています。
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時には追加の変更・修正点がある場合があります。