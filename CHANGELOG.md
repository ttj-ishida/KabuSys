# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、このCHANGELOGはソースコードから推測して作成しています。実装上の詳細やリリース日等は、実際のプロジェクト運用に合わせて調整してください。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回公開リリース。本パッケージは日本株の自動売買プラットフォーム向けに設計されたライブラリ群を含み、データ取得・保存・ETL・品質チェック・監査ログの初期実装を提供します。

### Added
- パッケージ基盤
  - パッケージメタ情報: kabusys/__init__.py にバージョン `0.1.0` を追加。
  - モジュール分割: data, strategy, execution, monitoring を公開モジュールとして定義。

- 環境設定・読み込み機能 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮。
    - コメント判定（クォート無しで '#' の直前がスペース/タブの場合はコメント扱い）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム設定（環境種別、ログレベル等）をプロパティで取得可能。
  - 必須環境変数未設定時は明確なエラーメッセージで ValueError を投げる `_require` 実装。
  - 環境名・ログレベルのバリデーション（許容値の定義）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装し、以下データを取得可能:
    - 株価日足 (OHLCV)
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - 設計/実装の主要ポイント:
    - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` 実装。
    - リトライロジック（指数バックオフ、最大3回）を実装。対象はネットワーク系・一部 HTTP ステータス（408, 429, 5xx）。
    - 401 Unauthorized 受信時はリフレッシュトークンで ID トークンを自動更新して1回リトライ。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止するトレーサビリティを確保。
    - DuckDB へ保存する際は冪等性を保つため INSERT ... ON CONFLICT DO UPDATE を使用。
  - ユーティリティ関数:
    - JSON デコード失敗時の明確な例外化。
    - `_to_float` / `_to_int` により入力データの安全な数値変換を実装（不正値は None）。
  - 主要 API 関数:
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform の3層（Raw / Processed / Feature）と Execution 層を想定したスキーマ定義を実装。
  - テーブル定義（CREATE TABLE IF NOT EXISTS）を多数追加:
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義を追加し、頻発クエリのパフォーマンスを想定したインデックスを作成。
  - init_schema(db_path) により DB ファイルのディレクトリ自動作成と全DDLの実行を行い、稼働準備済みの接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得できるユーティリティを追加。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL エントリポイント run_daily_etl を実装:
    - 処理フロー: カレンダー取得 → 株価差分取得（バックフィル可能） → 財務差分取得 → 品質チェック（任意）
    - 各ステップは独立したエラーハンドリング（1ステップ失敗でも他は続行）。
    - 差分更新用ユーティリティ: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 営業日調整ヘルパー `_adjust_to_trading_day`（カレンダー未取得時はフォールバックあり）。
    - run_prices_etl, run_financials_etl, run_calendar_etl の個別ジョブを追加。デフォルトのバックフィル日数やカレンダールックアヘッドを設定可能。
  - ETL 結果を格納するデータクラス ETLResult を追加（品質問題やエラー一覧を集約）。
  - 品質チェックは外部モジュール quality と連携して結果を収集。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注→約定の流れを UUID 連鎖で追跡可能にする監査テーブルを実装:
    - signal_events（戦略が生成したシグナル記録）
    - order_requests（発注要求。order_request_id を冪等キーとして利用）
    - executions（証券会社の約定情報を記録。broker_execution_id に UNIQUE 制約）
  - 各種制約・チェック（ENUM 相当の CHECK、必須カラムの制約、外部キー）を定義。
  - init_audit_schema(conn) により既存接続へ監査テーブルとインデックスを追加（UTC タイムゾーンを設定）。
  - init_audit_db(db_path) で専用 DB を作成・初期化するユーティリティを追加。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを追加（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は除外）。
    - スパイク検出 (check_spike): 前日比の変動率が閾値（デフォルト 50%）を超える急騰・急落を検出。LAG ウィンドウを用いる。
    - （重複チェック・日付不整合検出の設計は言及されているが、実装状況はコード片から部分的に確認。）
  - 各チェックは SQL を用いて実行し、問題は QualityIssue リストとして返す（Fail-Fast ではなく全件収集）。

### Changed
- （初回リリースのため過去の変更はなし）

### Fixed
- （初回リリースのため既知のバグ修正履歴はなし）

### Deprecated
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- HTTP タイムアウトやトークンリフレッシュの扱いなど、外部 API 呼び出し周りで基本的な堅牢化（タイムアウト、リトライ、レート制御）を実装。

### Notes / Limitations / TODO
- strategy/ と execution/ のパッケージは __init__.py が存在するのみで具象実装は含まれていません。戦略ロジックや発注実行ロジックは今後実装予定。
- quality モジュール内のチェックは主要な項目を実装しているが、追加のチェック（重複、将来日・営業日外データの詳細判定など）がドキュメントに記載されているため拡張の余地あり。
- DuckDB を利用するため、運用環境に duckdb パッケージが必要です。
- jquants_client は urllib を用いた実装のため、より高度な HTTP クライアント（例: requests, httpx）への差し替えや非同期対応は将来検討可能。
- 日付/時刻は UTC を基本とする設計。アプリ側での UTC 時間扱いに留意してください。
- 自動 .env ロードはプロジェクトルートの検出に .git または pyproject.toml を使用します。配布後の挙動に注意。

---

参照:
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/