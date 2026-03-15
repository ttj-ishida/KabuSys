# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

最新更新日: 2026-03-15

## [Unreleased]
- なし

## [0.1.0] - 2026-03-15
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。パッケージ公開の初期バージョン。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートの検出ロジック（.git または pyproject.toml を探索）に基づく自動 .env / .env.local 読み込み。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env.local は .env を上書き（override）して読み込む実装。
    - OS 環境変数を保護するための protected keys 処理を実装。
  - .env のパーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応）。
  - 必須環境変数チェック用の _require 関数を提供（未設定時は ValueError を送出）。
  - Settings プロパティ:
    - J-Quants / kabuステーション / Slack トークン類（必須）
    - DB パスのデフォルト（DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db）
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）
    - is_live / is_paper / is_dev などのヘルパープロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得を行うクライアントを実装。
  - サポートするエンドポイント:
    - 株価日足（/prices/daily_quotes）: fetch_daily_quotes()
    - 財務データ（/fins/statements）: fetch_financial_statements()
    - JPX マーケットカレンダー（/markets/trading_calendar）: fetch_market_calendar()
  - 認証:
    - リフレッシュトークンから ID トークンを取得する get_id_token() を実装。
    - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有する設計。
    - 401 受信時は自動でトークンをリフレッシュして 1 回リトライする。
  - ネットワーク/HTTP 耐性:
    - 固定間隔スロットリング（120 req/min）を守る RateLimiter 実装。
    - 指数バックオフを用いたリトライロジック（最大 3 回、対象: 408/429/5xx）。429 の場合は Retry-After を優先。
    - JSON デコード失敗やネットワークエラーに対する明確な例外とログ記録。
  - Look-ahead bias 対策:
    - 取得タイミングを fetched_at（UTC）として記録する考え方を反映した保存ロジックを提供。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes(conn, records): raw_prices テーブルへ ON CONFLICT DO UPDATE による上書き挿入。
    - save_financial_statements(conn, records): raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar(conn, records): market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - PK 欠損行はスキップし、スキップ件数はログ出力。
  - 型変換ユーティリティ:
    - _to_float(), _to_int() による安全な変換。_to_int は "1.0" のような文字列を許容、非整数の小数は None を返す設計。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー: features, ai_scores
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型、CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義。
  - パフォーマンスを考慮したインデックス定義を複数追加（銘柄×日付検索、ステータス検索など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成、DDL/インデックス実行を行い、初期化済みの接続を返す。
  - get_connection(db_path) により既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 戦略→シグナル→発注→約定のトレーサビリティを担保する監査テーブル群を実装。
  - トレーサビリティ階層（business_date / strategy_id / signal_id / order_request_id / broker_order_id）を前提とした設計。
  - テーブル:
    - signal_events: 戦略が生成したすべてのシグナルを記録（棄却・エラー含む）。
    - order_requests: 発注要求（order_request_id を冪等キーとして扱う）。order_type に応じた CHECK 制約（limit/stop/market）を実装。
    - executions: 証券会社からの約定情報。broker_execution_id を一意（冪等キー）として扱う。
  - すべての TIMESTAMP を UTC 保存とし、init_audit_schema(conn) / init_audit_db(db_path) API を提供。
  - インデックスを多数追加し、日付/銘柄検索・ステータスキュー処理・broker_order_id 紐付け・JOIN 最適化を考慮。

- パッケージ構成
  - src/kabusys 以下に data, strategy, execution, monitoring のモジュール階層を準備（初期プレースホルダとして __init__.py を配置）。

### Docs / コメント
- 各モジュールに設計原則や注意点を記載したドキュメント文字列（Look-ahead bias、冪等性、UTC タイムスタンプ等）を追加。

### Other
- ロギング（logger）を各所で利用し、重要イベント（取得件数、保存件数、リトライや 401 リフレッシュなど）を出力するよう実装。

### Known limitations / Notes
- strategy/ execution / monitoring の実装は雛形（パッケージ初期化ファイル）までで、具体的な戦略ロジックや注文送信処理は含まれていない。
- J-Quants API の呼び出しは urllib を使用しており、高度な HTTP クライアント（例: requests）を想定する場合は拡張の余地がある。
- DB 初期化関数は DuckDB 固有の DDL を多用しているため、他 DB への移植には変更が必要。

---

（今後のリリースでは、strategy の具体実装、kabu ステーションとの発注統合、モニタリング/アラート機能、より詳細なテストカバレッジや CI/CD の導入等を予定しています。）