# Changelog

すべての注目すべき変更履歴はここに記録します。  
このファイルは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のフォーマットに準拠します。

※ 本リリースはソースコードから推測して作成しています。実装の詳細や設計意図に基づく注記を含みます。

## [0.1.0] - 2026-03-15

### 追加
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)
  - パッケージ初期化: src/kabusys/__init__.py にてバージョンと公開モジュール (data, strategy, execution, monitoring) を定義。

- 環境設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む機能を提供。
  - 自動読み込み:
    - プロジェクトルートは __file__ を起点に上位ディレクトリから .git または pyproject.toml を探索して特定。プロジェクトルートが見つからない場合は自動読み込みをスキップ。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能（テスト用途想定）。
  - .env パーサ:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートで囲まれた値のエスケープ (\) に対応し、対応する閉じクォートまでを正しく取り扱う。
    - クォート無しの場合、インラインコメントの判定ルール（直前がスペース/タブなら '#' をコメント開始と扱う）を実装。
  - .env 読み込み:
    - override 引数により既存の環境変数を上書きする/しないを制御。protected 引数で上書きを禁止するキーセット（OS 環境変数の保護）を指定可能。
    - ファイル読み込み失敗時は警告を出して処理を継続。
  - Settings クラス:
    - アプリケーション設定のプロパティを提供。必須値取得時に未設定なら ValueError を送出する _require() を採用。
    - 用意されたプロパティ（例）:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
      - kabu_api_password (KABU_API_PASSWORD 必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token, slack_channel_id (必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV: 値検証。許容値: development, paper_trading, live)
      - log_level (LOG_LEVEL: 値検証。許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
      - is_live / is_paper / is_dev の便宜的プロパティ

- DuckDB スキーマ管理モジュールを追加 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（実際には Raw / Processed / Feature / Execution の 4 層表現）スキーマ定義を実装。
  - 定義されている主なテーブル（抜粋）:
    - Raw Layer:
      - raw_prices (date, code, open/high/low/close, volume, turnover, fetched_at)
      - raw_financials (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, fetched_at)
      - raw_news (id, datetime, source, title, content, url, fetched_at)
      - raw_executions (execution_id, order_id, datetime, code, side, price, size, fetched_at)
    - Processed Layer:
      - prices_daily (日次価格)
      - market_calendar (取引日カレンダー)
      - fundamentals (加工済み財務指標)
      - news_articles / news_symbols（ニュースと銘柄紐付け）
    - Feature Layer:
      - features (momentum, volatility, per/pbr 等の特徴量)
      - ai_scores (sentiment/regime/ai_score 等)
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー、FOREIGN KEY、CHECK 制約（例: side は 'buy'/'sell'、サイズは正の整数、価格は >= 0 など）を定義。
  - インデックスを複数定義（銘柄×日付スキャンやステータス検索を想定したもの）。
  - テーブル作成順を依存関係に配慮して管理。

  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスの DuckDB を初期化し、全テーブルとインデックスを作成。既存テーブルはスキップ（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。":memory:" でインメモリ DB をサポート。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用することを想定）。

- モジュール骨組み
  - 空のパッケージ初期化ファイルを追加: src/kabusys/data/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/monitoring/__init__.py（将来的な実装箇所として空のパッケージを用意）。

### 変更
- 該当なし（初回リリースのため）。

### 修正
- 該当なし（初回リリースのため）。

### 既知の注意点（ドキュメント的補足）
- Settings の必須プロパティに未設定でアクセスすると ValueError が発生するため、運用時は .env/.env.local や OS 環境で必要なキーを設定すること。
- .env のパース処理は実用的なルールを実装しているが、極端な入力（途中で閉じクォートが無い等）に対しては期待通りに処理されない可能性があるため、 .env の書式は一般的な形式に従うことを推奨。
- DuckDB スキーマは多くの CHECK 制約や外部キーを含むため、移行や外部ツールからの操作時に制約エラーが発生することがある。スキーマを変更する際は依存関係とインデックスを考慮すること。

---

（今後のリリースでは Added / Changed / Fixed / Deprecated / Removed / Security の各セクションごとに変更を追記してください。）