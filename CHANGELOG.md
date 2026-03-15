CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
リリースはセマンティックバージョニングに従います。

[0.1.0] - 2026-03-15
-------------------

初期リリース。

Added
- パッケージ初期化
  - kabusys.__init__ にバージョン (0.1.0) と公開サブパッケージ (data, strategy, execution, monitoring) を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点にルートを特定し、CWD に依存しない探索を実現。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS 環境変数を保護するため、既存の OS 環境変数はデフォルトで上書きされない挙動を採用。
  - .env パーサーの強化:
    - 空行・コメント行を無視。
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォート付き値のバックスラッシュエスケープ処理をサポート（インラインコメント無視）。
    - クォートなし値の行末コメント判定は直前が空白またはタブの場合にのみコメント扱い。
  - Settings クラスを提供し、アプリ用設定をプロパティ経由で取得可能:
    - 必須変数の取得時は未設定で ValueError を送出する _require を採用。
    - J-Quants / kabuステーション / Slack / データベース（DuckDB/SQLite）などの設定をプロパティ化。
    - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証、is_live/is_paper/is_dev のユーティリティを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 対応データ:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 設計上の特徴（実装済み）:
    - API レート制限対応: 固定間隔スロットリング実装（120 req/min、_RateLimiter）。
    - リトライ: 指数バックオフ（ベース 2.0 秒）、最大 3 回、408/429/5xx を対象。
    - 401 応答時はトークン自動リフレッシュを 1 回行いリトライ（無限再帰を回避）。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - id_token キャッシュをモジュールレベルで共有（ページネーション中のトークン再利用）。
    - 取得時刻（fetched_at）を UTC の ISO8601 形式で記録し Look-ahead Bias を防止。
    - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）を採用。
  - 公開 API:
    - get_id_token(refresh_token: str | None) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - データ変換ユーティリティ:
    - _to_float/_to_int: 無効値・空値・フォーマット異常を安全に扱う。float から int 変換時に小数部が残る場合は None を返すなどの保護あり。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル定義を実装。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けのインデックス群を定義して初期化時に作成。
  - init_schema(db_path) 関数:
    - DuckDB ファイル作成時に親ディレクトリを自動生成。
    - すべての DDL とインデックスを実行して接続を返す（冪等）。
  - get_connection(db_path) 関数: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - 監査用テーブル群と初期化ロジックを実装:
    - signal_events: 戦略が生成したシグナルログ（棄却やエラーも含む）
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして扱う）
    - executions: 証券会社からの約定ログ（broker_execution_id をユニークな冪等キーとして扱う）
  - テーブル制約、ステータス遷移、発注種別ごとのチェック制約を実装。
  - 監査向けインデックス群を作成。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。
  - 監査タイムスタンプは UTC に固定（init_audit_schema 内で SET TimeZone='UTC' を実行）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 現時点で機密情報（トークン）は環境変数経由で取得する設計。自動 .env ロード時にも OS 環境変数は保護され、意図しない上書きを防止する仕組みを導入。

Notes / 補足
- DuckDB に保存する際、PK 欠損行はスキップして警告ログを出力する挙動を採用（save_* 関数）。
- J-Quants クライアントは urllib を用いた同期実装。大規模取得時はレートリミットとリトライにより実行時間がかかることに注意。
- 現在 strategy、execution、monitoring の各パッケージは初期プレースホルダを含む構成。今後のリリースで戦略ロジック・発注連携・監視機能の実装を予定。

作者
- 初期実装

ライセンス
- リポジトリに従う（ソース内に明示があればそれに従ってください）。

---