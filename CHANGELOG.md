# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現状から推測して作成した初回リリース向けの変更履歴です。

フォーマットの慣例:
- Unreleased: 次回リリースに向けた未リリース項目（現状は空）
- 各バージョンはリリース日を付記

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョン (0.1.0)、公開モジュール一覧を定義。

- 設定/環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機構を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出ロジック: .git または pyproject.toml を探索して自動検出
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）
  - .env 行パーサーを実装（コメント、export プレフィックス、クォート／エスケープ対応）
  - Settings クラスを追加し、型付きプロパティで主要設定を提供:
    - J-Quants / kabu ステーション / Slack トークンやチャネル
    - データベースファイルパス（DuckDB / SQLite）
    - 環境（development / paper_trading / live）とログレベルのバリデーション
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - HTTP ユーティリティと堅牢なリトライ戦略を実装
    - 固定レートリミット (120 req/min) に基づくスロットリング
    - 指数バックオフによるリトライ（最大 3 回）
    - ステータス 401 を受けた場合にリフレッシュトークンから id_token を自動再取得して 1 回リトライ
    - 408 / 429 / 5xx 系でのリトライ対応（429 の Retry-After ヘッダ尊重）
  - ページネーション対応（pagination_key を利用）およびモジュールレベルの id_token キャッシュ
  - DuckDB への保存関数（冪等）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を用いた重複排除（冪等性保証）
  - ユーティリティ関数: _to_float / _to_int（安全な型変換）

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataPlatform の 3 層（Raw / Processed / Feature）と Execution 層を想定した詳細なテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を設定
  - インデックス定義（主要クエリパターンに対応）
  - init_schema(db_path) によりディレクトリ作成 -> テーブル作成（冪等） -> DuckDB 接続を返却
  - get_connection(db_path) で既存 DB への接続を取得可能

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリ run_daily_etl を実装（カレンダー取得 → 株価 → 財務 → 品質チェック）
  - 差分更新ロジック:
    - DB の最終取得日を基に差分日付を計算し、backfill_days により過去分を再取得して API の後出し修正に対応
    - デフォルトバックフィル 3 日
  - カレンダー先読み（デフォルト 90 日）による営業日の補正
  - 各 ETL ジョブを独立して実行し、個別に例外ハンドリングして他処理は継続する設計（Fail-Fast 回避）
  - ETL 実行結果を ETLResult 型で返却（フェッチ数、保存数、品質問題、エラー一覧などを保持）
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブを提供

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までを UUID 連鎖でトレースする監査テーブル群を実装
    - signal_events, order_requests, executions
  - 発注の冪等キー (order_request_id) をサポート
  - すべての TIMESTAMP を UTC 保存するための SET TimeZone='UTC' を適用
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

- データ品質チェック（kabusys.data.quality）
  - 一連の品質チェック関数を実装（QualityIssue 型を返却）
    - check_missing_data: raw_prices の必須カラム（OHLC）欠損検出（重大度: error）
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）
    - （設計文書に沿った重複・日付不整合チェックの枠組みを想定）
  - 各チェックはサンプル行を含む QualityIssue のリストを返し、Fail-Fast ではなく問題を全件収集する方針

### Changed
- N/A（初回リリースのため既存からの変更なし）

### Fixed
- N/A（初回リリースのため既存からの修正なし）

### Security
- 認証トークンは Settings を通して環境変数から取得する設計。トークンの環境変数未設定時は明示的に例外を投げて早期検出。

### Notes / Implementation details
- jquants_client は同期的な urllib ベース実装で、タイムアウトや HTTPError を丁寧に扱う設計。非同期実装は今後の改善対象。
- DuckDB スキーマは外部キーや CHECK 制約を多用してデータ整合性を担保。初期化は冪等で何度実行しても安全。
- ETL は品質チェックでエラーが発生しても処理を継続し、呼び出し元で対応を決める責務分離を採用。
- .env パーサーは quoted value のエスケープ処理やコメント扱いの細かい挙動に対応しているため、一般的な .env フォーマットに堅牢。

### Known limitations / TODO
- テストコードや CI の設定は含まれていない（自動テストの追加が推奨）。
- 非同期/並列取得やより高度なスループット最適化は未実装（現行は固定レートスロットリング）。
- 外部 API や証券会社との接続部分（kabu 実装、Slack 通知など）は設定と基盤を備えているが、実際のブローカー連携層は今後の実装予定。
- 一部の品質チェック（重複・日付不整合）の具体的な SQL 実装は設計に基づく追加実装の余地あり。

---

（注）本 CHANGELOG は現行のソースコードを解析して推測に基づき作成しています。実際の開発履歴や意図とは差異がある可能性があります。必要に応じて受け取った要件や実際のコミット履歴に合わせて調整してください。