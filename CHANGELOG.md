# Changelog

すべての notable な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

## [0.1.0] - 初回リリース
最初の公開リリース。以下のコア機能を実装しました。

### 追加
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0（__version__ を定義）。

- 環境設定・ロード（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - ロード優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き防止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等で利用）。
  - .env パーサを実装（export 形式、クォートやエスケープ、インラインコメントの扱いに対応）。
  - 必須キー取得のヘルパー (_require) と環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL 検証）。
  - 主要プロパティを用意：J-Quants リフレッシュトークン、kabu API パスワード/ベース URL、Slack トークン/チャンネル、DB パス等。
  - 環境判別ユーティリティ（is_live/is_paper/is_dev）。

- データ取得クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter 実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータスに対応（408/429/5xx 等）。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン管理: キャッシュされた ID トークンの共有（ページネーション間）、401 受信時にはトークン自動リフレッシュを 1 回行って再試行。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes: 日足（OHLCV）取得（pagination_key ハンドリング）
    - fetch_financial_statements: 四半期財務データ取得（pagination_key ハンドリング）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - JSON デコード失敗時の詳細エラーハンドリング、タイムアウト等のネットワークエラー対処。
  - DuckDB への保存関数（冪等に保存）:
    - save_daily_quotes: raw_prices テーブルへの保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials テーブルへの保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar テーブルへの保存（ON CONFLICT DO UPDATE）
  - 取得時刻（fetched_at）を UTC ISO 形式で保存して Look-ahead バイアスの管理を容易に。
  - PK 欠損行のスキップとログ警告（何件スキップしたかを出力）。
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換、空値や不正値は None）。

- データスキーマ（DuckDB）定義と初期化（src/kabusys/data/schema.py）
  - DataLayer に基づく一連のテーブル DDL を定義（Raw / Processed / Feature / Execution レイヤー）。
  - 生データ用テーブル: raw_prices, raw_financials, raw_news, raw_executions。
  - 整形済み市場データ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - 特徴量層: features, ai_scores。
  - 実行層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各種制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を定義してデータ整合性を担保。
  - 頻出クエリ向けのインデックスを複数定義（銘柄×日付、ステータス検索、JOIN 支援など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成・テーブル作成を行う（冪等）。
  - get_connection(db_path) により既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - Signal → Order → Execution に至る監査テーブルを実装（signal_events, order_requests, executions）。
  - トレーサビリティ設計（UUID 連鎖、order_request_id を冪等キーとして利用）。
  - order_requests に対する厳密な CHECK（limit/stop/market の価格要件）、ステータス遷移の定義（pending/sent/filled/...）。
  - executions テーブルに broker_execution_id の一意性（冪等性）を導入。
  - すべての TIMESTAMP を UTC で保存するために init_audit_schema() で SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供し、既存接続への追加初期化や専用 DB の初期化をサポート。
  - 監査用のインデックス定義（signal 日付/銘柄検索、status スキャン、broker_order_id 紐付け等）。

- その他
  - strategy, execution, monitoring のパッケージ初期化ファイル（空の __init__.py）を追加し、将来の拡張に備える。
  - モジュール内に豊富なドキュメンテーション文字列を追加（設計原則、使用上の注意、データ設計意図など）。

### 変更
- —（初回リリースのため変更はありません）

### 修正
- —（初回リリースのため修正はありません）

### 注意事項 / マイグレーション
- DuckDB スキーマ作成は冪等です。既存 DB に対して init_schema / init_audit_schema を安全に実行できますが、DDL の変更がある場合は手動でのマイグレーションが必要になる可能性があります。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境等で便利です）。
- J-Quants API のレート制限（120 req/min）とリトライ挙動を実装しています。大量取得の際はレートと課金を考慮してください。

---

今後の予定（例）
- strategy / execution 層の実装（ポートフォリオ構築、リスク管理、発注ロジック）
- 監査ログの追加ユーティリティ（order_request の冪等チェック、履歴参照関数）
- モニタリング・アラート（Slack 通知等）の実装

（この CHANGELOG はコードから推測して作成しています。実際のリリースノート作成時は差分やコミットログを参照して追記・修正してください。）