# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-15

初回リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - トップレベルのエクスポート: data, strategy, execution, monitoring
  - 各サブパッケージのスケルトンを追加（src/kabusys/{data,strategy,execution,monitoring}/__init__.py）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、実行カレントディレクトリに依存しない実装。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーの強化:
    - 空行・コメント行の無視、export KEY=val 形式対応
    - シングル／ダブルクォートのサポートとバックスラッシュエスケープ処理
    - クォート無し値のインラインコメント判定（直前が空白・タブの場合のみ）
  - .env の読み込み時に既存 OS 環境変数を保護するための protected キーセットの概念を実装。
    - override フラグで上書きの可否を制御。
  - Settings クラスによりアプリケーション設定をプロパティで提供:
    - 必須の取得で未設定時は ValueError を送出するヘルパー _require を用意。
    - サポートする設定例:
      - JQUANTS_REFRESH_TOKEN (必須)
      - KABU_API_PASSWORD (必須)
      - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
      - SLACK_BOT_TOKEN (必須)
      - SLACK_CHANNEL_ID (必須)
      - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
      - SQLITE_PATH (デフォルト: data/monitoring.db)
      - KABUSYS_ENV (有効値: development, paper_trading, live) — 不正値で例外を発生
      - LOG_LEVEL (有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL) — 不正値で例外を発生
    - 環境モード判定用ヘルパー: is_live, is_paper, is_dev

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3層（Raw / Processed / Feature）＋Execution 層に基づくテーブル定義を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対し型チェックや CHECK 制約、PRIMARY/FOREIGN KEY を設定。
  - 頻出クエリに対応するインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) を提供:
    - 指定したパスの DuckDB を初期化し、全テーブルとインデックスを冪等に作成。
    - db_path がファイルの場合は親ディレクトリを自動作成。
    - ":memory:" によるインメモリ DB をサポート。
  - get_connection(db_path) を提供:
    - 既存 DB への接続を返す（スキーマ初期化は行わない）。

- ドキュメント化
  - 各モジュールに簡単なモジュールドキュメンテーションを追加（目的や基本的な使い方を示す docstring）。

### 注意 / 使用上のメモ
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に例外となります。 .env.example を参考に .env を作成してください。
- DuckDB スキーマの初期化は一度 init_schema(settings.duckdb_path) を実行してください。初期化は冪等であり、既存テーブルはスキップされます。
- テスト等で自動環境読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### 既知の制限（今後の改善予定）
- サブパッケージ（strategy, execution, monitoring, data）は現状スケルトンのみ。具体的な実装（戦略ロジック、発注連携、監視機能、データ取得処理）は今後追加予定。

<!-- リリース比較やコミットへのリンクは必要に応じて追加してください -->