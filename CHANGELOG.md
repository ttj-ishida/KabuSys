# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

全ての非互換性のある変更は「Breaking Changes」に明記します。

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムのコア基盤を実装しています。

### 追加 (Added)
- パッケージの公開エントリポイントを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に ["data", "strategy", "execution", "monitoring"] を定義

- 環境変数・設定管理モジュール (kabusys.config)
  - Settings クラスを追加し、アプリケーション設定を環境変数から取得可能に
    - 必須設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意設定: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
    - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを検証
    - LOG_LEVEL は標準のログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL") を検証
    - is_live / is_paper / is_dev のユーティリティプロパティを提供
  - .env 自動読み込み機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートを .git または pyproject.toml を基準に探索（__file__ から親ディレクトリを探索）
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env 読み込み時に OS 環境変数を保護（既存キーは上書きされない、.env.local は override=True だが protected により OS 環境は保護）
  - 強力な .env パーサ実装
    - コメント行・空行をスキップ
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォートなし値のインラインコメント認識（直前が空白／タブの場合に '#' をコメントとして扱う）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API から株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する機能を実装
  - 設計上の特徴:
    - レート制限対応: 固定間隔スロットリングで 120 req/min を厳守（RateLimiter 実装）
    - 再試行 (Retry) ロジック: 指数バックオフ、最大 3 回、対象ステータスコードに対してリトライ（408, 429, 5xx 等）
    - 401 Unauthorized を検知した場合はリフレッシュトークンで自動的に ID トークンを再取得して 1 回再試行
    - ページネーション対応（pagination_key を利用して全件取得）
    - 取得時刻（fetched_at）を UTC タイムスタンプで記録し、Look-ahead bias のトレースを可能に
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）
  - HTTP ユーティリティ: _request 関数で JSON レスポンスを返す（タイムアウト、デコードエラー検出）
  - データ取得関数:
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB へ保存する冪等性のある保存関数:
    - save_daily_quotes(conn, records): raw_prices テーブルに ON CONFLICT DO UPDATE で保存
    - save_financial_statements(conn, records): raw_financials テーブルに ON CONFLICT DO UPDATE で保存
    - save_market_calendar(conn, records): market_calendar テーブルに ON CONFLICT DO UPDATE で保存
  - 型変換ユーティリティ:
    - _to_float(): 空値・変換失敗時は None
    - _to_int(): float 文字列 ("1.0") を int に変換可能だが、小数部がある場合は None を返す（意図しない切り捨て防止）

- DuckDB スキーマ定義 & 初期化 (kabusys.data.schema)
  - DataLayer に沿ったスキーマを定義（Raw / Processed / Feature / Execution）
  - テーブル群（主なもの）:
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（NOT NULL, CHECK, PRIMARY KEY 等）を幅広く定義してデータ整合性を担保
  - 頻出クエリ向けにインデックスを多数定義（例: prices_daily(code, date)、signal_queue(status) 等）
  - 公開 API:
    - init_schema(db_path): DB を初期化して全テーブル・インデックスを作成、DuckDB 接続を返す（親ディレクトリ自動作成、:memory: サポート）
    - get_connection(db_path): 既存 DB 接続を返す（初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - 戦略から約定までの完全なトレーサビリティを想定した監査テーブルを定義
  - テーブル群:
    - signal_events: 戦略が生成した全シグナルを記録（棄却も含む）
    - order_requests: 発注要求（order_request_id を冪等キーとして利用）、価格チェック制約、status 列等
    - executions: 証券会社からの約定ログ（broker_execution_id をユニークな冪等キーとして管理）
  - 監査向けのインデックスを定義（status スキャン、signal_id 連携、broker_order_id 紐付け等）
  - UTC タイムゾーン強制（init_audit_schema で SET TimeZone='UTC' を実行）
  - 公開 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（冪等）
    - init_audit_db(db_path): 監査専用 DB を初期化して接続を返す

- パッケージのモジュール骨格を追加
  - kabusys.execution, kabusys.strategy, kabusys.data, kabusys.monitoring の __init__.py（将来の拡張用）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制限 / 注意事項 (Known Issues / Notes)
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後も安全）
- get_id_token は settings.jquants_refresh_token を用いる前提。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境を制御すること
- 一部のモジュール（strategy, execution, monitoring）は現時点では実装の骨格のみで、ビジネスロジックは未実装

### 破壊的変更 (Breaking Changes)
- （初回リリースのため該当なし）

---

今後のリリースでは、戦略実装、発注ハンドラ、モニタリング・アラート、CI テスト、ドキュメントの拡充などを予定しています。