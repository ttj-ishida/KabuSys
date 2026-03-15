CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に基づきます。

[Unreleased]
-------------

- （現時点のコードベースでは未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

Added
- パッケージ初期リリース。kabusys のコア機能を提供するモジュール群を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にてバージョン "0.1.0" を設定。
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ から親ディレクトリを走査し .git または pyproject.toml を基準に行う（CWD に依存しない）。
    - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env パーサを実装:
    - コメント行・空行スキップ、export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート外での # の扱い）を考慮。
    - ファイル読み込み時の上書き制御（override）と OS 環境変数保護（protected set）をサポート。
    - 読み込み失敗時のワーニング出力。
  - Settings クラスを提供（settings インスタンスを公開）:
    - J-Quants / kabuステーション / Slack / データベースパス など主要設定をプロパティ化。
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）を実装。
    - duckdb/sqlite のデフォルトパスを用意。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しのための汎用 _request 実装（JSON パース、エラーハンドリング）。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - リトライロジックを実装（最大 3 回、指数バックオフ、HTTP 408/429 および 5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先して待機。
  - 401 Unauthorized を検出した場合、リフレッシュトークンから id_token を再取得して 1 回だけリトライする仕組み（無限再帰回避のため allow_refresh フラグを使用）。
  - id_token のモジュールレベルキャッシュを提供し、ページネーション間で共有。
  - API 用の高レベル関数を追加:
    - fetch_daily_quotes (日足 OHLCV、ページネーション対応)
    - fetch_financial_statements (四半期財務、ページネーション対応)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB へ保存するユーティリティを提供（冪等性を重視）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
      - INSERT ... ON CONFLICT DO UPDATE による重複除去（更新上書き）。
      - PK 欠損行はスキップして警告ログを出力。
      - fetched_at を UTC で記録（Look-ahead Bias を抑止するために「取得時刻」を保存）。
  - 型安全な変換ユーティリティ _to_float / _to_int を実装（不正値・空値は None、"1.0" のような float 文字列を許容するが小数部が残る場合は変換しない等）。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform.md に準拠した 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル DDL を提供。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - DDL に加えて使用想定のインデックスを定義（頻出クエリに対する最適化）。
  - init_schema(db_path) を実装:
    - 指定パスの DuckDB を初期化し、すべてのテーブルとインデックスを作成（冪等）。
    - ":memory:" のサポート、ファイルパス指定時は親ディレクトリを自動作成。
  - get_connection(db_path) を実装（既存 DB への接続取得、スキーマ初期化は行わない旨を明記）。
- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 戦略→シグナル→発注要求→約定 までの監査テーブル群を実装:
    - signal_events（シグナル生成ログ、棄却やエラーも記録）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして扱う）
  - init_audit_schema(conn) / init_audit_db(db_path) を実装:
    - 既存の DuckDB 接続に監査テーブルを追加（冪等）。
    - タイムゾーンを UTC に固定（SET TimeZone='UTC'）。
    - インデックス群を定義（日付・銘柄検索、status スキャン、broker_order_id 紐付け等）。
  - テーブル定義に多くの整合性制約（CHECK、FOREIGN KEY、ON DELETE RESTRICT など）を含め、ログは削除しない設計。
- モジュールの雛形
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的な機能追加のためのプレースホルダ）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- シークレットは環境変数経由で取得する設計（.env の自動読み込みはあるが OS 環境変数を保護するため上書き制御を導入）。

Notes / Implementation details
- J-Quants API クライアントはレート制限・リトライ・トークンリフレッシュを考慮した堅牢な設計を目標としていますが、実運用前に実際の API レスポンス・エラーレスポンスでの検証を推奨します。
- DuckDB スキーマは冪等に作成されるため、既存 DB に対して安全に初期化を呼ぶことができます。監査ログは削除しない方針のため、マイグレーション時は注意してください。
- .env パーサは多くのケースに対応していますが、特殊な .env フォーマット（複数行クォートなど）では期待通りに動作しない可能性があります。

Breaking Changes
- 初回リリースのため該当なし。