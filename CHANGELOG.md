KEEP A CHANGELOG
=================

すべての変更は Keep a Changelog の形式に従って記載しています。
重大・後方互換性のない変更がある場合は Breaking Changes として明示します。

Unreleased
---------
（なし）

0.1.0 - 2026-03-15
------------------
初回リリース。以下の主要機能を実装しています。

Added
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ により公開サブパッケージを定義: data, strategy, execution, monitoring

- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定
    - プロジェクトルートが見つからない場合は自動ロードをスキップ
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）
  - .env パーサを実装
    - 空行・コメント（#）の扱い、`export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの場合のインラインコメント処理（直前が空白またはタブの '#' をコメントとみなす）
    - 無効行のスキップ、安全なファイルオープンと読み込みエラー時の警告出力
    - override フラグと protected キーセットによる上書き制御（OS 環境変数の保護）
  - Settings クラスを提供（settings インスタンスを公開）
    - J-Quants、kabuステーション API、Slack、DB パス等の設定プロパティを定義
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
      - kabu_api_password (KABU_API_PASSWORD 必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token / slack_channel_id (必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを実装
      - 有効な KABUSYS_ENV: development, paper_trading, live
      - 有効な LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - is_live / is_paper / is_dev の補助プロパティを提供
    - 未設定の必須環境変数取得時は ValueError を送出

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - 市場データ・取引管理のための多層スキーマを定義（Raw / Processed / Feature / Execution）
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型制約、NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY を適用
    - 例: price/size/volume の非負や size > 0 などのチェック制約
    - 外部キーの ON DELETE 動作を明示（CASCADE / SET NULL 等）
  - 検索パフォーマンスを想定したインデックスを定義
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など
  - init_schema(db_path) を提供
    - 指定した DuckDB ファイルを初期化し、すべてのテーブルとインデックスを作成（冪等）
    - db_path の親ディレクトリが存在しない場合は自動作成
    - ":memory:" 指定でインメモリ DB に対応
    - 初期化済みの duckdb 接続を返す
  - get_connection(db_path) を提供（スキーマ初期化は行わない: 初回は init_schema を使用）

- サブパッケージ（空の __init__）を配置
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py
  - 今後これらに機能を追加するための土台を用意

Notes（注意事項）
- Settings の必須項目（トークン・パスワード等）が未設定の場合、実行時に ValueError が発生します。初期設定は .env.example を参考に .env を作成してください。
- DuckDB の初期化は init_schema を呼び出してください。get_connection は既存 DB へ接続するためのユーティリティです。
- .env のパースはかなり寛容である一方、複雑なエスケープや特殊ケースでは意図した通りに動作しない可能性があるため注意してください。

Deprecated
- なし

Removed
- なし

Security
- 現時点で特筆すべきセキュリティ修正はありません。環境変数に秘匿情報（トークン・パスワード）を含める場合は適切に管理してください。