# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
このプロジェクトはセマンティック バージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-16

Added
- 初回リリース: KabuSys — 日本株自動売買プラットフォームのコア基盤を追加。
- パッケージ公開 API
  - src/kabusys/__init__.py: バージョン 0.1.0 を設定。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
- 環境変数・設定管理
  - src/kabusys/config.py:
    - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
    - .env 行パーサの強化（export プレフィックス対応、シングル/ダブルクォート中のエスケープ処理、インラインコメント処理）。
    - Settings クラスを実装。J-Quants、kabuステーション、Slack、DBパスなどの設定をプロパティ経由で取得。
    - 必須環境変数未設定時に分かりやすいエラーを送出。KABUSYS_ENV / LOG_LEVEL の値検証を実装。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を追加。
    - レート制限制御（120 req/min）用の固定間隔スロットリング（RateLimiter）を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。429 の場合は Retry-After を優先。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライする仕組みを実装（無限再帰防止のため allow_refresh フラグを使用）。
    - ページネーション対応（pagination_key を利用して全件取得）。
    - 取得時刻（fetched_at）を UTC で記録して look-ahead bias を回避。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等に実行（ON CONFLICT DO UPDATE を使用）。主キー欠損行はスキップして警告ログを出力。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の耐性を向上。
    - get_id_token (refresh token → id token) を POST で取得する機能を提供。
- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution の多層スキーマを定義（テーブル定義多数）。
    - インデックス定義を含む（典型的なクエリパターンに対する最適化）。
    - init_schema(db_path) で DB ファイル親ディレクトリの自動作成、DDL 実行（冪等）・接続返却を実装。
    - get_connection(db_path) で既存 DB への接続を取得。
- ETL パイプライン
  - src/kabusys/data/pipeline.py:
    - 日次 ETL の主要フローを実装（run_daily_etl）。
    - 差分更新ロジック（最終取得日を基に date_from を算出）、backfill（デフォルト 3 日）、カレンダー先読み（デフォルト 90 日）をサポート。
    - 個別ジョブ: run_calendar_etl, run_prices_etl, run_financials_etl を実装。
    - 各ステップは独立して例外処理され、1ステップ失敗でも残りの処理を継続して結果を集約する設計。
    - ETL 実行結果を表す ETLResult dataclass を追加（品質問題やエラー一覧を保持、ディクショナリ変換機能付き）。
    - 営業日調整ヘルパー (_adjust_to_trading_day) を実装。market_calendar があれば直近営業日に調整。
    - DB の最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
- データ品質チェック
  - src/kabusys/data/quality.py:
    - 品質チェック基盤と QualityIssue dataclass を実装。
    - チェック項目のうち少なくとも以下を実装: 欠損データ検出（OHLC 欠損の検出）、スパイク検出（前日比の絶対変動が閾値を超える場合。デフォルト閾値 50%）。
    - 各チェックは問題のサンプル行（最大 10 件）と集計を返し、Fail-Fast ではなく全件収集する設計。
    - DuckDB の SQL をパラメータバインドで実行し、効率的かつ安全に検査を行う。
- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py:
    - シグナル→発注要求→約定までを UUID 連鎖で完全トレースする監査テーブルを定義（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして利用する設計（重複送信防止）。
    - すべての TIMESTAMP を UTC で保存する旨を明示し、init_audit_schema で SET TimeZone='UTC' を実行。
    - 監査用インデックス群を定義（検索やジョインを効率化）。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供。
- パッケージ構造のプレースホルダ
  - src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/data/__init__.py を配置（将来の拡張ポイント）。

Changed
- -（初回リリースのため該当なし）

Fixed
- -（初回リリースのため該当なし）

Security
- 環境変数は OS 環境を保護する仕組み（.env の上書き制御、protected set）を導入。自動ロードは明示的に無効化可能。

Notes / Implementation details
- DuckDB へのテーブル作成は冪等（CREATE TABLE IF NOT EXISTS / ON CONFLICT）で設計されているため、複数回の初期化や ETL 実行で安全に使用可能です。
- J-Quants クライアントはページネーションとトークンキャッシュをサポートしており、長時間のデータ取得でも効率的に動作します。
- 品質チェックは ETL の後にオプションで実行され、重大な品質問題は ETLResult に反映されます。呼び出し元で停止/アラート判断を行ってください。

参考
- 主要ファイル:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/schema.py
  - src/kabusys/data/pipeline.py
  - src/kabusys/data/quality.py
  - src/kabusys/data/audit.py

--- 
作成: 自動生成（コードベースの内容に基づく推測）