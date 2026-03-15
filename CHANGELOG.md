CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------

- （今後のリリースで記載）

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの骨組みを実装。
- パッケージ公開情報
  - src/kabusys/__init__.py にてバージョンを設定（0.1.0）および公開モジュールを __all__ で定義。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルの柔軟なパーサを実装:
    - export KEY=val 形式対応
    - シングル／ダブルクォートとバックスラッシュによるエスケープ処理対応
    - コメント（#）の取り扱い（クォート内無視 / 非クォートでは直前が空白の場合にコメントとする等）
    - 無効行のスキップ
  - ファイル読み込み時の上書き制御（override）と OS 環境変数を保護する protected ロジック。
  - Settings クラスを提供し、環境変数からアプリ設定を取得:
    - J-Quants, kabuステーション, Slack, DBパス（DuckDB/SQLite）などのプロパティを実装
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のショートカットプロパティ
  - 必須キー未設定時には明確な ValueError を送出する _require() を実装。

- データスキーマ（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマをレイヤー別（Raw / Processed / Feature / Execution）に定義。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー: features, ai_scores
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに整合性チェック（CHECK 制約／PRIMARY KEY／FOREIGN KEY）を付与。
  - 検索パフォーマンスを考慮したインデックス群を定義（銘柄×日付スキャン、ステータス検索など）。
  - init_schema(db_path) を提供:
    - 指定パスの親ディレクトリ自動作成
    - ":memory:" によるインメモリ DB サポート
    - DDL／インデックスの冪等的適用
  - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）。

- 監査ログ（src/kabusys/data/audit.py）
  - DataPlatform に基づく監査テーブル群を実装（トレーサビリティを UUID ベースで確保）。
  - 主要テーブル:
    - signal_events（戦略が生成したシグナルログ、棄却やエラーも永続化）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う。order_type に依る CHECK 制約あり）
    - executions（証券会社から返される約定ログ。broker_execution_id をユニーク冪等キーとして記録）
  - 監査用インデックス群を定義（戦略別検索、status キュー検索、broker_order_id による紐付け等）。
  - init_audit_schema(conn) を提供:
    - 与えた DuckDB 接続に監査テーブルを追加（冪等）
    - すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行
  - init_audit_db(db_path) を提供（監査専用 DB を作成して初期化）。

- ドキュメント的注記
  - 各モジュールに docstring を追加し、DataSchema.md / DataPlatform.md 等の設計文書を参照する旨を明記。

Security
- 監査テーブルの設計で TIMESTAMP を UTC に統一して保存（時刻関連の解釈差異を低減）。
- OS 環境変数の上書きを防ぐ保護ロジックを .env 読み込みに導入。

Notes / Design highlights
- DDL は可能な限り CHECK 制約・FK・PRIMARY KEY を用いてデータ整合性を担保。
- テーブル作成・インデックス作成は冪等的に行われるため、繰り返し初期化しても安全。
- 発注系では冪等キー（order_request_id）や broker_execution_id の扱いにより二重発注や重複約定を防止する設計を採用。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Security
- なし（既述の設計上の配慮を含む）

----

（注）本 CHANGELOG はリポジトリ内の現状コードを基に変更点を推測して作成しています。将来のコミットやリリース時には実際の差分に基づいて更新してください。