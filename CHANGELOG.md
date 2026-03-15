Keep a Changelog 準拠 — 変更履歴

すべての重要な変更をここに記載します。フォーマットは Keep a Changelog に準拠しています。
リリース日付はコードスナップショットの作成日を使用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤機能を実装。

### 追加
- パッケージメタ情報
  - パッケージルートに __version__ = "0.1.0" を追加。
  - __all__ に公開サブパッケージ（data, strategy, execution, monitoring）を設定。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を基準に親ディレクトリを探索）。これにより CWD に依存せずパッケージ配布後も正しく動作。
  - .env の行パーサ (_parse_env_line) を実装：
    - 空行・コメント行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して正しく値を抽出。
    - クォート無しの場合は '#' の前がスペース/タブであればコメントと判定するロジックを導入。
  - .env ファイル読み込みロジック (_load_env_file) を実装：
    - override フラグにより既存環境変数の上書き可否を制御。
    - protected（OS 環境変数のキー集合）を指定して上書きを防止。
    - ファイル読み込み失敗時には warnings.warn により警告を出力。
  - 自動ロードの優先順位を定義:
    - OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途向け）。
  - 必須環境変数取得ヘルパー _require を追加。未設定時は ValueError を送出。
  - Settings クラスを導入し、プロパティ経由で設定取得を提供：
    - J-Quants / kabuステーション / Slack / データベースパスなどのプロパティを定義。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL（DEBUG, INFO, ...）の値検証を実装。
    - is_live / is_paper / is_dev のブールヘルパーを追加。
    - データベースファイルの既定値（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を設定。
    - kabu_api_base_url にデフォルト値 "http://localhost:18080/kabusapi" を設定。

- DuckDB スキーマ定義と初期化機能（kabusys.data.schema）
  - 生データ（Raw Layer）、整形済み市場データ（Processed Layer）、特徴量（Feature Layer）、発注・約定・ポジション（Execution Layer）の 4 層を想定した DDL を実装。
  - 主なテーブル（例）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに主キー、型チェック、CHECK 制約、外部キーを適切に定義。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）。
  - テーブル作成順を外部キー依存関係を考慮して定義。
  - init_schema(db_path) を実装：
    - DuckDB データベースを初期化し、全テーブルおよびインデックスを作成（冪等性あり）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" 指定でインメモリ DB を利用可能。
    - 初期化済みの duckdb 接続オブジェクトを返す。
  - get_connection(db_path) を実装：既存 DB への接続を返す（スキーマ初期化は行わないことを明記）。

- パッケージ構成
  - サブパッケージの枠組みを追加（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring）。現時点では __init__ が存在するのみで、将来的な機能実装のプレースホルダ。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- 必須環境変数未設定時に明示的に例外を投げることで、安全な起動確認を容易に。

注記
- .env の解釈は一般的なシェルの挙動に近い形で実装されていますが、完全な互換性（すべてのエスケープや特殊ケース）を保証するものではありません。必要に応じて .env パーサの拡張を検討してください。
- DataSchema.md に基づくスキーマ設計を参照する想定の記述があります（ソースには DataSchema.md の内容は含まれていません）。
- 今後のリリースでは戦略実装、実行エンジン、監視（monitoring）機能の詳細実装を追加予定です。