CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
バージョンの付け方は SemVer を想定しています。

[Unreleased]
-------------

（現在のコードベースは初回リリース v0.1.0 として記録されています）

[0.1.0] - 2026-03-16
-------------------

Added
- パッケージ初回リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py: __version__)

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたはプロセス環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env による上書きを防止。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索
  - .env の行パーサを実装（コメント対応、export プレフィックス対応、引用符内のエスケープ対応など）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス等の設定取得プロパティ
    - env（KABUSYS_ENV）と log_level（LOG_LEVEL）の値検証（有効値セットを定義）
    - duckdb/sqlite のデフォルトパス設定
    - is_live / is_paper / is_dev の利便性プロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装 (_request)
    - レート制限（固定間隔スロットリング）を実装（120 req/min、間隔 60/120 秒）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）
    - 429 の場合は Retry-After ヘッダを尊重
    - 401 受信時にリフレッシュトークンで自動リフレッシュ（1 回のみ）
    - ページネーション対応
  - get_id_token(): リフレッシュトークンから ID トークンを取得する POST 実装
  - データ取得関数:
    - fetch_daily_quotes: 日次株価（OHLCV）取得（ページネーション）
    - fetch_financial_statements: 四半期財務データ取得（ページネーション）
    - fetch_market_calendar: JPX マーケットカレンダー取得
    - 取得時にフェッチ時刻（fetched_at）を UTC でトレースする設計思想を採用
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE）
    - save_daily_quotes: raw_prices テーブルに保存（PK: date, code）
    - save_financial_statements: raw_financials に保存（PK: code, report_date, period_type）
    - save_market_calendar: market_calendar に保存（PK: date）
  - ユーティリティ:
    - _to_float / _to_int: 変換ロジック（空値・不正値は None、int への浮動小数文字列処理の注意点等）

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - データレイヤーを 3 層（Raw / Processed / Feature）＋ Execution 層で定義
  - 多数のテーブル DDL を含む（例: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, orders, trades, positions, portfolio_performance など）
  - 運用上の検索性を考慮したインデックス定義を追加
  - init_schema(db_path) でディレクトリ自動作成とテーブル作成（冪等）を実行
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL 実装（run_daily_etl）:
    - 市場カレンダー取得 -> 営業日調整 -> 株価 ETL -> 財務 ETL -> 品質チェック の順で実行
    - 各ステップは個別に例外ハンドリングされ、1 ステップ失敗でも他は継続
    - 結果を ETLResult dataclass に格納（取得数 / 保存数 / 品質問題 / エラー要約 等）
  - 差分更新ロジック:
    - raw_* テーブルの最終取得日を基に差分のみ取得
    - デフォルトのバックフィル日数 backfill_days = 3（最終取得日の数日前から再取得して後出し修正を吸収）
    - calendar の先読みデフォルト 90 日
    - 最小データ開始日 _MIN_DATA_DATE = 2017-01-01 を定義
  - 個別ジョブ:
    - run_prices_etl / run_financials_etl / run_calendar_etl（それぞれ取得 → 保存 を実行）
  - トレース・ログ記録を行う（logger 出力）

- 監査ログ（監査 / トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナル → 発注 → 約定のトレーサビリティ用テーブルを定義
    - signal_events, order_requests, executions を提供
  - order_request_id を冪等キーとして二重発注防止を想定
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema で SET TimeZone='UTC' を実行）
  - インデックスを含むテーブル初期化関数 init_audit_schema / init_audit_db を実装

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（必須カラムの NULL をエラーとして検出）
    - check_spike: 前日比スパイク（LAG ウィンドウを使い、閾値超の変動を検出）
      - デフォルト閾値: 0.5（50%）
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集する設計
  - DuckDB の SQL をパラメータバインドで実行（インジェクション対策）

- パッケージ構造
  - サブパッケージのスケルトンを配置: data, strategy, execution, monitoring（将来の拡張領域）
  - data 以下に jquants_client, schema, pipeline, audit, quality を実装

Changed
- 初回リリースのため、API/設計の初期選定を反映（設計方針やデフォルト値を多数設定）
  - レート制限、リトライポリシー、バックフィル・先読み日数、品質判定閾値など

Fixed
- （該当なし: 初回リリース）

Removed
- （該当なし: 初回リリース）

Deprecated
- （該当なし: 初回リリース）

Security
- （該当なし: 初回リリース）

Notes / 使用上の重要ポイント
- 環境変数の必須項目（Settings のプロパティで _require を使っているため未設定だと ValueError が発生します）
  - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
- DuckDB の初期化は init_schema() を推奨。既存 DB に接続するだけなら get_connection() を使用。
- J-Quants API 呼び出しはモジュールレベルでトークンキャッシュを保持（ページネーション間で共有）。必要な場合は _get_cached_token(force_refresh=True) 相当の挙動で更新される。
- ETL 実行時に品質チェックを行うと QualityIssue のリストが ETLResult に含まれる。重大度に応じた運用判断（ETL 停止など）は呼び出し元で行う設計。

今後の予定（例）
- execution / strategy / monitoring の具体実装（注文送信/ポジション管理／戦略実装／監視・アラート）
- 追加の品質チェック（重複検出、将来日付検出など）の実装拡充
- 単体テスト・統合テストの追加と CI 設定
- ドキュメント（DataSchema.md, DataPlatform.md 等）の整備・公開

---
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして利用する場合は各変更点の確認・調整を行ってください。）