# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
タグ付けはセマンティックバージョニングを使用します。

※ 初期リリース（0.1.0）はソースコードから推測した機能・設計方針に基づいて記載しています。

## [Unreleased]


## [0.1.0] - 2026-03-15

### Added
- パッケージ基本情報
  - パッケージ名: KabuSys（日本株自動売買システム）
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート

- 環境設定 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装
  - プロジェクトルート検出: __file__ を基点に親ディレクトリを探索し `.git` または `pyproject.toml` で判定（配布後も動作する実装）
  - .env パーサー: コメント（#）、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いをサポートする堅牢なパーシング実装
  - .env ファイル読み込みロジック:
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - override フラグと protected（既存 OS 環境変数を保護する仕組み）を実装
    - 自動ロード無効化のための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須設定の検証を行う _require() を提供（未設定時は ValueError を発生）
  - 提供される設定項目（プロパティ）:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev ブールプロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 機能:
    - 株価日足（OHLCV）の取得（ページネーション対応）
    - 財務データ（四半期 BS/PL）の取得（ページネーション対応）
    - JPX マーケットカレンダーの取得
  - 設計方針の実装:
    - レート制限: 固定間隔スロットリングにより 120 req/min を遵守（_RateLimiter）
    - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429 および 5xx。429 の場合は Retry-After を優先
    - 認証トークン管理:
      - refresh token から id token を取得する get_id_token（POST）
      - モジュールレベルで id token をキャッシュしページネーション間で共有（_ID_TOKEN_CACHE）
      - 401 受信時は一度だけ自動でトークンをリフレッシュして再試行（無限再帰を回避）
    - エラー時の詳細ログ/例外処理（JSON デコード失敗等でわかりやすいメッセージ）
    - 取得日時（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - データ保存ユーティリティ:
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes: raw_prices テーブルに保存（ON CONFLICT DO UPDATE）
      - save_financial_statements: raw_financials テーブルに保存（ON CONFLICT DO UPDATE）
      - save_market_calendar: market_calendar テーブルに保存（ON CONFLICT DO UPDATE）
    - PK 欠損行のスキップとログ出力
    - 型変換ユーティリティ: _to_float / _to_int（厳密な変換ルール、空値や不正値は None に）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 「3 層アーキテクチャ」に基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェックや制約（PRIMARY KEY, CHECK 等）を付与
  - パフォーマンスを考慮したインデックスの定義（銘柄×日付検索やステータス検索等）
  - init_schema(db_path) を提供:
    - DB ファイルの親ディレクトリを自動作成
    - すべての DDL とインデックスを実行（冪等）
    - ":memory:" によるインメモリ DB 対応
  - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - 監査テーブル群の定義（戦略 → シグナル → 発注要求 → 約定 の一貫トレースを想定）
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う）
    - executions（約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
  - テーブル設計の特徴:
    - すべてのテーブルに created_at を付与、updated_at はアプリ側で current_timestamp を設定して更新
    - FK は ON DELETE RESTRICT（監査ログは削除しない前提）
    - 注文種別ごとの CHECK 制約（limit/stop/market に応じた price 条件）
    - ステータス遷移の列挙（pending, sent, filled, ...）
    - タイムゾーン強制: init_audit_schema() 実行時に SET TimeZone='UTC' を行う
  - インデックス定義: 日付/銘柄検索、戦略別検索、status ベースのキュー検索、broker_order_id 検索等
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加初期化 or 専用 DB 初期化）

- 形的なモジュール構成
  - src/kabusys/data, src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring などのパッケージ構造を準備（空の __init__.py を含む）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- J-Quants の id token はモジュール内でキャッシュされ、必要に応じてのみ refresh する仕組みを実装。自動リフレッシュは 1 回に制限して無限再帰を回避。

### Notes / 実装上の注意
- DuckDB のテーブル定義や制約に依存した動作を前提としているため、初回使用時は schema.init_schema()（および監査用なら init_audit_schema()）を必ず実行してください。
- .env の自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限とリトライ方針はライブラリ内で制御されますが、上位アプリケーションでの並列リクエスト等には注意してください（グローバルなレートリミッタを共有する設計になっています）。
- save_* 系関数は DuckDB の接続オブジェクトを受け取るため、トランザクションや接続管理は呼び出し側で行う想定です。

---

開発・運用中に追加の変更が発生した場合は、この CHANGELOG を更新してください。