Changelog
=========

すべての変更は「Keep a Changelog」形式に準拠し、セマンティック バージョニングを採用しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py に __version__ を定義）。
- パッケージ公開APIの整備:
  - __all__ による公開サブパッケージ指定: data, strategy, execution, monitoring。
  - 空のサブパッケージ用モジュールプレースホルダを追加（src/kabusys/{execution,strategy,monitoring}/__init__.py）。

- 環境変数・設定管理モジュール（src/kabusys/config.py）を追加:
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を検出してルートを特定（CWDに依存しない方式）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
  - OS 環境変数を保護するため、既存の環境変数はデフォルトで上書きされない。必要に応じて .env.local の上書きを許可。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みをスキップ可能（テスト用など）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート値をサポートし、バックスラッシュによるエスケープを正しく処理。
    - クォートなしの場合のインラインコメント判定（'#' の前が空白/タブならコメントとみなす）を実装。
    - 無効行（空行、コメント、key=value でない行）をスキップ。
  - Settings クラスを提供し、アプリケーションが使用する主要な設定をプロパティとして取得:
    - J-Quants: jquants_refresh_token（必須）
    - kabuステーション API: kabu_api_password（必須）、kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須）、slack_channel_id（必須）
    - DBパス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - システム設定: env (KABUSYS_ENV、"development"|"paper_trading"|"live" を検証)、log_level (LOG_LEVEL を検証)、および便利なブールプロパティ is_live/is_paper/is_dev
  - 未設定の必須環境変数取得時は ValueError を発生させ、.env.example を参照する旨のメッセージを含む。

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）を追加:
  - 3層設計に基づくテーブル群を定義（Raw / Processed / Feature / Execution レイヤー）。
  - 主要テーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions（取得した生データを格納）
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（整形済み市場データ）
    - Feature Layer: features, ai_scores（戦略・AI用特徴量／スコア）
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（発注〜ポジション管理）
  - 各テーブルに対して適切な型、PRIMARY KEY、FOREIGN KEY、CHECK 制約、DEFAULT（fetched_at / created_at に current_timestamp など）を追加。
  - 頻出クエリに備えたインデックスを定義（例: prices_daily(code, date), features(code, date), signal_queue(status), orders(status) など）。
  - テーブル作成順は外部キー依存を考慮して定義。
  - 公開関数:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルを初期化し、全テーブル／インデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定してインメモリ DB を使用可能。
      - 初期化済みの DuckDB 接続を返す。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わないため、初回は init_schema を呼ぶ必要がある）。

Changed
- なし（初回リリースのため変更履歴なし）

Fixed
- なし

Removed
- なし

Security
- なし

Notes
- このリリースは基盤実装（設定管理とデータスキーマ）に注力しており、戦略・実行・モニタリングの具体的実装は今後のリリースで追加予定です。