# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
<https://keepachangelog.com/ja/1.0.0/>

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-16

初期リリース（アルファ相当）。日本株自動売買システムの基盤モジュール群を追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - パッケージの公開 API: data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを 0.1.0 に設定。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルからの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサ実装（export 形式・クォート・インラインコメントやエスケープ処理に対応）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等）。
  - 環境変数の必須チェック（未設定時に ValueError を送出）および env/log_level の値検証。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 認証トークン取得（get_id_token）とモジュール内トークンキャッシュを実装。401 受信時の自動トークンリフレッシュをサポート。
  - API リクエスト周りの堅牢化:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先処理、408/429/5xx に対する再試行。
    - ページネーション対応（pagination_key を使用）。
    - JSON デコードエラーハンドリング。
  - DuckDB への保存ユーティリティ（冪等性を意識した ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - 取得時刻のトレーサビリティ（fetched_at を UTC ISO8601 形式で付与）。
  - データ変換ユーティリティ (_to_float, _to_int)。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層データモデル（Raw / Processed / Feature / Execution）に基づくテーブル DDL を実装。
  - raw_prices / raw_financials / raw_news / raw_executions 等の Raw テーブル。
  - prices_daily / market_calendar / fundamentals / news_articles / news_symbols 等の Processed テーブル。
  - features / ai_scores 等の Feature テーブル。
  - signals / signal_queue / orders / trades / positions / portfolio_performance 等の Execution テーブル。
  - パフォーマンス向けインデックス定義を追加。
  - init_schema(db_path) により DuckDB ファイルの親ディレクトリ自動作成→全テーブル・インデックス作成（冪等）。
  - get_connection(db_path) により既存 DB への接続を取得（初回は init_schema を推奨）。

- 監査ログ（Audit）モジュール (src/kabusys/data/audit.py)
  - シグナル→発注要求→約定までのトレーサビリティを実現する監査テーブルを追加:
    - signal_events（シグナル生成ログ）、order_requests（冪等キー付き発注要求）、executions（約定ログ）。
  - 発注要求の制約（limit/stop/market の価格必須/禁止チェック）やステータス管理を実装。
  - init_audit_schema(conn) で監査テーブルとインデックスを既存接続に追加（UTC タイムゾーン固定）。
  - init_audit_db(db_path) で監査専用 DB 初期化をサポート。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - DataPlatform に基づく品質チェックを実装。
  - チェック項目:
    - 欠損データ検出（check_missing_data: raw_prices の OHLC 欄）
    - 異常値（スパイク）検出（check_spike: 前日比閾値、デフォルト 50%）
    - 重複チェック（check_duplicates: 主キー重複 date, code）
    - 日付不整合チェック（check_date_consistency: 未来日付・market_calendar による非営業日検出）
  - 各チェックは QualityIssue オブジェクトのリストを返す（fail-fast ではなく全件収集）。
  - run_all_checks で一括実行と統計ログ出力。

- モジュールパッケージ構成
  - data, strategy, execution, monitoring のパッケージを配置（strategy/execution/monitoring は現状で初期化ファイルのみ）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- API トークンの自動リフレッシュを実装し、認証失敗時に安全に再試行する処理を導入（401 ハンドリング）。
- .env 自動読み込み時に既存 OS 環境変数を保護する仕組み（protected set）を実装。

## 既知の注意点 / マイグレーション
- DuckDB スキーマは初回 init_schema 時に作成されます。既存 DB との互換性やマイグレーション機能は本バージョンでは提供していません。
- audit モジュールは init_audit_schema にて既存接続へ追記する形で動作します。監査用 DB を分離する場合は init_audit_db を利用してください。
- .env の自動ロードはプロジェクトルート検出に依存しており、配布後や CWD が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化し、明示的に環境変数を設定してください。

---

今後の予定（例）
- execution 層の証券会社接続（kabu API）実装
- strategy 層のサンプル戦略とバックテスト機能
- 品質チェックのアラート通知（Slack 連携）および自動修復オプション
- スキーマのバージョン管理とマイグレーションツール

ご要望やバグ報告があればお知らせください。