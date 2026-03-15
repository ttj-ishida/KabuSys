CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しており、重要な変更点を分かりやすく記録します。

フォーマット:
- Unreleased: 今後の変更（現状は空）
- 各リリースはバージョンと日付を併記
- 各リリース内は Added / Changed / Fixed / Deprecated / Removed / Security セクションで整理

Unreleased
----------
（現在未登録の変更はありません）

0.1.0 - 2026-03-15
-----------------

Added
- パッケージ初回リリース（kabusys v0.1.0）。
- パッケージ公開情報:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理モジュール（src/kabusys/config.py）を追加:
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env 読み込み機能:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml で検出（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - テスト等で自動読み込みを無効にするためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS 側既存環境変数は保護され、.env による上書き回避が可能。
  - .env のパースは以下に対応:
    - export KEY=val 形式。
    - シングル/ダブルクォート、バックスラッシュエスケープの取り扱い。
    - コメントの取り扱い（インラインコメントの条件付き認識）。
  - 必須環境変数未設定時は ValueError を送出する _require() を提供。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加:
  - 取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 設計上の特徴:
    - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大試行回数 3 回。対象は 408/429 と 5xx、およびネットワークエラー。
    - 401 受信時は ID トークンを自動リフレッシュして1回だけリトライ（無限再帰回避）。
    - id_token のモジュールレベルキャッシュを保持（ページネーション間で共有）。
    - ページネーション対応（pagination_key を用いたループ）により全件取得。
    - 取得時刻（fetched_at）を UTC ISO8601 形式で記録（Look-ahead Bias 対策）。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - save_daily_quotes(conn, records) / save_financial_statements(conn, records) / save_market_calendar(conn, records)
      - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複更新を排除。
    - 内部ユーティリティ: _to_float, _to_int（安全な変換ロジック、"1.0" のような文字列処理など）

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）を追加:
  - データ層の3層構造を明確化: Raw / Processed / Feature（＋Execution）。
  - テーブル定義（DDL）を網羅:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - よく使われるクエリに備えたインデックス定義を追加。
  - 依存関係を考慮したテーブル作成順を用意。
  - 公開 API:
    - init_schema(db_path) -> DuckDB 接続（親ディレクトリ自動作成、":memory:" 対応、冪等にテーブル作成）
    - get_connection(db_path) -> 既存 DB への接続（スキーマ初期化は行わない）

- 監査ログ・トレーサビリティ（src/kabusys/data/audit.py）を追加:
  - シグナルから約定までのトレースを行う監査テーブル群を定義:
    - signal_events（戦略が生成したシグナルのログ。棄却やエラーも記録）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う）
    - executions（証券会社から返る約定情報。broker_execution_id を冪等キー）
  - 設計原則の明記:
    - 全ての TIMESTAMP は UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - テーブルは削除しない前提（FOREIGN KEY に ON DELETE RESTRICT）
    - order_requests のチェック制約: order_type に応じた limit_price/stop_price の必須/禁則を表現
    - 状態遷移（pending → sent → filled / partially_filled / cancelled / rejected / error）
  - インデックスを多数定義（status, signal_id, broker_order_id など検索に最適化）。
  - 公開 API:
    - init_audit_schema(conn)（既存接続へ監査テーブルを追加）
    - init_audit_db(db_path)（監査専用 DB を作成して接続を返す）

- モジュール構成:
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（パッケージの骨組み、将来の拡張用）。現状は空の __init__。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

マイグレーション / 利用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須扱い。未設定時は ValueError が発生します。
- .env 自動ロード:
  - パッケージはインポート時にプロジェクトルートを探索して .env / .env.local を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時推奨）。
- DuckDB スキーマ初期化:
  - データベース初回作成時は init_schema() を呼び出してテーブル／インデックスを作成してください。既存 DB へ接続するだけなら get_connection() を使用してください。
- 監査ログの UTC 保持:
  - init_audit_schema() はタイムゾーンを UTC に設定します。監査用途では全ての TIMESTAMP が UTC で格納されます。
- リトライとレート制限:
  - J-Quants クライアントは 120 req/min のレート制限を尊重します。大量データ取得時は処理時間やレート制限に注意してください。
- 冪等性:
  - raw_* テーブルへの保存は ON CONFLICT DO UPDATE を使用しているため、再実行で重複行が上書きされます。
- 数値変換の挙動:
  - _to_int は "1.0" のような文字列を int に変換することがある一方、小数部が存在する値（例: "1.9"）は None を返します。データの正確性に注意してください。

今後の予定（例）
- strategy / execution / monitoring パッケージに具体的実装を追加し、オーダー送信フロー・ポートフォリオ最適化・アラート監視を実装予定。
- Slack 通知や kabuステーション連携の実装拡充。

貢献・問い合わせ
- 本 CHANGELOG はリポジトリ内のソースコードに基づき推測して作成しています。実装や設計の詳細についてはコードを参照してください。