CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース: kabusys パッケージを追加（バージョン 0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準にルートを特定（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途を想定）。
    - .env 読み込み時の保護: OS の既存環境変数は protected として上書きされない（override パラメータあり）。
    - .env 行パーサ:
      - 空行・コメント行（#）を無視。
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
      - クォート無しの場合は '#' の直前が空白/タブのときのみコメントとみなす等、実用的なパース挙動を実装。
    - .env ファイルの読み込み失敗時は警告を発行（例外ではなく警告）。

  - Settings クラスで主要設定値をプロパティ経由で取得（環境変数の必須チェックとデフォルト付き設定）。
    - J-Quants / kabu ステーション / Slack / データベースパス等の取得プロパティを実装。
    - duckdb/sqlite の既定パスを提供（Path オブジェクト）。
    - KABUSYS_ENV の検証: 有効値は "development", "paper_trading", "live"（不正値は ValueError）。
    - LOG_LEVEL の検証: 有効値は "DEBUG","INFO","WARNING","ERROR","CRITICAL"（不正値は ValueError）。
    - is_live / is_paper / is_dev 判定プロパティを提供。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - データレイヤーを3層（Raw / Processed / Feature）＋Execution 層で設計・DDL 定義。
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions（主キー・型チェック付き）。
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（外部キー制約含む）。
  - Feature Layer: features, ai_scores（作成時刻・主キー付き）。
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（ステータス列やチェック制約を含む）。
  - 各テーブルに対する整合性チェック（NOT NULL、CHECK、主キー、外部キー制約等）を定義。
  - 頻出クエリ向けのインデックスを追加（例: 銘柄×日付、ステータス検索、JOIN 用インデックス等）。
  - init_schema(db_path) API を提供:
    - 指定した DuckDB ファイルを初期化して全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" モード対応。
  - get_connection(db_path) API を提供:
    - 既存 DB へ接続を返す（スキーマ初期化は行わない旨を明示）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナルから約定に至るフローを UUID 連鎖で追跡可能にする監査用テーブル群を実装。
  - 主要テーブル:
    - signal_events: 戦略が生成した全シグナル（棄却・エラーも記録）、decision/status 列を設置。
    - order_requests: 発注要求ログ。order_request_id を冪等キー（UUID）として採用。order_type に応じたチェック制約（limit/stop/market の価格列必須/禁止）を実装。status と error_message を保持。外部キーは ON DELETE RESTRICT（監査ログを削除しない方針）。
    - executions: 実際の約定ログ。broker_execution_id を証券会社提供の冪等キーとして UNIQUE 制約を付与。order_request_id に対する FK を設定（ON DELETE RESTRICT）。
  - 追加インデックスを定義（シグナル日付検索、戦略別検索、status によるキュー取得、broker_id による紐付け等）。
  - init_audit_schema(conn) / init_audit_db(db_path) API を提供:
    - init_audit_schema は接続に対して監査テーブルを冪等で追加。
    - init_audit_db は監査専用 DB の初期化（親ディレクトリ自動作成、":memory:" 対応）。
    - すべての TIMESTAMP は UTC で保存するため init_audit_schema 内で SET TimeZone='UTC' を実行。

Other
- ドキュメント的な説明（モジュール docstring）を充実させ、DataSchema.md / DataPlatform.md に基づく設計方針やトレーサビリティの考え方を明記。

Security
- .env 読み込み時に OS の既存環境変数を保護する仕組み（protected set）を導入。これにより OS 側の機密値が誤って上書きされないよう配慮。

Notes
- schema の初期化は冪等で安全に何度でも呼べる設計。初回は init_schema() / init_audit_db() を呼び、以降は get_connection() や接続を再利用する想定。
- 監査ログは削除しない（FK は ON DELETE RESTRICT）方針のため、運用時の取り扱いに注意。
- .env のパース挙動などは実運用の .env ファイルの多様な書き方を考慮した実装になっているが、特殊ケースはテストの上で利用することを推奨。

References
- 本 CHANGELOG はソースコード（src/ 以下）の内容を基に作成しています。