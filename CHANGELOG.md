KEEP A CHANGELOG
全ての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
- （なし）

[0.1.0] - 2026-03-16
Added
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys.config: 環境変数/設定管理
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - 高度な .env パーサ実装（コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ対応）
    - Settings クラスによる型付きアクセサ（必須キーの検証、env/log level のバリデーション、パスの Path 化）
    - 主要環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等
- データ層（kabusys.data）:
  - jquants_client:
    - J-Quants API クライアント実装
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）
    - 401 発生時にリフレッシュトークンから id_token を自動再取得して再試行（無限再帰防止）
    - ページネーション対応の取得関数:
      - fetch_daily_quotes（株価日足 OHLCV）
      - fetch_financial_statements（財務データ：四半期 BS/PL）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB へ冪等に保存する関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）
    - 型変換ユーティリティ（_to_float, _to_int）や fetched_at に UTC タイムスタンプを付与
  - schema:
    - DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - Raw / Processed / Feature / Execution 層のテーブル群を定義（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, orders, trades, positions, portfolio_performance 等）
    - 参照整合性・制約・チェック制約を積極的に導入（NULL/型/範囲チェック、PRIMARY KEY、FOREIGN KEY、CHECK 等）
    - よく使うクエリのためのインデックス定義
    - テーブル作成順を外部キー依存に配慮して管理
  - pipeline:
    - ETL パイプライン（差分取得、保存、品質チェック）の実装
    - 差分更新ロジック（DB の最終取得日に基づく自動 date_from 計算、デフォルトバックフィル日数 = 3）
    - 市場カレンダー先読み（デフォルト 90 日）と営業日調整（非営業日の場合は過去方向で直近営業日に調整）
    - run_daily_etl エントリポイント（カレンダー → 株価 → 財務 → 品質チェックの順で実行、各ステップは独立してエラーハンドリング）
    - ETL 実行結果を表す ETLResult データクラス（取得数／保存数／品質問題／エラー一覧を保持）
  - audit:
    - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化関数（init_audit_schema, init_audit_db）
    - トレーサビリティ設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id のチェーン）
    - 発注要求の冪等キー（order_request_id）、タイムゾーンを UTC に固定する設定、created_at/updated_at の運用ルール
    - ステータス遷移管理や必要なチェック制約、関連インデックスを提供
  - quality:
    - データ品質チェックモジュール（DuckDB 上で効率的に実行）
    - 実装済みチェック:
      - check_missing_data: raw_prices の OHLC 欄の欠損検出（Severity: error）
      - check_spike: 前日比スパイク検出（デフォルト閾値 0.5 = 50%）
    - QualityIssue データクラス（check_name, table, severity, detail, rows）
    - pipeline からの呼び出しで集約し、重大度に応じた判定を行う設計（Fail-Fast ではなく問題を全件収集）
- 公開 API の主な関数/クラス（利用しやすいようにドキュメント文字列あり）:
  - settings (Settings インスタンス)
  - data.schema.init_schema / get_connection
  - data.audit.init_audit_schema / init_audit_db
  - data.jquants_client.get_id_token / fetch_* / save_*
  - data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- パッケージメタ:
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし。

Security
- HTTP タイムアウトや例外ハンドリング、リトライ/バックオフ、トークンリフレッシュなどを組み込み、API 呼び出しの堅牢性と安全性を強化。

Notes / TODO（コードから推測）
- strategy/execution パッケージは __init__ が存在するが実装は未着手（プレースホルダ）。
- quality モジュールのコメントには重複チェック・日付不整合検出も想定されているが、本リリースでは主に欠損検出とスパイク検出が実装済み。
- 実運用では J-Quants のレート制限や Retry-After ヘッダに基づく待機の微調整、監査ログの永続化ポリシー、SLACK 連携等の追加実装が想定される。

--- 
（注）本 CHANGELOG は提供されたソースコードから実装状況を推測して作成しています。実際のリリースノート作成時は追加のコミット履歴・リリース方針に基づき更新してください。