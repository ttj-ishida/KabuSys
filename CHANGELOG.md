# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]


## [0.1.0] - 2026-03-16

### Added
- 初回リリース。日本株自動売買システム「kabusys」のコアモジュール群を追加。
- パッケージ管理
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - モジュールエクスポート: data, strategy, execution, monitoring

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出は .git または pyproject.toml を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env 行パーサはコメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮して堅牢に処理。
  - 必須値取得ヘルパー `_require`（未設定時は ValueError）。
  - Settings クラスにて以下を取得・検証:
    - J-Quants / kabu ステーション / Slack の必須トークン
    - DB のデフォルトパス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）
    - 環境 (development/paper_trading/live) とログレベルのバリデーション
    - is_live / is_paper / is_dev の判定ヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得 API を実装。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）。
  - 401 受信時は自動で ID トークンをリフレッシュして 1 回リトライ（無限再帰防止）。
  - ページネーション対応（pagination_key を用いたループ）とモジュールレベルの ID トークンキャッシュの共有。
  - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を保証（ON CONFLICT DO UPDATE）し、fetched_at を UTC で記録。
  - 型変換ユーティリティ `_to_float` / `_to_int` を提供（不正な値は None）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の多層スキーマを定義（多数のテーブルDDLを実装）。
  - インデックス定義を含む（頻出クエリを考慮）。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル作成（冪等）。
  - get_connection(db_path) を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う日次 ETL を実装（run_daily_etl）。
  - 処理フロー:
    1. 市場カレンダー ETL（先読み: デフォルト 90 日）
    2. 株価日足 ETL（差分 + backfill、デフォルト backfill_days = 3）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）
  - 差分取得のためのヘルパー（最終取得日の取得、営業日への調整）。
  - ETLResult dataclass により取得数・保存数・品質問題・エラーを集約。品質問題は詳細なリストとして取得可能。
  - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - signal_events, order_requests, executions テーブルと関連インデックスを定義。
  - 監査用スキーマ初期化関数 init_audit_schema(conn) と監査専用 DB 初期化 init_audit_db(path) を提供。
  - すべての TIMESTAMP を UTC で保存する方針（init で SET TimeZone='UTC' を実行）。
  - 発注リクエストは order_request_id を冪等キーとして扱う制約・チェックを実装。
  - 発注ステータス遷移や制約（limit/stop/market の必須/排他ルール）をスキーマレベルで表現。

- データ品質チェック (src/kabusys/data/quality.py)
  - 以下のチェックを実装:
    - 欠損データ検出（OHLC の NULL）
    - 異常値（スパイク）検出（前日比の絶対変化率で判定、デフォルト閾値 50%）
    - （今後の拡張想定: 重複、日付不整合などのチェック）
  - 各チェックは QualityIssue dataclass のリストを返し、重大度（error/warning）・サンプル行を含む。
  - SQL を用いた効率的なチェック実装（パラメータバインド使用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API 認証トークンは環境変数から取得する設計（トークンの自動リフレッシュ機能あり）。セキュリティに関しては外部にトークンを書き出さない運用を前提。

Notes / 実装上の重要点
- J-Quants クライアントはレートリミットとリトライ、トークンリフレッシュを組み合わせて堅牢性を確保しています。429 の場合は Retry-After ヘッダを優先して待機します。
- DuckDB への保存は可能な限り冪等に設計されています（ON CONFLICT DO UPDATE）。
- ETL は Fail-Fast を採らず、品質問題を収集して呼び出し元で判断できるようにしています。
- audit スキーマは削除を前提とせず、監査ログの永続化とトレーサビリティを重視しています。

Contributors
- 初期実装: 開発チーム（リポジトリ内コードより推測）

参考
- DataPlatform.md / DataSchema.md に基づく設計（ソース内コメントを参照）。

----- 
（必要に応じて日付や担当者、リリースノートの詳細を追加してください。）