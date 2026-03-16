# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
現在のバージョンは 0.1.0 です。

## [Unreleased]
（次回リリース用の空セクション）

## [0.1.0] - 2026-03-16
初回リリース

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - モジュール構成: data, strategy, execution, monitoring（空のパッケージ初期化を含む）

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定読み込みを自動化
    - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）によりカレントワーキングディレクトリに依存しない読み込み
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）
  - 複雑な .env パーサ実装（コメント、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など）
  - Settings クラスに主要設定プロパティを定義
    - J-Quants / kabuステーション / Slack / DB パス等の必須・既定値管理
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）
    - Path 型での duckdb/sqlite パス解決ユーティリティ
  - 必須環境変数未設定時に明示的なエラーを発生させる _require 関数

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（JSON デコード・エラーハンドリング）
  - レート制限の実装（固定間隔スロットリング、デフォルト 120 req/min）
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 429 の場合は Retry-After ヘッダを優先
  - 401 に対する自動トークンリフレッシュ（1 回まで）とトークンキャッシュ共有（ページネーション間）
  - ページネーション対応のデータ取得関数
    - fetch_daily_quotes（OHLCV 日足、ページネーション）
    - fetch_financial_statements（四半期 BS/PL、ページネーション）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ保存する冪等性のある保存関数（ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ（_to_float, _to_int）: 無効な値は None として扱う。_to_int は小数部が存在する場合は変換を行わない（意図しない切り捨て防止）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマ定義を追加
    - 主要テーブル（例）: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など
  - スキーマ初期化ユーティリティ
    - init_schema(db_path) — ディレクトリ自動作成、全テーブルとインデックスの作成（冪等）
    - get_connection(db_path) — 既存 DB への接続取得（スキーマ初期化は行わない）
  - 頻出クエリに対するインデックス定義を含む

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリポイント run_daily_etl を実装
    - 処理順: 市場カレンダー取得 → 株価差分取得（backfill）→ 財務データ差分取得 → 品質チェック（オプション）
    - 各ステップは独立して例外処理され、1 ステップ失敗でも他は継続（全件収集方針）
    - backfill_days と calendar_lookahead_days による再取得と先読み制御
    - 営業日補正（market_calendar に基づき target_date を直近の営業日に調整）
  - 個別 ETL ジョブを分離
    - run_prices_etl, run_financials_etl, run_calendar_etl（差分取得ロジック、backfill/lookahead 対応）
  - ETL 実行結果を格納する ETLResult データクラス
    - 取得／保存件数、品質問題リスト、エラーメッセージを持つ
    - 品質エラー判定ヘルパ（has_quality_errors）と dict 変換ユーティリティ

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - シグナルから約定に至る監査テーブル群を追加
    - signal_events（戦略生成シグナル）
    - order_requests（発注要求、冪等キー: order_request_id）
    - executions（証券会社由来の約定ログ）
  - テーブル作成ユーティリティ
    - init_audit_schema(conn) — 既存接続に監査テーブルを追加（UTC タイムゾーン設定を実行）
    - init_audit_db(db_path) — 監査用 DB の初期化
  - 監査用のインデックス定義（status／日付などでの検索最適化）

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラス（check_name, table, severity, detail, rows）
  - チェック実装（DuckDB 上の SQL 実行で効率的に処理）
    - check_missing_data: raw_prices の OHLC 欠損検出（severity: error）
    - check_spike: 前日比スパイク検出（LAG ウィンドウ使用、デフォルト閾値 50%）
    - （設計に重複チェック・将来日付検出等のチェックも示唆）
  - 各チェックはサンプル行を返し、Fail-Fast ではなく全件収集する設計

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- J-Quants の認証トークンは Settings 経由で環境変数から取得（直接ハードコードなし）
- .env の読み込みでは OS 環境変数を保護する仕組み（protected set）を導入

---

注:
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は、追加のユーザ向け変更点・既知の制約・互換性情報を補足してください。