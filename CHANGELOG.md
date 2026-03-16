Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

フォーマット:
- 変更はカテゴリごとに分類（Added, Changed, Fixed, Deprecated, Removed, Security）
- バージョンと日付を付与

Unreleased
----------

（なし）

0.1.0 - 2026-03-16
------------------

Added
- パッケージ初期リリース。日本株自動売買システムのコアモジュールを追加。
  - src/kabusys/__init__.py
    - パッケージのメタ情報（__version__ = "0.1.0"）、公開モジュール一覧を定義。
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env ロード機構（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env パーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD、OS 環境変数保護（override/protected）対応。
    - 必須環境変数取得ヘルパ _require と環境値検証（KABUSYS_ENV, LOG_LEVEL）。
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - レート制限制御（固定間隔スロットリング: 120 req/min を守る _RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）と 408/429/5xx 対応。
    - 401 受信時の自動トークンリフレッシュ（get_id_token を用いて1回のみリトライ）。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務データ)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB への冪等性のある保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 型変換ユーティリティ: _to_float, _to_int
    - id_token のモジュールレベルキャッシュ実装（ページネーション間で共有）。
  - src/kabusys/data/schema.py
    - DuckDB 用の包括的スキーマ定義と初期化機能を提供。
    - Raw / Processed / Feature / Execution 層のテーブル DDL を定義（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, orders, trades, positions, 等）。
    - 頻出クエリに基づくインデックスを作成。
    - init_schema() によりディレクトリ作成・テーブル作成（冪等）を実行、get_connection() を提供。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの実装（差分更新・バックフィル・品質チェックの統合）。
    - 差分取得のヘルパ（最終取得日の算出 get_last_price_date 等）。
    - 市場カレンダー先読み（lookahead）、バックフィル（デフォルト 3 日）実装。
    - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブを提供。
    - run_daily_etl による日次一括処理（各ステップは個別にエラーハンドリング）。
    - ETLResult データクラス（結果集約、品質問題・エラー一覧保持、辞書変換）。
  - src/kabusys/data/quality.py
    - データ品質チェックの実装（欠損、スパイク、重複、日付不整合等を想定）。
    - QualityIssue データクラスを定義し、チェック結果を構造化。
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行取得・件数集計）。
    - check_spike: 前日比スパイク検出（LAG ウィンドウ関数、閾値デフォルト 50%）。
    - DuckDB 上の効率的な SQL 実行とサンプル行収集を重視した設計。
  - src/kabusys/data/audit.py
    - 監査ログ（トレーサビリティ）用スキーマと初期化機能を実装。
    - signal_events, order_requests, executions の DDL を定義（冪等性・監査要件に準拠）。
    - order_request_id を冪等キーとして扱う設計、タイムスタンプは UTC 保存（SET TimeZone='UTC'）。
    - init_audit_schema, init_audit_db を提供。
    - 監査用インデックスを追加し検索効率を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 認証トークン管理において、refresh トークンからの id_token 取得処理を明示（get_id_token）し、
  401 時の自動リフレッシュで無限再帰しないよう allow_refresh フラグを導入。

Notes / 実装上の留意点
- J-Quants API のレート制限やリトライ挙動は実装済みだが、実運用ではさらに監視・メトリクスの導入を推奨。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD による制御や明示的な設定提供を検討してください。
- DuckDB のスキーマ初期化は冪等性を保つが、既存スキーマの変更（マイグレーション）は本リリースでは未提供。
- quality チェックは Fail-Fast ではなく全件収集する設計（呼び出し元が重大度に応じて対応）。

作者: kabusys チーム
