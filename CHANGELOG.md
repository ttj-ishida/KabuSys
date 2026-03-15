Changelog
=========
すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

v0.1.0 - 2026-03-15
-------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring
  - ルート docstring を追加（「KabuSys - 日本株自動売買システム」）。

- 環境設定処理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加。
    - ロード優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートの検出は .git または pyproject.toml を探索して行う（CWD に依存しない）。
  - .env 解析機能を強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応して正しく値を復元。
    - クォートなし値でのコメント判定（'#' の直前がスペース/タブの場合はコメントと扱う）に対応。
    - 無効行（空行やコメント行、= を含まない行）は無視。
  - .env 読み込み時の上書きポリシー:
    - override=False: 未設定キーのみ設定。
    - override=True: protected（OS 環境変数セット）に含まれるキーを除き上書き。
    - 読み込み失敗時には警告を出力して安全にスキップ。
  - Settings クラスを提供し、環境変数から設定値を取得するプロパティを用意:
    - J-Quants 関連: jquants_refresh_token (必須)
    - kabuステーション API: kabu_api_password (必須), kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - Slack: slack_bot_token (必須), slack_channel_id (必須)
    - データベースパス: duckdb_path (デフォルト: data/kabusys.duckdb), sqlite_path (デフォルト: data/monitoring.db)
    - システム設定: env (KABUSYS_ENV デフォルト: development)、log_level (LOG_LEVEL デフォルト: INFO)
    - env/log_level の値検証（許容値は定義済みで不正な値は ValueError を送出）
    - is_live / is_paper / is_dev といった判定プロパティを追加
  - 必須環境変数が未定義の場合は _require() にて ValueError を送出（.env.example を参照する旨のメッセージ）。

- データベーススキーマ管理（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマ定義と初期化ユーティリティを追加。
  - データレイヤ設計（README 相当の説明）:
    - Raw Layer（raw_* テーブル）
    - Processed Layer（prices_daily, fundamentals, news_articles 等）
    - Feature Layer（features, ai_scores）
    - Execution Layer（signals, signal_queue, orders, trades, positions, portfolio_performance 等）
  - 多数のテーブル DDL を定義（主なもの）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions（主キー・チェック制約あり）
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（外部キー付き）
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して妥当性チェック（CHECK 制約）、主キー、外部キー、ON DELETE 挙動を設定。
    - 例: side は ('buy','sell') のみ許可、size は > 0、price は >= 0、low <= high など。
    - 外部キーの ON DELETE 動作を明示（NEWS -> news_symbols は CASCADE、orders.signal_id は SET NULL、trades.order_id は CASCADE）。
  - 頻出クエリ向けのインデックスを定義・作成:
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した path の親ディレクトリを自動作成（":memory:" は除く）。
      - 全テーブル・インデックスを作成（冪等的に実行）。
      - 初期化済みの DuckDB 接続を返す。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続を返す（スキーマ初期化はしない。初回は init_schema を呼ぶべき）。

Changed
- 初期リリースのため「Changed」には現状なし（初版で新規追加された機能が中心）。

Fixed
- 初期リリースのため特定のバグ修正履歴はなし。

Security
- 特になし。

Notes / 補足
- src/kabusys 以下に空の __init__.py が用意されており、サブパッケージ（data, strategy, execution, monitoring）を将来的に拡張可能。
- .env 読み込み処理はプロジェクトルートを探索するため、パッケージ配布後でも安定して動作する設計。
- DuckDB 初期化はファイルパスの親ディレクトリ自動生成や ":memory:" 対応など実運用を意識した実装になっている。