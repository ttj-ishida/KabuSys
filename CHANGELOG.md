CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
このプロジェクトはまだ初期段階のため、最初のリリースのみ記載しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-15
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境変数 / 設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に親ディレクトリを探索（CWD 非依存）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - .env 読み込み時に OS 環境変数は保護（.env.local の上書きでも保護対象は上書きされない）。
    - .env 読み込みに失敗した場合は警告を出力（warnings.warn）。
  - .env パーサーの仕様実装:
    - 空行・コメント行('#'で始まる)を無視。
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォートで囲まれた値を扱い、バックスラッシュによるエスケープを解釈。
    - クォート無し値は、'#' の直前がスペースまたはタブの場合をコメントとみなす（それ以外の '#...' は値の一部）。
    - 無効行はスキップ。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - 必須値取得のヘルパー: _require() — 未設定時は ValueError を送出。
    - J-Quants、kabu ステーション、Slack、データベースパス等のプロパティ:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (KABU_API_PASSWORD)
      - kabu_api_base_url（既定値: http://localhost:18080/kabusapi）
      - slack_bot_token (SLACK_BOT_TOKEN)
      - slack_channel_id (SLACK_CHANNEL_ID)
      - duckdb_path（既定: data/kabusys.duckdb）
      - sqlite_path（既定: data/monitoring.db）
    - システム設定:
      - env（KABUSYS_ENV、許容値: development, paper_trading, live。無効な値は ValueError）
      - log_level（LOG_LEVEL、許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL。無効な値は ValueError）
      - is_live / is_paper / is_dev のブール判定プロパティ

- データスキーマ / 初期化モジュールを追加 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層＋実行層のテーブル定義（DuckDB 用 DDL）を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに主キー / 外部キー / CHECK 制約を多用してデータ整合性を確保（例: side の列に IN 制約、価格やサイズの非負チェック等）。
  - news_symbols による news_articles への外部キー（ON DELETE CASCADE）や orders → signal_queue の参照（ON DELETE SET NULL）などの参照整合性を定義。
  - 頻出クエリを想定したインデックスを定義（例: prices_daily(code, date), signal_queue(status), orders(status) 等）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイル（":memory:" をサポート）を初期化し、全テーブル・インデックスを作成して接続を返す。
      - 既に存在するテーブルはスキップするため冪等。
      - db_path の親ディレクトリが存在しない場合は自動作成。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続を返す（スキーマ初期化は行わない。初回は init_schema を使用）。

- パッケージ構造
  - 空のパッケージ初期化ファイルを追加:
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - strategy, execution, monitoring の各モジュールは現時点で未実装（プレースホルダ）。

Notes / その他
- スキーマ定義は DuckDB を前提としており、主に時系列市場データ、ファンダメンタル、ニュース、取引/ポジション管理をカバーする構成になっています。
- 初期リリースではテストや詳細なエラーハンドリング、各サブモジュールの実装（strategy / execution / monitoring）はこれからの開発課題です。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Security
- なし

今後の予定（参考）
- strategy / execution / monitoring の実実装（発注ロジック、バックテスト、監視・通知機能等）
- 単体テスト、CI、型チェック、ドキュメント強化
- .env パースの追加ケース対応・堅牢化

---

（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリース日等はプロジェクト実態に合わせて調整してください。）