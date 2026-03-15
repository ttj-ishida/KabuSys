# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-15

初回リリース。

### 追加 (Added)
- パッケージの初期化
  - パッケージメタデータ: `kabusys.__version__ = "0.1.0"`、公開モジュール一覧 (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 環境変数・設定管理 (`kabusys.config`)
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準にパッケージ設置位置からプロジェクトルートを特定するユーティリティを追加。これにより CWD に依存せず .env 自動読み込みが可能。
  - .env 自動読み込み機能:
    - 読み込み順序: OS 環境変数 > `.env.local` > `.env`
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - OS 環境変数は保護（上書き防止）される仕組みを実装。
  - .env パースの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート（エスケープ対応）やインラインコメント（`#`）の取り扱いを実装。
    - 無効行やキー欠損の安全処理。
  - `Settings` クラスを提供し、プロパティ経由で設定取得:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`（必須）
    - kabuステーション API: `KABU_API_PASSWORD`（必須）、`KABU_API_BASE_URL`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `SLACK_BOT_TOKEN`（必須）、`SLACK_CHANNEL_ID`（必須）
    - DB パス: `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）、`SQLITE_PATH`（デフォルト: `data/monitoring.db`）
    - システム設定: `KABUSYS_ENV`（`development` / `paper_trading` / `live`）、`LOG_LEVEL`（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
    - 利便性メソッド: `is_live`, `is_paper`, `is_dev`
  - 必須設定未提供時には明確な `ValueError` を送出。

- J-Quants データクライアント (`kabusys.data.jquants_client`)
  - ベース実装:
    - API ベース URL: `https://api.jquants.com/v1`
    - レート制限（120 req/min）に合わせた固定間隔スロットリング `_RateLimiter` を実装（モジュール内共有）。
    - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス（408, 429, 5xx）、429 の場合は `Retry-After` ヘッダを優先。
    - 401 受信時はリフレッシュトークンを用いてトークンを自動更新し 1 回だけリトライ。
    - ID トークンのモジュールレベルキャッシュを実装し、ページネーション間で共有。
    - JSON レスポンスのデコード失敗やネットワークエラーに対する明示的なエラーメッセージ。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）を取得。
    - fetch_financial_statements: 財務（四半期 BS/PL）を取得。
    - fetch_market_calendar: JPX マーケットカレンダー（祝日・半日・SQ）を取得。
    - 各関数は pagination_key を使ったページネーションを処理し、取得件数をログ出力。
  - 認証補助:
    - get_id_token(refresh_token=None): リフレッシュトークンから ID トークンを取得（POST）。
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes: `raw_prices` へ保存。主キー欠損行はスキップし、`ON CONFLICT DO UPDATE` により冪等性を確保。fetched_at を UTC ISO8601 で記録して Look-ahead Bias 防止をサポート。
    - save_financial_statements: `raw_financials` へ保存（冪等）。
    - save_market_calendar: `market_calendar` へ保存（冪等）。`HolidayDivision` を解釈して `is_trading_day` / `is_half_day` / `is_sq_day` を判定。
  - 型変換ユーティリティ:
    - _to_float / _to_int: 安全に None を扱い、文字列等からの変換規則を定義（"1.0" → 1 を許容、非ゼロ小数部は None を返す等）。

- DuckDB スキーマ定義 & 初期化 (`kabusys.data.schema`)
  - 3 層データモデルに基づくテーブル定義を実装:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 制約（CHECK, PRIMARY KEY, FOREIGN KEY）や合理的な型を設定。
  - 頻出クエリ用のインデックス群を定義（銘柄×日付、ステータス検索、外部キー結合等を想定）。
  - 初期化 API:
    - init_schema(db_path): DB ファイルの親ディレクトリを自動作成し、すべての DDL とインデックスを実行して接続を返す（冪等）。
    - get_connection(db_path): 既存 DB への単純接続（スキーマ初期化は行わない）。
  - ":memory:" 対応でインメモリ DB を使用可能。

- 監査ログ / トレーサビリティ (`kabusys.data.audit`)
  - 監査テーブルの DDL を追加（戦略→シグナル→発注→約定までの UUID 連鎖を保存）。
  - テーブル:
    - `signal_events`: 戦略が生成したすべてのシグナルを記録（棄却・エラーも含む）。
    - `order_requests`: 発注要求（`order_request_id` を冪等キーとして扱う）。注文種別に応じた CHECK 制約（limit/stop/market）の組合せチェックを実装。
    - `executions`: 証券会社から返された約定情報を保存（`broker_execution_id` をユニーク・冪等キー相当として扱う）。
  - 監査用インデックスを追加（シグナル検索、status ベースのキュー取得、broker_order_id 紐付け等）。
  - 初期化 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（UTC タイムゾーンを強制）。
    - init_audit_db(db_path): 監査専用 DB を初期化して接続を返す。
  - 設計方針の注記として、TIMESTAMP は UTC 保存、監査ログは削除しない（FK は ON DELETE RESTRICT）等を明記。

- その他
  - 空のパッケージモジュールプレースホルダを追加: `kabusys.data.__init__`, `kabusys.execution.__init__`, `kabusys.strategy.__init__`, `kabusys.monitoring.__init__`（将来的な拡張点）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の注意点 / マイグレーション
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後や別配置環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境変数を用意することを推奨します。
- DuckDB スキーマは多くの制約（CHECK / FK / PK）を含むため、手動で外部ツールからデータを投入する場合は制約違反に注意してください。
- 監査テーブルは削除を想定していない設計です。データ削除が必要な運用要件がある場合は別途検討してください。
- J-Quants クライアントは最大リトライ回数・レート制限を内部で厳守します。高速大量取得を行う用途では注意してください（API レート制限に合わせた実装）。

---

（以降のリリースでは Unreleased セクションに変更を積み上げ、リリース時にバージョンヘッダと日付を追加してください。）