# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはパッケージの初回リリースに基づき推測して作成しています。

## [0.1.0] - 2026-03-15

### 追加
- パッケージ初期リリース "kabusys"。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - パブリック API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

- 環境設定モジュール（kabusys.config）を追加。
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: 現在のファイル位置から親ディレクトリを上に辿り、.git または pyproject.toml を基準にプロジェクトルートを特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化オプション: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを停止可能（テスト用途想定）。
    - 読み込みに失敗した場合は警告を発行（ファイル読み込み例外を捕捉）。
  - .env パーサーの拡張:
    - export KEY=val 形式をサポート。
    - シングル・ダブルクォートされた値内のバックスラッシュエスケープを正しく扱う（対応する閉じクォートまでを値として解釈し、以降のインラインコメントは無視）。
    - クォートなし値では、'#' が直前に空白/タブがある場合のみコメントと扱う。
    - 無効行（空行、コメント行やキーがない行）を無視。
    - protected set（OS 環境変数）を指定して上書きを抑制する機能。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得可能:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 実行環境: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live, is_paper, is_dev
  - 必須環境変数未設定時は ValueError を発生させるヘルパー _require を実装。

- DuckDB スキーマ定義および初期化モジュール（kabusys.data.schema）を追加。
  - 3層（Raw / Processed / Feature）＋ Execution 層に対応するテーブル群を定義:
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー・外部キー・CHECK 制約（数値の非負、列値の許容集合等）を付与し、データ整合性を強化。
  - 頻出アクセスパターンを考慮したインデックス定義を追加（例: prices_daily(code, date), features(code, date), signal_queue(status) 等）。
  - テーブル作成順を外部キー依存に基づき管理。
  - 初期化用関数を提供:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスの DuckDB を初期化して全テーブル・インデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定するとインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない）。
  - DuckDB を利用することでローカルかつ高速な分析用 DB を想定。

- サブパッケージのプレースホルダを追加:
  - kabusys.data.__init__, kabusys.strategy.__init__, kabusys.execution.__init__, kabusys.monitoring.__init__（現時点では空のモジュール）。

### 変更
- 初回リリースのため該当なし。

### 修正
- 初回リリースのため該当なし。

### 削除
- 初回リリースのため該当なし。

### 既知の注意点 / 備考
- 環境変数自動ロードはプロジェクトルートが特定できない場合はスキップされます（配布後の環境や CWD に依存しない設計）。
- .env のパースルールは一般的なケースをカバーするよう手当てしているが、特殊なエッジケースがある可能性があります。必要に応じてパースルールを調整してください。
- init_schema は冪等にテーブルを作成するため、スキーマのマイグレーション機構は含まれていません。将来的にスキーマ変更がある場合はマイグレーション対応が必要です。

---