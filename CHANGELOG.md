KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ja/ に準拠しています。

履歴
====

v0.1.0 - 2026-03-16
-------------------

Added
- 初回リリース: KabuSys - 日本株自動売買システムのコアライブラリを追加。
  - パッケージ構成
    - kabusys: パッケージルート（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring（strategy/execution/monitoring の __init__ は現状空）。
  - 設定管理 (kabusys.config)
    - .env ファイルまたは環境変数からの設定自動読み込みを実装。プロジェクトルートは .git または pyproject.toml を探索して決定するため、CWD に依存しない動作を実現。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env と .env.local の読み込み順序を実装（OS 環境 > .env.local > .env）。.env.local は override=True で .env 上書きを許可。ただし OS 環境変数は保護（protected）され、上書きされない。
    - .env パーサは以下の取り扱いに対応:
      - 空行・コメント行（#）を無視
      - export KEY=val 形式に対応
      - シングル／ダブルクォート内のバックスラッシュエスケープを正しく処理
      - クォート無しの値では、行内のコメント判定を直前がスペース/タブの場合に限る（より実運用寄りの挙動）
    - Settings クラスを提供。J-Quants トークン、kabu API パスワード、Slack トークン／チャンネル、DB パス等の設定プロパティを公開。KABUSYS_ENV と LOG_LEVEL の検証（許可値チェック）や is_live / is_paper / is_dev ヘルパーを実装。
    - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

  - データ層 (kabusys.data)
    - J-Quants API クライアント (data.jquants_client)
      - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得 API を実装。
      - 設計上の特徴:
        - API レート制限を順守する固定間隔スロットリング（120 req/min）を組み込み（RateLimiter）。
        - リトライロジック（指数バックオフ、最大3回）。408/429/5xx 系を再試行対象、429 の場合は Retry-After ヘッダを優先。
        - 401 受信時はリフレッシュトークンで自動的に id_token をリフレッシュして1回リトライ（無限再帰防止のため allow_refresh フラグを利用）。
        - ページネーション対応（pagination_key の連続取得）と、モジュールレベルの id_token キャッシュ共有（ページ間でトークンを使い回し）。
        - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead Bias を防止可能に。
        - DuckDB へ保存する際は冪等性を考慮（INSERT ... ON CONFLICT DO UPDATE）。
      - HTTP ユーティリティはタイムアウト、JSON デコード例外ハンドリングを備える。
      - ユーティリティ関数 _to_float/_to_int は入力の柔軟な変換と不正値時の None 返却（"1.0" のような float 文字列を int に変換するが小数部が非ゼロなら None）を行う。
      - fetch_* 関数群: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - save_* 関数群: save_daily_quotes, save_financial_statements, save_market_calendar（各関数は PK 欠損行のスキップ・ログ出力・更新件数を返す）。

    - DuckDB スキーマ (data.schema)
      - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
      - 主なテーブル:
        - Raw: raw_prices, raw_financials, raw_news, raw_executions
        - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
        - Feature: features, ai_scores
        - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
      - 各テーブルに適切な型チェック制約・PRIMARY KEY を設定（例: prices_daily の low <= high など）。
      - 頻出クエリ向けのインデックス群を用意（code×date スキャンやステータス検索等）。
      - init_schema(db_path) でディレクトリ作成・全テーブル作成を行う（冪等）。get_connection(db_path) で既存 DB に接続。

    - 監査ログ (data.audit)
      - シグナル→発注→約定のトレーサビリティを確保する監査用テーブルを実装（signal_events, order_requests, executions）。
      - 設計上の特徴:
        - UUID ベースの ID（signal_id, order_request_id 等）を想定し、order_request_id は冪等キーとして機能。
        - order_requests の order_type に応じたチェック制約（limit/stop の必須価格など）を実装。
        - ステータス遷移モデル（pending → sent → filled / partially_filled / cancelled / rejected / error）を想定した列定義。
        - executions の broker_execution_id をユニーク（証券会社提供の約定 ID を冪等キーとして扱う）。
        - すべての TIMESTAMP を UTC で保存するため init_audit_schema 内で SET TimeZone='UTC' を実行。
      - init_audit_schema(conn) / init_audit_db(db_path) を提供。

    - データ品質チェック (data.quality)
      - DataPlatform.md のガイドに基づく品質チェック群を実装。
      - 提供するチェック:
        - 欠損データ検出 (check_missing_data): raw_prices の open/high/low/close 欠損検出（volume は除外）。
        - スパイク検出 (check_spike): 前日比の絶対変動率が閾値（デフォルト 0.5 = 50%）を超える急騰・急落の検出（LAG を使用）。
        - 重複チェック (check_duplicates): raw_prices の主キー (date, code) 重複検出。
        - 日付不整合 (check_date_consistency): 未来日付検出と market_calendar との整合性チェック（非営業日のデータ検出）。market_calendar テーブル未存在時はスキップ。
      - QualityIssue dataclass により、発見された問題の一覧（チェック名・テーブル・重大度・詳細・サンプル行）を返却。
      - run_all_checks(conn, ...) で一括実行し、エラー／警告数をログ出力。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Security
- 環境変数の上書き制御を導入し、OS 環境変数は .env/.env.local による上書きから保護。

Notes / 注意事項
- 本バージョンはライブラリ初版。API クライアントはネットワーク依存のため、実運用前に接続・認証情報・レート制限の挙動確認を推奨。
- DuckDB スキーマの変更は互換性に注意（初回は init_schema を実行して DB を作成してください）。監査ログは削除を想定していないため、FK 制約や ON DELETE ポリシーに注意。
- strategy / execution / monitoring の各モジュールは初期化ファイルのみで実装は最小限。戦略実装や実行エンジンは今後追加予定。

今後の予定（例）
- 発注ライブラリ（kabu ステーションとの連携）と execution 層の実装
- 戦略テンプレート・バックテスト機能追加
- モニタリング（Slack 通知や Prometheus Exporter 等）の実装・統合
- 単体テスト、CI の整備および型チェックの強化

--- 

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて責任者による確認・修正を行ってください。）