Changelog
=========
すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース: KabuSys パッケージ (バージョン 0.1.0)
  - パッケージ概要: 日本株自動売買システムの基盤モジュール群（data, strategy, execution, monitoring）を提供。
  - パッケージメタ: src/kabusys/__init__.py にて __version__ = "0.1.0"、__all__ に主要サブパッケージを公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル／環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を起点に行い、カレントワーキングディレクトリに依存しない設計。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途など）。
    - OS 環境変数は protected として上書きを防止。
    - .env 読み込みでファイルを開けない場合は warnings.warn を発行して安全に継続。
  - .env パーサー (_parse_env_line) の細かな仕様:
    - 空行・コメント行（# で始まる）を無視。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理をサポートし、対応する閉じクォートまでを正しく抽出。
    - クォートなしの場合は、'#' が直前にスペースまたはタブがある場合のみコメントと判断して切り取り。
  - Settings クラスを公開（settings インスタンス経由で利用）:
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティを提供。
    - 必須環境変数未設定時は _require() が ValueError を送出。
    - デフォルト値: KABUS_API_BASE_URL のデフォルト（http://localhost:18080/kabusapi）、DUCKDB_PATH / SQLITE_PATH のデフォルトパス。
    - KABUSYS_ENV の検証（development / paper_trading / live）および LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Data Lake 層設計（Raw / Processed / Feature / Execution）に基づくテーブル定義を提供。
  - Raw Layer:
    - raw_prices, raw_financials, raw_news, raw_executions（主キー／チェック制約付き）。
  - Processed Layer:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols（外部キー、主キー、NULL 制約など）。
  - Feature Layer:
    - features, ai_scores（特徴量・AI スコア保存用）。
  - Execution Layer:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（発注・約定・ポジション管理用）。
    - signal_queue / orders / trades 等にステータスチェック、列チェック（order_type, status, side）や外部キーを設定。
  - インデックス定義: 頻出クエリを想定したインデックスを作成（銘柄×日付、ステータス検索、orders.signal_id など）。
  - 公開 API:
    - init_schema(db_path): DuckDB ファイルを初期化して全テーブル／インデックスを作成。冪等で、db_path の親ディレクトリが存在しない場合は自動作成。":memory:" によるインメモリ DB に対応。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema() を使用すること）。
  - テーブルの設計方針や制約 (チェック制約、NOT NULL、PRIMARY KEY、FOREIGN KEY) を明確化してデータ整合性を強化。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 今後の予定
- strategy, execution, monitoring サブパッケージは初期のパッケージ構成として空の __init__.py を含む（実装は今後追加予定）。
- 将来的に schema のマイグレーション機能やバージョン管理、より詳細なログ・監視機能を追加予定。