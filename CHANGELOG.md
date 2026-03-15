Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に従っています。
頻繁な非互換な変更はメジャーバージョンを上げて表記します。

1.0.0 より前の慣例: 初期リリースを 0.1.0 として記録します。

## [Unreleased]

（現時点での未リリース変更はありません）

## [0.1.0] - 2026-03-15

追加 (Added)
- パッケージの初期リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py にて定義）。
  - エクスポートモジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を自動読み込み。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を基準）。これによりカレントワーキングディレクトリに依存しない自動読み込みが可能。
  - .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化オプション: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途を想定）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル / ダブルクォート内のバックスラッシュエスケープを正しく解釈。
    - インラインコメント処理（クォート内は無視、クォート外は '#' の直前が空白またはタブの場合にコメントと判定）。
    - 無効行やコメント行は無視。
  - .env 読み込み時の保護機能:
    - OS 環境変数を protected として扱い、必要に応じて .env の上書きを制御。
  - Settings クラスを提供（settings = Settings() で使用可能）:
    - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティを定義（必須環境変数は _require() で検証して不在時は ValueError を送出）。
    - KABUSYS_ENV の許容値検証（development, paper_trading, live）。
    - LOG_LEVEL の許容値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - Path 型での duckdb/sqlite パスの返却、ユーザーディレクトリ展開対応。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- DuckDB ベースのスキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - データレイヤを明確に区分（Raw / Processed / Feature / Execution）。
  - 多数のテーブル DDL を定義（例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各カラムに対する制約 (CHECK, PRIMARY KEY, FOREIGN KEY) を多数導入し、データ整合性を強化。
  - 頻出クエリに備えたインデックス定義を追加（例: 銘柄×日付インデックス、ステータス検索、外部キー参照用インデックスなど）。
  - init_schema(db_path) を公開:
    - 指定された DuckDB ファイルを初期化し、全テーブルとインデックスを作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" を指定してインメモリ DB を利用可能。
    - 初回初期化やスキーマ追加に対応。
  - get_connection(db_path) を公開:
    - 既存の DuckDB へ接続を返す（スキーマ初期化は行わない。初回は init_schema() を使用する旨を明記）。

- 監査ログ／トレーサビリティモジュールを追加（src/kabusys/data/audit.py）。
  - シグナル→発注→約定までを UUID 連鎖で完全追跡する監査用テーブルを定義。
  - トレーサビリティ階層と設計原則（冪等キー、削除禁止（ON DELETE RESTRICT）、UTC タイムゾーン、created_at/updated_at の扱い等）をドキュメント化。
  - テーブル定義:
    - signal_events（戦略が生成したシグナルログ。拒否された/棄却されたシグナルも記録）
    - order_requests（発注要求、order_request_id が冪等キー。order_type ごとの CHECK 制約で価格の必須/禁止を担保）
    - executions（証券会社から返る約定ログ。broker_execution_id をユニーク制約で冪等性確保）
  - 監査専用インデックス群を定義（シグナル検索、戦略別検索、status によるキュー検索、broker_order_id での結合等を想定）。
  - init_audit_schema(conn) を公開:
    - 既存の DuckDB 接続に監査テーブルとインデックスを追加（冪等）。
    - 実行時に TimeZone を UTC に設定して TIMESTAMP を UTC 保存することを保証。
  - init_audit_db(db_path) を公開:
    - 監査ログ専用の DuckDB ファイルを作成して初期化した接続を返す（親ディレクトリ自動作成、":memory:" 対応）。

- パッケージのサブモジュールプレースホルダを追加。
  - src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/data/__init__.py、src/kabusys/monitoring/__init__.py（現時点では空の初期化ファイル。将来の機能追加を想定）。

変更 (Changed)
- （初期リリースのため該当なし）

修正 (Fixed)
- （初期リリースのため該当なし）

削除 (Removed)
- （初期リリースのため該当なし）

注意事項 / 備考
- DuckDB を利用するため、実行環境に duckdb パッケージが必要です。
- .env の自動読み込みはプロジェクトルート判定に依存するため、パッケージ配布後も正しく動作する設計。ただしプロジェクトルートが見つからない場合は自動ロードはスキップされます。
- 監査ログは削除しない前提のスキーマ設計（ON DELETE RESTRICT 等）となっており、運用上はログの肥大化・バックアップ方針を検討してください。
- Settings の必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出します。 .env.example を参考に .env を作成してください。

将来の予定（例）
- strategy / execution / monitoring サブパッケージの実装（シグナル生成、ポートフォリオ管理、発注実行、監視アラート等）。
- マイグレーション／スキーマバージョン管理機能の追加。
- テストカバレッジと CI の整備。

--- 
（注）上記は提供されたソースコードから推測して作成した変更履歴です。実際のリリースノートにはリリース手順や依存関係のバージョン情報、既知の問題などを補足することをお勧めします。