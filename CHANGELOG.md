Keep a Changelog 準拠の CHANGELOG.md（日本語）

All notable changes are推測に基づきコードベースから記載しています。

Unreleased
---------
- なし

0.1.0 - 2026-03-15
------------------
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージエントリポイントを追加
    - src/kabusys/__init__.py: __version__ = "0.1.0", __all__ に主要モジュールを公開 (data, strategy, execution, monitoring)。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
      - プロジェクトルートの検出ロジック: 現在のファイル位置から上位ディレクトリを探索し、.git または pyproject.toml を基準にルートを特定（CWD に依存しない実装）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途を想定）。
      - .env パーサ:
        - export KEY=val 形式に対応
        - シングル/ダブルクォートされた値をバックスラッシュエスケープを考慮して解析
        - クォートなし時のインラインコメント判定は、「# の直前がスペースまたはタブ」の場合のみコメントとみなす
        - 無効行やコメント行はスキップ
      - ファイル読み込み失敗時には警告を出力
    - Settings クラスでアプリ設定を提供（プロパティ経由で環境変数にアクセス）
      - 必須設定を取得する _require() を実装し、未設定時は ValueError を送出
      - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供
      - デフォルト値:
        - KABUSYS_ENV: "development"
        - KABUSYS_API_BASE_URL: "http://localhost:18080/kabusapi"
        - DUCKDB_PATH: "data/kabusys.duckdb"
        - SQLITE_PATH: "data/monitoring.db"
      - KABUSYS_ENV の許容値検証 (development, paper_trading, live) とログレベルの検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev のヘルパープロパティ

- J-Quants API クライアント（データ取得・保存）
  - src/kabusys/data/jquants_client.py
    - 目的: J-Quants API から株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
    - 設計上の特徴:
      - レート制限の遵守: 固定間隔スロットリング _RateLimiter（デフォルト 120 req/min -> 最小間隔 0.5s）
      - リトライロジック: 指数バックオフ（base=2.0 秒）、最大リトライ回数 3 回。リトライ対象は 408, 429 および 5xx 系。
      - 401 Unauthorized を受け取った場合はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ（無限再帰回避のため allow_refresh フラグあり）。
      - id_token のモジュールレベルキャッシュによるページネーション間での共有
      - JSON デコードエラーやネットワークエラー時に適切に例外化・ログ出力
    - 公開関数:
      - get_id_token(refresh_token: Optional[str]) -> str: refresh_token から id_token を取得
      - fetch_daily_quotes(...): 日足データをページネーション対応で取得
      - fetch_financial_statements(...): 財務データをページネーション対応で取得
      - fetch_market_calendar(...): JPX マーケットカレンダーを取得
    - DuckDB への保存関数（冪等）
      - save_daily_quotes(conn, records) / save_financial_statements(conn, records) / save_market_calendar(conn, records)
      - INSERT ... ON CONFLICT DO UPDATE を使った冪等的な保存（重複上書き）
      - fetched_at を UTC の ISO8601 (Z付き) で記録し、Look-ahead Bias を防止できるように取得タイミングをトレース
      - PK 欠損行はスキップし、その件数を警告ログ出力
    - データ変換ユーティリティ:
      - _to_float / _to_int: 安全な数値変換（空値は None、"1.0" のような小数表現は int 変換を慎重に扱う）

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - DataPlatform に基づく 3+ 層（Raw / Processed / Feature / Execution）のテーブル群を定義
    - 主なテーブル:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - インデックスを多数定義（銘柄×日付検索、ステータス検索、外部キー結合最適化など）
    - init_schema(db_path) 関数:
      - 指定 DB を初期化して全テーブル・インデックスを作成（冪等）
      - db_path の親ディレクトリがなければ自動作成。":memory:" に対応
    - get_connection(db_path) 関数: 既存 DB 接続を返す（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール
  - src/kabusys/data/audit.py
    - シグナル→発注→約定の監査チェーンを保存する専用テーブルを定義
    - 主なテーブル:
      - signal_events: 戦略が生成したすべてのシグナル（棄却されたものも含む）
      - order_requests: 発注要求（order_request_id を冪等キーとして利用）。order_type ごとの price チェックなどの制約を組み込み
      - executions: 実際の約定ログ（broker_execution_id をユニーク／冪等キー扱い）
    - ステータスやチェック制約、FOREIGN KEY、INDEX を多数定義してクエリ効率と整合性を確保
    - init_audit_schema(conn) 関数:
      - 既存の DuckDB 接続に監査テーブルを追加（冪等）
      - 実行時に SET TimeZone='UTC' を実行し、TIMESTAMP を UTC 保存する方針を明記
    - init_audit_db(db_path) 関数: 監査専用 DB を作成して接続を返す（親ディレクトリ自動作成、":memory:" 対応）

- パッケージ構成
  - 空のパッケージ初期化子を追加（strategy, execution, monitoring, data パッケージの __init__.py）により今後の拡張を容易化

Notes / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から必須取得（未設定時は ValueError）。
- 自動 .env 読み込み:
  - プロジェクトルートが検出できない場合は自動読み込みをスキップする（配布後の動作を安全にするため）。
- DuckDB 初期化:
  - 初回は data.schema.init_schema(db_path) を使用してスキーマを作成してください。既存 DB には get_connection() を利用。
- 監査ログの時刻管理:
  - 監査テーブルは UTC 保存を前提とし、init_audit_schema は接続で TimeZone='UTC' を設定します。
- API 利用時のレート制限:
  - J-Quants API は 120 req/min を想定した実装になっており、クライアントは内部でスロットリング・リトライを行いますが、外部からもリクエスト頻度には注意してください。

Breaking Changes
- なし（初回リリース）

Security
- なし（変更履歴に記載すべきセキュリティ修正はなし）

References
- コード内ドキュメント（各モジュールの docstring）に設計原則・仕様を記載しています。README / DataPlatform.md / DataSchema.md 等の上位ドキュメントを合わせて参照してください。