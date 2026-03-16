# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に従っています。  
比較的初期のリリースのため、主に機能追加を記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名: KabuSys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（カレントワーキングディレクトリに依存しない）。
    - 自動ロード無効化のための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env の上書きを防止（.env.local はオーバーライド可能）。
  - .env パーサーの実装（コメント行、export 先頭、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
  - Settings クラスを提供。主要な設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース URL と API 呼び出しユーティリティを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min（内部 RateLimiter）。
  - リトライロジック:
    - 最大リトライ回数 3 回、指数バックオフ、対象ステータス: 408/429/5xx、ネットワークエラーもリトライ。
    - 429 の場合は Retry-After ヘッダを優先して待機。
  - 認証トークン管理:
    - refresh token から id_token を取得する get_id_token()。
    - モジュールレベルで id_token をキャッシュ、401 受信時に自動リフレッシュして 1 回リトライ。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足：OHLCV）
    - fetch_financial_statements（財務データ：四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - データ保存関数（DuckDB 用、冪等性を考慮）:
    - save_daily_quotes → raw_prices テーブルに ON CONFLICT DO UPDATE で保存。fetched_at を UTC で記録（Look-ahead Bias 対策）。
    - save_financial_statements → raw_financials に保存（ON CONFLICT）。
    - save_market_calendar → market_calendar に保存（ON CONFLICT）。
  - データ変換ヘルパー: _to_float, _to_int（堅牢な型変換ロジック）

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層＋実行層のスキーマ定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) による冪等的な初期化関数を実装。親ディレクトリを自動作成。
  - get_connection(db_path) で既存 DB への接続を取得可能（スキーマ初期化は行わない旨を明示）。

- 監査ログ・トレーサビリティ (kabusys.data.audit)
  - シグナルから約定に至る監査テーブル群を実装（signal_events, order_requests, executions）。
  - トレーサビリティ階層と設計原則をドキュメント化（order_request_id を冪等キーとして利用等）。
  - すべての TIMESTAMP を UTC で保存する設計（init_audit_schema 時に SET TimeZone='UTC'）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。
  - 監査用インデックスを作成（ステータス検索・signal_id 連携・broker_order_id など）。

- データ品質チェックモジュール (kabusys.data.quality)
  - DataPlatform.md に基づく品質チェック実装:
    - 欠損データ検出: check_missing_data（raw_prices の OHLC 欠損検出）
    - 異常値検出: check_spike（前日比スパイク検出、デフォルト閾値 50%）
    - 重複チェック: check_duplicates（主キー重複: date, code）
    - 日付不整合検出: check_date_consistency（未来日付・market_calendar と矛盾するデータ）
    - run_all_checks で一括実行し、QualityIssue のリストを返す（error/warning を含む）
  - QualityIssue データクラスを定義し、詳細サンプル（最大 10 件）を返す設計。
  - SQL バインドパラメータを使用して注入リスクを軽減。

- パッケージ構成
  - 空のパッケージ初期化子を追加: kabusys.__init__（__version__ = "0.1.0"、__all__ 定義）
  - 空のサブパッケージプレースホルダ: kabusys.execution.__init__, kabusys.strategy.__init__, kabusys.data.__init__, kabusys.monitoring.__init__（将来の実装用スタブ）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制約 / 注意事項
- strategy および execution、monitoring パッケージは現状プレースホルダ（実装は今後追加予定）。
- DuckDB スキーマや監査テーブルは初期化時に既存のテーブルがある場合はスキップされる（冪等）。
- get_connection() はスキーマ初期化を行わないため、初回は init_schema() / init_audit_schema() を使用すること。
- J-Quants クライアントの HTTP 実行は urllib を使用しており、タイムアウトやエラーハンドリングは実装済みだが、実際の運用では接続や認可周りの追加監視が推奨される。

---

（次のリリースでは strategy・execution の実装、監視/通知の強化、運用テレメトリ追加などを予定）