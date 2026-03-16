CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を管理します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]: https://example.com/kabusys/compare/HEAD...v0.1.0

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコア機能を実装しました。以下はコードベースから推測した主要な追加点と設計上の特徴です。

Added
- パッケージの初期構成
  - kabusys パッケージとサブモジュール（data, strategy, execution, monitoring）を公開。 (src/kabusys/__init__.py)
  - バージョン: 0.1.0

- 環境変数・設定管理
  - .env ファイル（.env, .env.local）および環境変数からの自動読み込み機能を実装。プロジェクトルート検出は .git または pyproject.toml を基準にし、CWD に依存しない設計。 (src/kabusys/config.py)
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱い等に対応。
  - protected（既存 OS 環境変数）を維持する上書き制御をサポート。
  - Settings クラスで主要設定をプロパティで公開（J-Quants / kabu API / Slack / DB パス / 環境区分 / ログレベル等）。入力値検証（KABUSYS_ENV, LOG_LEVEL）と利便性プロパティ（is_live, is_paper, is_dev）を提供。
  - デフォルトの DB パス設定（DuckDB, SQLite）と Path 変換をサポート。

- J-Quants API クライアント
  - API クライアントを実装し、日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得可能。 (src/kabusys/data/jquants_client.py)
  - レート制御: 固定間隔スロットリングにより 120 req/min を遵守する RateLimiter を実装。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx・ネットワークエラーに対応。429 の場合は Retry-After ヘッダを優先。
  - 認証: リフレッシュトークンから ID トークン取得用関数 (get_id_token) と、401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有。
  - ページネーション対応: fetch_* 関数は pagination_key を用いて全ページを取得。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead Bias のトレースを可能に。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を担保し、主キー欠損行はスキップしてログ出力。

- DuckDB スキーマ定義・初期化
  - 3 層（Raw / Processed / Feature）＋Execution 層 を意識したスキーマ定義を提供し、ETL と実行ログを永続化するテーブル群を用意。 (src/kabusys/data/schema.py)
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル
  - features, ai_scores 等の Feature テーブル
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル
  - 頻出クエリ向けのインデックス定義も追加。
  - init_schema(db_path) による DB 初期化とテーブル作成（親ディレクトリ自動作成、インメモリ対応 ":memory:"）を提供。get_connection() で既存 DB に接続可能。

- ETL パイプライン
  - 差分更新・バックフィル・品質チェックを含む日次 ETL の実装。 (src/kabusys/data/pipeline.py)
  - run_daily_etl: 市場カレンダー取得 → 営業日に調整 → 株価差分 ETL → 財務差分 ETL → 品質チェック の順で実行。各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）。
  - 差分ロジック: DB の最終取得日から未取得範囲を算出し、デフォルトで backfill_days=3 を用いて数日前から再取得して API の後出し修正を吸収。
  - カレンダーはデフォルトで target 日から先読み（lookahead_days=90 日）を行い、ETL 内で営業日判定に使用。
  - ETL 結果を ETLResult dataclass で集約。品質問題は severity によって判定可能（has_quality_errors 等のユーティリティ提供）。

- データ品質チェック（quality）
  - データ品質モジュールを実装し、少なくとも欠損データ検出（check_missing_data）とスパイク検出（check_spike）のチェックを提供。 (src/kabusys/data/quality.py)
  - check_missing_data: raw_prices の OHLC 欠損を検出し、サンプルと件数を返す（重大度 error）。
  - check_spike: LAG ウィンドウで前日終値を取得し、閾値（デフォルト 50%）を超える変動を検出してサンプルと件数を返す。
  - QualityIssue dataclass によりチェック名・テーブル・severity・詳細・サンプル行を返却する設計。品質チェックは Fail-Fast ではなく全件収集する方針。

- 監査ログ・トレーサビリティ（audit）
  - シグナルから約定までの監査テーブル群を実装。トレーサビリティは UUID 連鎖で実現。 (src/kabusys/data/audit.py)
  - signal_events（戦略が生成した全シグナルの記録）、order_requests（冪等キー付きの発注要求）、executions（実際の約定ログ）を定義。
  - order_requests のチェック制約（order_type に応じた価格必須/禁止）やステータス遷移管理、すべての TIMESTAMP を UTC で保存する運用（SET TimeZone='UTC'）を明示。
  - init_audit_schema / init_audit_db を提供し、既存接続へ監査テーブルを追加可能。

- ユーティリティ関数
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、空文字や不正値を None に変換。_to_int は "1.0" のような float 文字列を安全に処理し、小数部が非ゼロの場合は None を返す等のルールを実装。
  - DuckDB 接続の作成と初期化関数群を提供（init_schema, get_connection, init_audit_db）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 認証トークンの自動リフレッシュとモジュールレベルのトークンキャッシュを実装。自動トークン更新時の無限再帰を防ぐ設計（allow_refresh フラグ）。
- .env 読み込み時に既存 OS 環境変数を保護する protected 機構を採用。

Notes / 実装上の注意
- jquants_client の _request は urllib を直接使用しており、http タイムアウトや HTTPError/URLError を明示的に扱う実装です。外部 HTTP クライアント（requests 等）に差し替え可能な抽象化は現状なし。
- DuckDB の ON CONFLICT を用いたアップサートやインデックス定義により冪等性と検索性能を考慮している。
- pipeline.run_daily_etl は品質チェックで検出された問題を収集して戻すが、最終的な停止判断（ETL を止めるかどうか）は呼び出し元で行う設計。

今後の改善案（推奨）
- quality モジュールに重複チェック・日付不整合チェックなどの追加実装（ドキュメントに記載あり）。
- ETL の監査ログ追加（ETLResult を DB に保存）や通知（Slack 連携）機能の統合。
- 外部 HTTP 呼び出しの抽象化とユニットテスト用のモック容易化。
- 大量データ取得時の並列化・スロットリング最適化（ただし API レート制限に注意）。

[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0