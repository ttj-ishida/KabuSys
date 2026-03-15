# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従います。  
現在のリリース情報は下記の通りです。

## [0.1.0] - 2026-03-15
初回リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py に定義）
  - エクスポート対象モジュール: data, strategy, execution, monitoring（将来的な拡張のためのサブパッケージを含む空の __init__ を用意）

- 環境変数 / 設定管理（src/kabusys/config.py）
  - Settings クラスを追加し、アプリケーション設定を環境変数から取得する統一 API を提供（settings インスタンスを公開）。
  - サポートする設定例:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live。デフォルト: development）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
  - Settings に利便性プロパティを追加:
    - is_live, is_paper, is_dev（環境判定用ブール）
  - 環境変数が未設定の場合は _require 関数が ValueError を送出する挙動を定義（必須変数の明示的チェック）。

- .env ファイル自動読み込み機能
  - プロジェクトルート検出: カレントワークディレクトリに依存せず、実ファイル位置（__file__）から親ディレクトリを辿って .git または pyproject.toml を探す実装（_find_project_root）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書きする）。
  - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを抑止可能（テスト時等の用途を想定）。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォートありの場合はコメント無視、クォートなしは '#' が直前スペース/タブのときコメント扱い）など堅牢なパース処理を実装（_parse_env_line）。
  - .env 読み込み時の保護機能: OS 環境変数のキーセットを protected として扱い、必要に応じて上書きを防止。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - データレイヤー設計に基づくテーブル定義を追加（Raw / Processed / Feature / Execution の 4 層）。
  - 主なテーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型・CHECK 制約・PRIMARY KEY を設計:
    - 価格関連カラムに対する非負チェック、orders/trades/position に対するサイズ/価格の整合性チェック、signals/signal_queue/orders における side/order_type/status の列挙チェックなどを含む。
    - news_symbols における外部キー（news_articles）や orders/trades の外部キー制約も定義。
  - インデックス定義を追加（頻出クエリパターンに最適化）:
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status, idx_news_symbols_code 等
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスの DuckDB を初期化して全テーブル・インデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定してインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用すること）。

- ドキュメント参照
  - schema モジュール内から DataSchema.md を参照する旨の記載（設計ドキュメントへの参照）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- （初回リリースのため該当なし）

### 既知の注意点 / 移行メモ
- Settings の必須項目が未設定の場合は起動時に ValueError が発生します。運用前に .env（または OS 環境）を正しく設定してください。.env.example を参照することを推奨します。
- 自動 .env ロードをテスト環境等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- init_schema は初回のスキーマ作成を行いますが、既存 DB に対するスキーマ変更（マイグレーション）機能は現状含まれていません。将来的にマイグレーション機構を追加予定です。
- strategy, execution, monitoring サブパッケージはプレースホルダとして存在します。実ロジックは今後追加予定です。

---

（変更ログは今後のリリースで逐次更新してください）