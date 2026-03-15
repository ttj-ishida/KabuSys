CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-03-15
--------------------

初回公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョン（0.1.0）を定義。公開サブパッケージとして data, strategy, execution, monitoring を列挙。

- 環境設定モジュール
  - src/kabusys/config.py を追加。
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。これにより CWD に依存せずに自動ロードできる設計。
  - .env パーサーを実装し、以下をサポート：
    - 空行・コメント行の無視
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの inline コメントの扱い（直前がスペース/タブの場合に '#' をコメントと認識）
  - .env 読み込み時の上書き制御（override フラグ）と保護キーセット（protected）により OS 環境変数の保護を実現。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途など）。
  - Settings クラスを提供し、アプリケーションで使う主要設定値をプロパティとして取得可能：
    - J-Quants リフレッシュトークン、kabuステーション API パスワード、API ベース URL（デフォルトあり）
    - Slack ボットトークン・チャンネル ID
    - DuckDB / SQLite のデフォルトパス（expanduser に対応）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 未設定の必須環境変数取得時は ValueError を送出する設計。

- データスキーマ（DuckDB）基盤
  - src/kabusys/data/schema.py を追加。
  - DataSchema.md に基づく 3 層（Raw, Processed, Feature）＋Execution 層のテーブル定義を実装：
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型・制約（CHECK, PRIMARY KEY, FOREIGN KEY 等）を設定してデータ整合性を担保。
  - 頻出クエリを考慮したインデックス群を定義（銘柄×日付レンジ、ステータス検索など）。
  - init_schema(db_path) を実装：DuckDB ファイルの親ディレクトリ自動作成、テーブル作成（冪等）、接続オブジェクトを返す。
  - get_connection(db_path) を実装：既存 DB への接続取得（スキーマ初期化は行わない旨を明記）。
  - ":memory:" を指定したインメモリ DB にも対応。

- 監査ログ（トレーサビリティ）基盤
  - src/kabusys/data/audit.py を追加。
  - DataPlatform.md セクションに沿った監査ログ設計を実装。戦略→シグナル→発注要求→約定 の UUID 連鎖によるトレーサビリティを想定。
  - テーブル定義:
    - signal_events（シグナル生成ログ、戦略決定・棄却など全てを記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ、order_type に応じた CHECK 制約）
    - executions（証券会社からの約定ログ、broker_execution_id を一意に扱う）
  - すべての TIMESTAMP を UTC で保存する方針を採用（init_audit_schema 内で SET TimeZone='UTC' を実行）。
  - 監査向けインデックスを定義（シグナル検索、処理待ちキュー、broker_order_id 紐付け等）。
  - init_audit_schema(conn)（既存接続へ監査テーブル追加）と init_audit_db(db_path)（監査専用 DB 初期化）を実装。親ディレクトリの自動作成に対応。

- パッケージ構造（骨格）
  - strategy, execution, monitoring の各サブパッケージ初期化ファイル（__init__.py）を追加し、今後の機能拡張に備える。

### Changed
- （なし）

### Fixed
- （なし）

### Security
- 環境変数に関する処理は、必須変数が未設定の場合に ValueError を投げるため、起動前に .env 等での適切な設定が必要。
- .env 自動ロードは必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Migration
- 初回利用時は data.schema.init_schema() を用いてスキーマを初期化してください。監査テーブルを追加したい場合は init_audit_schema() を呼ぶか、監査専用 DB を利用する場合は init_audit_db() を使用してください。
- 環境変数の自動ロードをテスト環境等で抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に例外を投げます。デプロイ前に .env を作成してください（.env.example を参照）。

以上。