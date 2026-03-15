変更履歴 (Keep a Changelog 準拠)
================================

すべての変更は https://keepachangelog.com/ja/ のガイドラインに従って記載しています。

[Unreleased]
-----------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン: 0.1.0
- パッケージ公開 API
  - パッケージルート: src/kabusys/__init__.py（__version__ と __all__ を定義）
  - 空のサブパッケージプレースホルダ: execution, strategy, monitoring（将来の拡張用）
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - Settings クラスを追加し、アプリ設定をプロパティ経由で提供
    - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id（必須）
    - kabu_api_base_url, duckdb_path, sqlite_path（デフォルト値付き）
    - env（KABUSYS_ENV の検証: development / paper_trading / live）
    - log_level（LOG_LEVEL の検証: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー
  - .env 自動読み込み機能を追加
    - プロジェクトルートを .git または pyproject.toml から探索して特定
    - 優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数を保護する仕組み（.env の上書きを防止）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で使用）
  - .env パーサーの実装（_parse_env_line）
    - 空行 / コメント行（先頭 #）の無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート対応、バックスラッシュエスケープ処理、クォート内のインラインコメント無視
    - クォートなしの場合は '#' がコメント始点となるが、直前がスペース/タブの場合にのみコメントとみなす（柔軟なコメント処理）
  - 環境変数未設定時は _require() による ValueError 投出（必須設定の明示的検出）
- データスキーマ (DuckDB) — 基本スキーマ (src/kabusys/data/schema.py)
  - init_schema(db_path) と get_connection(db_path) を提供
  - Raw / Processed / Feature / Execution の4層設計に基づくテーブル群を定義
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する詳細な型・CHECK 制約・PRIMARY KEY を定義（数値非負チェック、列単位制約など）
  - 性能向上のためのインデックス群を定義・作成（銘柄×日付スキャン、ステータス検索、FK 結合最適化など）
  - init_schema は冪等（既存テーブルがあればスキップ）、db_path の親ディレクトリがなければ自動作成
  - ":memory:" によるインメモリ DB のサポート
- 監査ログ（トレーサビリティ）機能 (src/kabusys/data/audit.py)
  - init_audit_schema(conn) と init_audit_db(db_path) を提供
  - シグナル → 発注要求 → 約定 のフローをトレースする監査テーブル群を定義
    - signal_events（戦略が生成したすべてのシグナルを保存。棄却も含む）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定情報。broker_execution_id を冪等キーとして扱う）
  - テーブル間の外部キー制約（ON DELETE RESTRICT）により監査ログは削除されない設計
  - 各テーブルに created_at / updated_at を持ち、監査証跡を保証（updated_at はアプリ側で更新）
  - すべての TIMESTAMP は UTC に統一（init_audit_schema は "SET TimeZone='UTC'" を実行）
  - 監査用のインデックス群を定義（signal や order の検索・処理待ちキューの効率化など）
  - init_audit_db は単体監査 DB の初期化を行い、init_audit_schema を呼び出す
- データベース初期化の設計上の注意点をドキュメント的に実装
  - DuckDB の PRIMARY / UNIQUE / INDEX の扱い、NULL の扱いに配慮した設計（例: broker_order_id の UNIQUE インデックス）
  - 発注系の制約（limit/stop の price 要件チェック等）をスキーマレベルで担保

Changed
- n/a（初回リリースのため過去バージョンからの変更はなし）

Fixed
- n/a（初回リリースのためバグ修正履歴はなし）

Notes / 実装上の留意点
- Settings による環境変数取得は実行時に ValueError を投げるため、起動前に .env の準備が必要（.env.example を参照する旨のエラーメッセージあり）。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後も正しく動作するよう __file__ から親ディレクトリを探索する実装になっている。
- DuckDB スキーマ初期化は idempotent であり、既存データベースに対して安全に実行可能。
- 監査ログは削除せず追跡可能であることを前提とした設計（FK は RESTRICT、履歴保持）。
- init_audit_schema は UTC タイムゾーンを設定するため、アプリケーション側でもタイムゾーンの扱いに注意すること。

今後の予定（非保証）
- strategy / execution / monitoring 各サブパッケージの実装（戦略ロジック、発注処理、モニタリング・アラート等）
- DB マイグレーション機能の追加（スキーマ進化対応）
- より詳細なドキュメント（DataSchema.md, DataPlatform.md の参照実装や利用例）の追加

以上。