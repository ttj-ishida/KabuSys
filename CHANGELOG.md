# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」のフォーマットに準拠し、安定版・後方互換性・変更内容の可視化を目的としています。

最新の変更履歴はリリースの順に記載しています。

## [Unreleased]
- （現在のコードベースは初期リリースとして v0.1.0 を含みます。今後の変更はここに追記してください）

## [0.1.0] - 2026-03-16
初回公開リリース。本リリースは日本株自動売買プラットフォーム（KabuSys）の基盤的なモジュール群を実装しています。以下の主要機能・設計要素を含みます。

### Added
- パッケージメタデータ
  - パッケージ version を `__version__ = "0.1.0"` として設定。
  - パッケージの公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して判定。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化:
    - `export KEY=val` 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなし行での inline コメント処理（直前が空白／タブの `#` をコメントとみなす）。
  - 必須環境変数取得用の `_require()` と、env 値検証:
    - KABUSYS_ENV は `development` / `paper_trading` / `live` のみ許容。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
  - 各種設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack トークン/チャンネル, DB パス等）。

- データクライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を順守（_RateLimiter）。
  - 再試行（リトライ）ロジック:
    - 指数バックオフ（base=2.0）、最大 3 回試行。
    - ステータス 408, 429 および 5xx 系をリトライ対象。
    - 429 の場合は `Retry-After` ヘッダを優先して待機時間を決定。
    - ネットワーク例外（URLError, OSError）にも再試行。
  - 認証トークン管理:
    - リフレッシュトークンから ID トークンを取得する `get_id_token()`（POST）。
    - モジュールレベルで id_token をキャッシュし、401 を受けた場合は自動で 1 回だけリフレッシュして再試行（無限再帰防止）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - 全て INSERT ... ON CONFLICT DO UPDATE を使用し重複を排除
    - 取得時刻（fetched_at）は UTC ISO 形式で記録
  - 値変換ユーティリティ:
    - _to_float: 空値や変換失敗で None を返す
    - _to_int: "1.0" のような float 文字列を整数化し、小数部が非ゼロのものは None を返す（意図しない切り捨て防止）

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層＋監査用テーブルを含むスキーマ定義を追加。
  - 主要テーブル例:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）や型チェックを明示。
  - 頻出クエリを考慮したインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成・DDL 実行（冪等）。
  - get_connection(db_path) を提供（既存 DB に接続）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリポイント run_daily_etl を実装（市場カレンダー、株価、財務の差分取得・保存・品質チェック）。
  - 差分更新設計:
    - 最終取得日からの差分取得、自動で未取得範囲を計算。
    - デフォルトのバックフィル日数: 3 日（後出し修正を吸収）。
    - 市場カレンダーの先読みデフォルト: 90 日（営業日調整に使用）。
    - 初回ロード用の最小データ日付: 2017-01-01。
  - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）。
  - ETLResult dataclass:
    - 実行結果（fetched / saved 数、品質問題、エラーリスト）を格納・変換するユーティリティを提供。
  - 品質チェック（quality モジュール）をオプションで実行。デフォルトで有効。

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティを担保する監査テーブルを追加。
  - 主なテーブル:
    - signal_events（戦略が生成したシグナルログ: decision, reason, strategy_id 等）
    - order_requests（冪等キー order_request_id を持つ発注要求, 注文種別ごとの価格必須チェックを含む）
    - executions（証券会社から返された約定情報、broker_execution_id を冪等キーとして保持）
  - UTC タイムゾーン（SET TimeZone='UTC' を実行）を初期化時に設定。
  - 監査専用初期化 API:
    - init_audit_schema(conn)
    - init_audit_db(db_path)（専用 DB を作成して初期化）
  - 各種インデックスを定義し検索性能を考慮。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass により各チェック結果を構造化。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL を検出、重大度は error）
    - check_spike: 前日比のスパイク（デフォルト閾値 50%）検出。LAG ウィンドウを使って前日比を計算。
  - 各チェックは全件収集型で、大量の問題を一括で検出して呼び出し元が措置を判断可能。

- パッケージ構造
  - data, strategy, execution, monitoring のトップレベルパッケージを配置（strategy, execution は現時点で初期ファイル/プレースホルダ）。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Notes / その他
- 全体的な設計方針:
  - 冪等性（ON CONFLICT DO UPDATE）・トレーサビリティ（UUID 連鎖・created_at）・UTC の一貫保存を重視。
  - ETL は Fail-Fast ではなく、問題を収集して呼び出し側が判断する方式を採用。
  - ネットワーク/API 呼び出しはレート制御とリトライを組み合わせ、堅牢性を確保。
- ドキュメント参照:
  - 各モジュールの docstring に設計目的・参照ドキュメント（DataPlatform.md, DataSchema.md 等）への言及あり。実運用前に該当設計資料を参照してください。

今後のリリースでは、戦略実装（strategy.*）、注文実行のブローカー統合（execution.*）、監視（monitoring）、テストカバレッジ、CLI/API の追加などを予定しています。