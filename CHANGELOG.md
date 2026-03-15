CHANGELOG
=========

すべての日付は YYYY-MM-DD 形式。  
この CHANGELOG は "Keep a Changelog" に準拠しています。

Unreleased
----------

（現時点なし）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリース。パッケージ名: kabusys（バージョン 0.1.0）
  - src/kabusys/__init__.py
    - パッケージメタ情報を追加（__version__, __all__）。
- 環境変数・設定管理モジュールを追加
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルパーサーを実装:
      - 空行・コメント行（行頭の #）を無視。
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のエスケープ処理に対応（バックスラッシュエスケープを解釈）。
      - クォート無し値では '#' の前が空白・タブの場合にインラインコメントとして扱うロジックを実装。
    - .env 読み込みの上書き制御（override）と OS 環境変数を保護する protected セットを実装。
    - 必須環境変数チェック用のヘルパー _require() を実装。
    - 設定クラス Settings を提供（インターフェース経由で設定を取得）:
      - J-Quants、kabuステーション、Slack、データベースパス（duckdb/sqlite）、システム設定（KABUSYS_ENV / LOG_LEVEL）などのプロパティを提供。
      - KABUSYS_ENV と LOG_LEVEL の許容値チェック（不正な値は ValueError）。
      - is_live / is_paper / is_dev のブール判定プロパティ。
- データレイヤー（DuckDB）スキーマ定義と初期化機能を追加
  - src/kabusys/data/schema.py
    - 3層構造（Raw / Processed / Feature）と Execution レイヤーを想定したテーブル定義を実装。
    - 生データ（raw_prices, raw_financials, raw_news, raw_executions）用テーブルを追加。
    - 整形済みデータ（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）を追加。
    - 特徴量・AI スコア（features, ai_scores）用テーブルを追加。
    - 発注・約定・ポジション管理（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）用テーブルを追加。
    - 各種 CHECK 制約、主キー、外部キーを含めた堅牢な DDL を定義（NULL制約や値範囲チェック等）。
    - 頻出クエリを想定したインデックスを定義（銘柄×日付スキャンやステータス検索等）。
    - init_schema(db_path) 関数を提供:
      - DuckDB 接続を作成し（":memory:" 対応）、親ディレクトリを自動作成して全テーブル・インデックスを作成（IF NOT EXISTS により冪等）。
    - get_connection(db_path) 関数を提供（既存 DB へ接続。スキーマ初期化は行わない）。
- 監査ログ（トレーサビリティ）モジュールを追加
  - src/kabusys/data/audit.py
    - シグナル→発注→約定のトレーサビリティを保証する監査テーブル群を定義。
    - signal_events（戦略が生成したシグナルログ）、order_requests（冪等キー order_request_id を持つ発注要求ログ）、executions（証券会社からの約定ログ）を実装。
    - すべての TIMESTAMP を UTC で保存する方針を明記し、init_audit_schema() 実行時に SET TimeZone='UTC' を実行。
    - order_requests のチェック制約により order_type に応じた必須価格フィールド（limit_price / stop_price）の整合性を担保。
    - 各テーブルに created_at / updated_at 等を配置し監査証跡を保持。
    - 監査用インデックス群を定義（検索性・参照整合性を考慮）。
    - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加初期化、専用 DB の初期化両対応）。
- パッケージ構成（空の初期化モジュール）
  - src/kabusys/data/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/monitoring/__init__.py を配置（将来的な拡張のためのプレースホルダ）。

Design / Notes
- DDL は多くの CHECK 制約や FK 制約、PRIMARY KEY を含み、データ整合性を重視。
- ほとんどの CREATE 文は IF NOT EXISTS を使用し、スキーマ初期化関数は冪等に設計。
- DuckDB を利用し、インメモリ（":memory:"）モードをサポート。DB ファイルの親ディレクトリは自動作成。
- 監査ログは削除しない前提（ON DELETE RESTRICT を採用）で、発注・約定の完全な追跡性を保証。
- order_requests.broker_order_id の一意索引については、DuckDB の NULL の取り扱い（NULL は重複扱いされる）に注意した設計。

Fixed
- なし

Changed
- なし

Deprecated
- なし

Removed
- なし

Security
- なし

今後の TODO（抜粋）
- 実際の kabu ステーション / J-Quants / Slack との連携実装（API クライアント、認証フローなど）。
- execution / strategy 層の具体的な実装（シグナル生成、ポートフォリオ最適化、発注フロー制御）。
- マイグレーション戦略（スキーマ変更時の移行ツール）。
- 単体テスト、統合テスト、CI 設定および .env 取り扱いのセキュリティ確認。

お問い合わせ・貢献
- バグ報告や機能提案はリポジトリの Issue にて受け付けてください。