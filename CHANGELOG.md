# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株向けの自動売買プラットフォームの基本コンポーネントを実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開サブパッケージ指定: data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - 自動読み込みの探索はパッケージ配置を考慮して .git または pyproject.toml を基準にプロジェクトルートを特定。
  - .env/.env.local の読み込み順（OS環境変数 > .env.local > .env）および KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val、クォート文字列（エスケープ処理含む）、インラインコメントなどを考慮した .env パーサーを実装。
  - 必須環境変数取得時に ValueError を投げる _require、および settings オブジェクトを提供。各種設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別、ログレベル）をプロパティとして定義。
  - KABUSYS_ENV と LOG_LEVEL の検証（許可値チェック）を実装。is_live/is_paper/is_dev のヘルパープロパティを追加。
- データアクセス / J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装（株価日足、財務データ、JPX カレンダー）。
  - API レート制御（固定間隔スロットリング）を実装し、デフォルトで 120 req/min を遵守。
  - 冪等性・堅牢性のためのリトライロジック（指数バックオフ、最大 3 回。対象ステータス: 408, 429, 5xx）を実装。
  - 401 時の自動トークンリフレッシュを 1 回まで行う仕組みを実装（無限再帰を防止するフラグを採用）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）を実装。
  - DuckDB へ保存するための idempotent な save_* 関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装（ON CONFLICT DO UPDATE を利用）。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead bias を防止する設計思想を採用。
  - 入出力の型変換ユーティリティ（_to_float, _to_int）を追加。数値文字列の堅牢な扱い（"1.0"→1 等）や不正値の None 変換を行う。
- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform の3層（Raw / Processed / Feature）および Execution 層を想定したスキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブルを定義。
  - features, ai_scores などの Feature テーブルを定義。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など Execution 層テーブルを定義。
  - 頻出クエリ向けのインデックスを複数追加。
  - init_schema(db_path) による DB 初期化（親ディレクトリ自動作成、冪等実行）と get_connection を提供。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新ベースの ETL ワークフローを実装（差分判定、backfill、保存、品質チェックの一連処理）。
  - run_prices_etl / run_financials_etl / run_calendar_etl を実装。最終取得日からの差分自動算出と backfill_days による後出し修正吸収をサポート。
  - カレンダーは lookahead（デフォルト 90 日）で先読みし、営業日の調整に利用。
  - run_daily_etl をエントリポイントとして実装。処理は以下順で実行：市場カレンダー → 株価日足 → 財務データ → （オプション）品質チェック。個々のステップは独立してエラーハンドリングされ、1 ステップ失敗でも他が継続する設計。
  - ETL の結果を表す ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー等を格納）。
  - 品質チェック機能を外部モジュール（kabusys.data.quality）に委譲し、run_daily_etl から呼び出す仕組みを導入。
- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注要求→約定までを UUID 連鎖でトレース可能にする監査テーブル群を実装。
  - signal_events、order_requests（冪等キー order_request_id）、executions を定義。
  - すべての TIMESTAMP を UTC で運用するため init_audit_schema が SET TimeZone='UTC' を実行。
  - order_requests における order_type ごとのチェック制約（limit/stop/market の必須/不許可カラム制御）やステータス遷移を定義。
  - 監査用インデックスを複数追加（検索効率向上）。
  - init_audit_db により専用 DB の初期化と接続を提供。
- データ品質チェック (kabusys.data.quality)
  - 欠損データ検出（raw_prices の OHLC 欄の NULL 検出）を実装（check_missing_data）。
  - スパイク（急騰・急落）検出ロジックを実装（LAG ウィンドウを使用した前日比判定、check_spike、デフォルト閾値 50%）。
  - QualityIssue データクラスを導入し、チェック名・対象テーブル・重大度（error/warning）・サンプル行などを返却する設計。
  - 各チェックは Fail-Fast とせず、問題を全件収集して呼び出し元に返す方針。
  - DuckDB に対して SQL（パラメータバインド）で効率的に実行。

### Changed
- （該当なし：初回リリース）

### Fixed
- （該当なし：初回リリース）

### Security
- （該当なし：初回リリース）

### Notes / 補足
- J-Quants API クライアントはトークンのキャッシュをモジュールレベルで保持し、ページネーション間で共有することで不要な認証呼び出しを削減する設計。
- save_* 系関数は ON CONFLICT DO UPDATE を用いて冪等にデータを保存するため、再実行による重複挿入を防止。
- run_daily_etl の品質チェックはオプションでスキップ可能。品質チェックで error 相当の問題が検出されても ETL 自体は継続する（呼び出し元で停止判定できるように ETLResult に情報を返す）。
- .env のパースはシェル風の表記（export プレフィックス、クォーティング、エスケープ、インラインコメント）にある程度対応しているが、極端なケースは想定外の挙動となる可能性あり。

---

以上はコードベースから判断して作成した CHANGELOG です。追加のコミット履歴や実際の変更要望があれば、該当バージョンに追記して更新します。