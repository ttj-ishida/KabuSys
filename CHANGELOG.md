Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]
------------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-15
-------------------

初回公開リリース。本リポジトリの最初の安定化された機能群を導入します。

Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名、バージョン (__version__ = "0.1.0") および公開モジュール一覧 (__all__) を定義。

- 環境設定管理モジュール
  - src/kabusys/config.py を追加。
  - .env ファイル（および .env.local）または既存の OS 環境変数から設定を読み込む自動ローダを実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用など）。
    - プロジェクトルートを .git または pyproject.toml により __file__ の親階層から検出するため、CWD に依存しない実装。
    - .env と .env.local の読み込み順序（OS 環境 > .env.local > .env）および .env.local による上書き挙動をサポート。
    - OS 環境変数を保護するための protected キー集合を採用し、不用意な上書きを防止。
  - .env パーサを実装（_parse_env_line）:
    - 空行やコメント行（#）の無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポートし、対応する閉じクォートまでを正しくパース。
    - クォート無し値におけるインラインコメントの扱い（直前がスペース/タブの場合のみコメントとして認識）。
  - 設定取得ラッパ Settings クラスを追加（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / Slack / データベースパス等のプロパティを提供:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (KABU_API_PASSWORD)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (SLACK_BOT_TOKEN)
      - slack_channel_id (SLACK_CHANNEL_ID)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
    - env（KABUSYS_ENV）と log_level（LOG_LEVEL）に対する値検証を実装:
      - KABUSYS_ENV の有効値: development, paper_trading, live
      - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - is_live, is_paper, is_dev の便利プロパティを追加。
    - 未設定の必須環境変数に対しては ValueError を送出する _require() を実装。

- DuckDB ベースのデータスキーマと初期化ユーティリティ
  - src/kabusys/data/schema.py を追加。
  - データレイヤ設計（Raw / Processed / Feature / Execution）に基づくテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して制約（NOT NULL、PRIMARY KEY、CHECK、外部キーなど）を設定。
  - 検索パフォーマンスを考慮したインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) を実装:
    - 指定されたパスの親ディレクトリを自動作成（":memory:" の場合はスキップ）。
    - 全テーブル・インデックスを作成（冪等性を保持）。
    - 初期化済みの duckdb 接続を返す。
  - get_connection(db_path) を実装: 既存 DB へ接続（スキーマ初期化は行わない）。

- パッケージ構造のスケルトン
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的なモジュール実装用プレースホルダ）。

Changed
- 該当なし（初回リリースのため差分なし）。

Fixed
- 該当なし（初回リリースのため差分なし）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし（ただし環境変数の保護と必須値チェックにより安全性に配慮）。

Notes / 備考
- .env の読み込みロジックは実運用での誤上書きを防ぐ設計（protected set）です。CIやテスト環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマは将来的に拡張を想定してレイヤ構造で設計されています。外部キーやインデックス順序は依存関係を考慮して決められています。