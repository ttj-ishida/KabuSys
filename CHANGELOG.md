# Changelog

すべての注目すべき変更はこのファイルに記録しています。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/）に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージの初期構成を追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にてパッケージ名・バージョンと公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を起点に行うため、カレントディレクトリに依存しない動作を実現。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト時等の利便性）。
    - .env を先に読み込み（既存の OS 環境変数を上書きしない）、続けて .env.local を上書きモードで読み込む仕組みを採用。
    - OS 環境変数は保護（protected）され、.env から上書きされないように制御。
  - .env のパース処理を強化：
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートされた値のエスケープ処理と適切な終端検出に対応。
    - クォートなし値に対するコメント解釈は「# の直前がスペースまたはタブである場合のみ」コメントとして扱う等、実用的なパースを実現。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - J-Quants、kabuステーション、Slack、データベースパスなどの設定プロパティを用意。
    - 必須環境変数取得時に未設定なら ValueError を送出する _require() を実装。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の値検証を実装。
    - is_live / is_paper / is_dev のヘルパーを提供。
    - デフォルト値の設定:
      - KABUS_API_BASE_URL のデフォルトは "http://localhost:18080/kabusapi"
      - DUCKDB_PATH のデフォルトは "data/kabusys.duckdb"
      - SQLITE_PATH のデフォルトは "data/monitoring.db"

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - DataSchema.md に基づく 3〜4 層（Raw / Processed / Feature / Execution）のテーブル定義を実装。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型チェック（CHECK 制約）や主キー、外部キー制約を設定。
  - よく使われるクエリに備えたインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - テーブル作成順を外部キー依存を考慮して整理。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - DB ファイルの親ディレクトリを自動作成し、全テーブル・インデックスを作成。冪等性あり（既存ならスキップ）。
      - ":memory:" を指定してインメモリ DB の利用が可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わないため、初回は init_schema を使用すること）。

- パッケージの空のサブパッケージプレースホルダを追加（src/kabusys/execution, src/kabusys/strategy, src/kabusys/data, src/kabusys/monitoring の __init__.py）。  
  将来の機能拡張（戦略、実行、監視）に備えた構成。

### Security
- .env 自動読み込み時に OS の環境変数を保護する仕組みを導入（protected set に含まれるキーは .env/.env.local によって上書きされない）。

### Notes
- スキーマ初期化は冪等（init_schema は既存テーブルを上書きせずスキップ）なので、複数回呼び出しても安全です。
- .env のパースは POSIX シェルの完全な互換を目指したものではなく、実用上の多数ケース（export、クォート、エスケープ、行内コメント等）に対応しています。特殊ケースは予期しない動作になる可能性があります。

## Deprecated
- なし

## Removed
- なし

## Fixed
- なし

## Internal
- パッケージ初期構成と基本 API の導入により今後の開発の基盤を整備。

--- 

（この CHANGELOG はリポジトリの現状コードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）