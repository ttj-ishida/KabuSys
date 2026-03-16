# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
安定版リリースのセマンティクスに従い、主に機能追加（Added）、修正（Fixed）、変更（Changed）を記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース: kabusys 0.1.0
- 基本パッケージ構成を追加
  - モジュール: data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装
  - プロジェクトルート検出 (_find_project_root)：.git または pyproject.toml を基準に探索
  - .env パーサー実装（クォート、エスケープ、コメント、export プレフィックス対応）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスで主要設定をプロパティとして提供
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などの必須取得関数
    - デフォルト値サポート（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用の fetch_* 関数を実装
  - ページネーション対応（pagination_key を利用して繰り返し取得）
  - レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
  - 再試行ロジック（指数バックオフ、最大 3 回、対象: HTTP 408/429 および 5xx、ネットワークエラー）
  - 401 受信時はリフレッシュトークンから id_token を自動更新して1回リトライ
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
  - JSON デコードエラー時の明示的なエラーメッセージ
  - DuckDB に対する冪等保存用の save_* 関数（ON CONFLICT DO UPDATE）を実装
  - 保存時に fetched_at を UTC ISO フォーマットで記録（Look-ahead Bias 対策）
  - 型変換ユーティリティ (_to_float, _to_int) を実装（安全な変換と不正値扱い）

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層アーキテクチャに基づくテーブル群を定義（Raw / Processed / Feature / Execution）
  - raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance などを含む DDL を実装
  - 各種 CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義してデータ整合性を強化
  - 利用頻度の高いクエリ向けのインデックスを定義
  - init_schema(db_path) による冪等的な初期化（親ディレクトリ自動作成、":memory:" サポート）
  - get_connection(db_path) を提供（既存DBへの接続）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の実装（run_daily_etl）
    - 市場カレンダー、株価、財務データの差分取得・保存・品質チェックを順次実行
    - 各ステップは個別に例外処理され、1ステップ失敗でも他ステップは継続
    - カレンダー先読み（デフォルト 90 日）、バックフィル（デフォルト 3 日）をサポート
    - 営業日調整（非営業日は直近の営業日に調整）
    - ETLResult データクラスで実行結果・品質問題・エラー概要を返す（監査ログや通知用）
  - 個別 ETL ジョブを提供: run_prices_etl, run_financials_etl, run_calendar_etl
  - 差分更新ヘルパー関数: get_last_price_date, get_last_financial_date, get_last_calendar_date

- 監査ログ（Audit）機能（src/kabusys/data/audit.py）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群を実装
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとする設計
  - すべての TIMESTAMP を UTC で保存するための初期化（SET TimeZone='UTC'）
  - init_audit_schema(conn) と init_audit_db(db_path) を提供
  - 発注・約定の状態遷移や制約を DDL として明文化
  - 監査用インデックスを定義

- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比の絶対変動が閾値を超える場合、デフォルト閾値 0.5=50%）
  - 重複チェック、日付不整合チェック等の設計方針を準備（SQL ベース）
  - QualityIssue データクラスを導入し、チェック結果を一律で返却（severity を含む）
  - SQL はパラメータバインドを使用してインジェクションリスクを低減

### Changed
- 新規リリースのための初期構成。既存プロジェクトへの影響は無し。

### Fixed
- （初期リリースのため該当なし）

### Security
- HTTP リクエストでの JSON デコード失敗やトークン更新失敗時に明示的に失敗することで不正な状態の継続を防止

---

開発・設計上の注記（要約）
- API 呼び出しはレート制御・リトライ・トークン自動更新を組み合わせて堅牢性を高めています。
- DuckDB スキーマは冪等に作成され、データ整合性（PK/FK/CHECK）と検索効率（インデックス）が考慮されています。
- ETL は差分更新・バックフィル・品質チェックを組み合わせ、運用時の後出し修正やデータ品質問題に対処します。
- 監査ログは UUID ベースでトレーサビリティを保証し、削除を伴わない監査設計になっています。
- 環境変数パーサーは .env の実用的なケース（クォート、エスケープ、コメント、export）に対応しています。

もしリリースノートに追記したい箇所（例: 実際のリリース日、貢献者、未実装のチェック項目など）があれば指示してください。