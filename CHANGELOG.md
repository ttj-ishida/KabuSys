CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の記法に準拠して記載しています。
リンクは必要に応じて埋めてください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース (バージョン 0.1.0)
  - パッケージ基礎
    - パッケージメタ情報を追加: kabusys.__version__ = "0.1.0"
    - パッケージ外部公開モジュールを __all__ で定義: "data", "strategy", "execution", "monitoring"
    - 空のサブパッケージ初期化ファイルを配置: execution, strategy, data, monitoring（拡張ポイントとして位置付け）
  - 環境設定管理モジュール (kabusys.config)
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加
      - 公開プロパティ:
        - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
        - kabu_api_password (KABU_API_PASSWORD 必須)
        - kabu_api_base_url (デフォルト: "http://localhost:18080/kabusapi")
        - slack_bot_token (SLACK_BOT_TOKEN 必須)
        - slack_channel_id (SLACK_CHANNEL_ID 必須)
        - duckdb_path (デフォルト: "data/kabusys.duckdb")
        - sqlite_path (デフォルト: "data/monitoring.db")
        - env (KABUSYS_ENV、許容値: "development", "paper_trading", "live")
        - log_level (LOG_LEVEL、許容値: "DEBUG","INFO","WARNING","ERROR","CRITICAL")
        - is_live / is_paper / is_dev のブール判定プロパティ
      - 設定未定義や不正値の場合は ValueError を送出することで早期検出を容易に
    - .env 自動読み込み機能を追加
      - 読み込み優先順位: OS環境変数 > .env.local > .env
      - プロジェクトルート検出: __file__ を起点に親ディレクトリ内の .git または pyproject.toml を探索
      - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - OS 環境変数を保護する仕組み: .env 読み込み時に既存の環境変数を保護（.env.local は override=True だが保護されたキーは上書きしない）
    - .env パーサーの実装
      - 空行・コメント行のスキップ、"export KEY=val" 形式のサポート
      - クォートあり値のエスケープ処理に対応（シングル/ダブルクォート、バックスラッシュのエスケープ）
      - クォートなし値では適切な位置の '#' をインラインコメントとして扱うロジックを実装
  - DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
    - データレイヤーを想定した多層スキーマを定義
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - テーブル定義に各種制約を付与（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY など）
      - 例: prices_daily の low <= high、volume や size の非負/正チェック、side/status/order_type 列の列挙チェック等
    - インデックス定義を追加して典型的なクエリパターン（銘柄×日付スキャン、ステータス検索など）に最適化
      - 例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定の DuckDB ファイルに対してスキーマとインデックスを作成（冪等）
        - db_path の親ディレクトリが存在しない場合は自動作成
        - ":memory:" によるインメモリ DB をサポート
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存 DB へ接続（スキーマ初期化は行わない。初回は init_schema を使用）
    - テーブルの作成順を外部キー依存に配慮して定義
  - ドキュメント & コードコメント
    - 各モジュール・関数に日本語ドキュメント文字列を付与し、挙動や例を明確化

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- なし（初回リリース）

Upgrade notes
- 初回導入時は以下を推奨:
  - .env / .env.local をプロジェクトルートに準備し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定する。
  - テスト実行等で自動 .env 読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
  - DuckDB の初回セットアップは init_schema() を呼んでからアプリケーションを起動する（db_path の親ディレクトリは自動作成される）。
  - 必須環境変数が未設定だと Settings プロパティで ValueError が発生するため、起動前に環境変数を確認する。

Contributors
- 初期実装者（リポジトリのコードに基づく推定）: 開発チーム

注記
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や意図した変更点に応じて適宜修正してください。