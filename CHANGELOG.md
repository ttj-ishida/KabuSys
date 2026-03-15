# Changelog

すべての注目すべき変更点を記録します。形式は「Keep a Changelog」に準拠しています。  
初版リリースはパッケージの初期機能実装に相当するため、ここではコードベースから推測される機能・変更点をまとめています。

全般的な注意
- この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴とは差異がある可能性があります。
- 本リポジトリのバージョンはパッケージ定義（src/kabusys/__init__.py）に従い v0.1.0 として記載しています。

Unreleased
- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-15
Added
- パッケージ初期リリースとして基本モジュールを追加
  - パッケージメタ情報を追加（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を定義
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装
    - プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存せず配布後も正しく動作
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化可能
    - OS 環境変数は保護（.env の上書きを抑制）する仕組みを実装
  - .env パーサを実装（引用符、エスケープ、コメント、export 形式などに対応）
  - 必須環境変数を要求する _require 関数と Settings クラスを提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須変数をプロパティで公開
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供（Path オブジェクトで取得）
    - KABUSYS_ENV の妥当性チェック（development, paper_trading, live）と補助プロパティ（is_live, is_paper, is_dev）
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- データ層（DuckDB）スキーマ定義と初期化機能を追加（src/kabusys/data/schema.py）
  - 3層＋実行層アーキテクチャを定義
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を付与
  - 頻出クエリを想定したインデックス定義を追加（例: prices_daily(code,date), features(code,date), signal_queue(status) 等）
  - init_schema(db_path) を提供
    - db_path の親ディレクトリを自動作成
    - ":memory:" のサポート
    - 冪等にテーブル／インデックスを作成
    - 初期化済みの duckdb 接続を返す
  - get_connection(db_path) を提供（スキーマ初期化は行わない）
- 監査ログ（Audit）スキーマを追加（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定 に至るトレーサビリティ設計を実装
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ）
  - 設計原則・制約を明記（全 TIMESTAMP を UTC で保存、FK は ON DELETE RESTRICT、updated_at はアプリ側で更新など）
  - 注文タイプ別の CHECK 制約（limit/stop/market に応じた価格の必須／禁止）を実装
  - 各種検索用インデックスを追加（signal_events の日付検索、order_requests.status、executions の broker_order_id など）
  - init_audit_schema(conn) を提供（既存接続へ監査テーブルを追加、UTC タイムゾーン設定を行う）
  - init_audit_db(db_path) を提供（監査専用 DB を初期化して接続を返す、親ディレクトリの自動作成、":memory:" サポート）
- サブパッケージ用の空 __init__ を追加（execution, strategy, data, monitoring）によりパッケージ構成を整備

Changed
- 初リリースのため「変更」はありません（新規実装のみ）

Fixed
- 初リリースのため「修正」はありません

Security
- 初リリースのため既知のセキュリティ修正はありません

Notes / Migration / 使用上の注意
- DB 初期化
  - アプリ開始時に data.schema.init_schema(settings.duckdb_path) を呼び出し、スキーマを初期化してください。
  - 監査ログを別 DB として使う場合は data.audit.init_audit_db() を使用するか、既存接続に対して data.audit.init_audit_schema(conn) を呼び出してください。
- 環境変数の自動ロード
  - デフォルトでプロジェクトルートの .env, .env.local を自動ロードします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数が未設定の場合、Settings の対応プロパティが ValueError を投げます。事前に .env.example 等を用意して設定してください。
- すべての TIMESTAMP は監査テーブル関連で UTC 保存を前提としています（init_audit_schema 内で SET TimeZone='UTC' を実行）。

既知の制約 / 今後の改善候補（推奨）
- DuckDB は単一ノード向けの組み込み DB のため、複数プロセスからの同時書き込みや分散運用を行う場合は運用設計が必要。
- audit テーブルの broker_order_id に対する UNIQUE インデックスは NULL を許容する設計のままになっているため、外部コールバック連携時の運用ルールを明確化する必要あり。
- エラーメッセージやロギング周りは Settings の log_level を利用する想定だが、ログ設定の統合的な初期化モジュールがあれば望ましい。

問い合わせ・貢献
- この CHANGELOG はコード内容から自動推測したものであり、実際のコミットログや設計ドキュメント（DataSchema.md, DataPlatform.md 等）に基づく保守を推奨します。補足や修正があれば PR をお願いします。