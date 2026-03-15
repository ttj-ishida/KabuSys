CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  

[0.1.0] - 2026-03-15
--------------------

初期公開リリース。

### 追加 (Added)

- パッケージ基盤
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - サブパッケージの公開インターフェースを定義: data, strategy, execution, monitoring。

- 設定・環境読み込み (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ の親ディレクトリから探索。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - OS 側に存在する環境変数は protected として .env による上書きを防止。
  - .env パーサ実装:
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォートを考慮した値の解析（バックスラッシュエスケープ考慮）。
    - インラインコメント検出のルール（クォート有無で挙動を分離）。
  - Settings クラスを提供（settings インスタンスで利用）:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH を設定。
    - KABUSYS_ENV 値検証（development, paper_trading, live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアント実装:
    - 株価日足（OHLCV）取得: fetch_daily_quotes()
    - 財務データ（四半期 BS/PL）取得: fetch_financial_statements()
    - JPX マーケットカレンダー取得: fetch_market_calendar()
  - 認証/トークン:
    - refresh_token から id_token を取得する get_id_token()（POST）。
    - モジュールレベルの id_token キャッシュを保持し、ページネーション間で共有。
    - 401 受信時に自動で 1 回トークンをリフレッシュしてリトライ（無限再帰防止）。
  - レート制御とリトライ:
    - 固定間隔スロットリングでリクエスト間隔を制御（120 req/min を想定）。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象: ネットワークエラー、408/429/5xx。
    - 429 の場合は Retry-After ヘッダを優先。
  - ページネーション対応: pagination_key を用いた繰り返し取得。重複キー検出でループ終了。
  - 取得ログ（logger.info）を出力。

- DuckDB への永続化・スキーマ連携 (src/kabusys/data/jquants_client.py, src/kabusys/data/schema.py)
  - DuckDB に対する保存関数実装:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装し重複を排除。
    - PK 欠損行はスキップし、スキップ件数を警告ログで出力。
    - fetched_at を UTC の ISO タイムスタンプで記録し、Look-ahead バイアス防止を想定。
    - 値変換ユーティリティ _to_float(), _to_int() を実装（安全な数値パース、丸め回避の挙動を明示）。
  - DuckDB スキーマ定義モジュール (data/schema.py):
    - 3 層構造に基づくテーブル定義（Raw / Processed / Feature / Execution）。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions。
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
    - Feature レイヤー: features, ai_scores。
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
    - 各テーブルに適切な型チェック制約（NOT NULL、CHECK、PK、FK）を付与。
    - クエリパターンを想定したインデックス群を定義。
    - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成→全 DDL とインデックスを実行。冪等。
    - get_connection(db_path) を提供（初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 監査用スキーマを定義:
    - signal_events（シグナル生成ログ）、order_requests（発注要求、冪等キー order_request_id）、executions（約定ログ）。
    - 各テーブルに created_at / updated_at 等のタイムスタンプを保持。UTC での保存を想定。
    - order_requests における注文タイプ別チェック（limit/stop/market の必須/排他ルール）。
    - executions に broker_execution_id のユニーク制約を付与（証券会社側の冪等キー）。
  - インデックスを多数定義（状態検索・JOIN・日付/銘柄検索を高速化）。
  - init_audit_schema(conn) で既存接続に監査テーブルを追加（SET TimeZone='UTC' を実行）。
  - init_audit_db(db_path) で監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成）。冪等。

- ロギング・エラーハンドリング
  - 重要な操作に対して logger.warning / logger.info を挿入。
  - ネットワーク・HTTP エラー時は詳細な例外や警告を出力し、適切に再試行。

### 変更点 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 初回リリースのため該当なし。

### 破壊的変更 (Breaking Changes)

- 初回リリースのため該当なし。

### セキュリティ (Security)

- 初回リリースのため該当なし。

補足
----
- このリリースは "初期実装" を目的とし、J-Quants API 統合、データ永続化、監査トレーサビリティの主要コンポーネントをカバーしています。
- strategy, execution, monitoring パッケージは初期モジュールプレースホルダとして存在します。これらは将来的に戦略ロジック、発注エンジン、監視機能を実装するための拡張ポイントです。
- マイグレーションやスキーマ変更は init_schema / init_audit_schema が冪等にテーブルを作成する設計のため、既存 DB へは安全に適用可能ですが、将来的なスキーマ変更時はバックアップを推奨します。