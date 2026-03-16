# Changelog

すべての注目すべき変更は本ファイルに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-16

初回公開リリース。本リリースでは、日本株自動売買システムの基盤となる設定管理、データ取得/保存、ETLパイプライン、データ品質チェック、監査ログスキーマなどのコア機能を実装しています。

### Added
- パッケージエントリポイント
  - src/kabusys/__init__.py に __version__ と __all__ を定義。
- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - .env のパーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの処理）。
    - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - OS側環境変数を保護する protected オプション（.env.local は .env の上書きとして読むが既存 OS 環境変数は保護）。
    - Settings クラスでアプリケーション設定を型付けして提供（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル検証等）。
    - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と便宜的プロパティ（is_live / is_paper / is_dev）。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API ベース実装（株価日足、財務データ、マーケットカレンダーの取得）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx 等で再試行）。
    - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）とページネーション間での id_token キャッシュ共有。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - DuckDB への保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。いずれも冪等性を担保する ON CONFLICT DO UPDATE を使用。
    - データ変換ユーティリティ（_to_float, _to_int）を実装し、空値や不正値の安全な扱いを実現。
    - fetched_at を UTC で記録して Look-ahead bias を防止。
- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層を想定したテーブル定義群を実装。
    - 各テーブルに型チェック、CHECK 制約、主キー・外部キーを付与（データ整合性重視）。
    - 頻出クエリを考慮したインデックス群を定義。
    - init_schema(db_path) によりデータベースの初期化（テーブル作成・インデックス作成）を冪等に実行。
    - get_connection() により既存 DB への接続を提供。
- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 日次 ETL（run_daily_etl）と個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）を実装。
    - 差分更新ロジック（DB の最終取得日時を参照して未取得分のみ取得）および backfill（デフォルト 3 日）で後出し修正を吸収する設計。
    - 市場カレンダーの先読み（デフォルト 90 日）により営業日判定や将来カレンダーを事前取得。
    - 各ステップは独立したエラーハンドリングで、1 ステップの失敗が他を止めない設計。
    - ETLResult dataclass によりフェッチ数・保存数・品質問題・エラーを集約して返却。
    - テスト容易性のため id_token を注入できるインターフェース設計。
- データ品質チェック
  - src/kabusys/data/quality.py
    - QualityIssue dataclass を定義し、複数チェックの結果を一貫して扱えるように実装。
    - 欠損データ検出（OHLC の必須カラムの欠損を検出）。
    - スパイク検出（前日比の絶対変化率が閾値を超える異常を検出。デフォルト閾値 50%）。
    - 重複チェック、将来日付/営業日外などの整合性チェック（設計に基づく、SQL による効率的実装を想定）。
    - 各チェックは Fail-Fast ではなく問題を収集して返す方針。
- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py
    - シグナル→発注→約定の端から端までを UUID 連鎖でトレースする監査テーブル群を実装（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして二重発注防止を想定。
    - order_requests テーブルに order_type に応じた CHECK 制約（limit/stop/market の価格必須/禁止のルール）を追加。
    - 全 TIMESTAMP を UTC で保存するため init_audit_schema() 実行時に SET TimeZone='UTC' を適用。
    - 監査用インデックス群を提供し検索・結合パフォーマンスを向上。
- その他
  - README 相当の設計意図やドキュメントコメントを各モジュールに付与（設計原則、DataPlatform / DataSchema の参照など）。
  - エラーロギングと警告出力を適所に実装（例: .env 読み込み失敗、PK 欠損スキップ、リトライログなど）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Known limitations
- J-Quants API のエンドポイントやレスポンス仕様に依存するため、実運用では API 仕様変更に応じた更新が必要。
- 現在のリトライ／レート制御は単一プロセス内の実装。複数プロセスや分散実行環境での一意なスロットリング調整は未実装。
- quality モジュールの一部チェックは SQL 実装に依存するため、運用データのスキーマ・量によりパフォーマンスチューニングが必要になる可能性あり。
- DuckDB はローカルファイル基盤を想定。大規模分散 DB へ移行する場合はスキーマおよび接続管理の見直しが必要。

---

今後のリリース案（例）:
- Unreleased: モニタリング・アラート連携（Slack通知）、kabuステーション実行モジュールの実装、戦略層のサンプル戦略追加、単体テストの充実化。