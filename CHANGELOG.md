Keep a Changelog
=================

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - モジュール構成:
    - kabusys.config: 環境変数／設定管理（.env 自動読み込み、プロジェクトルート検出、必須キー取得、環境値検証等）
      - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定
      - .env のパースは export 構文、シングル／ダブルクォート、エスケープ、行内コメント（スペース／タブ判定）に対応
      - 自動ロード順序: OS 環境変数 > .env > .env.local（.env.local は上書き）
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
      - 必須環境変数取得用の _require を提供（未設定時は ValueError）
      - settings オブジェクトに主要設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）
      - KABUSYS_ENV と LOG_LEVEL の許容値検証（development / paper_trading / live、DEBUG/INFO/...）
  - kabusys.data パッケージ: データ取得・スキーマ・ETL・品質チェック・監査ログ
    - jquants_client:
      - J-Quants API クライアントを実装
      - 機能: 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダー取得
      - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）
      - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx とネットワークエラーに対してリトライ
      - 401 Unauthorized を受けた場合はリフレッシュトークンで 1 回自動リフレッシュして再試行（無限再帰を防止）
      - ページネーション対応（pagination_key を用いたループ取得）
      - トークンはモジュールレベルでキャッシュしてページネーション間で共有
      - JSON デコード失敗時に詳細を含むエラーを送出
      - データ整形ユーティリティ (_to_float / _to_int)：空値／変換エラーを安全に None にマップ、"1.0" のような浮動小数文字列を int に変換可能だが小数部が残る場合は None を返す
      - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。すべて ON CONFLICT DO UPDATE による冪等性を保証し、fetched_at を UTC ISO8601 形式で保存
    - schema:
      - DuckDB のスキーマ初期化ユーティリティを実装（init_schema / get_connection）
      - 3 層データモデル（Raw / Processed / Feature）および Execution 層のテーブル DDL を定義
      - 主要テーブル群（例）:
        - Raw: raw_prices, raw_financials, raw_news, raw_executions
        - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
        - Feature: features, ai_scores
        - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
      - 制約（PK, CHECK）や頻出クエリ向けのインデックスを定義
      - init_schema は db_path の親ディレクトリを自動作成（":memory:" をサポート）
    - pipeline:
      - ETL パイプライン（run_daily_etl）を実装
      - フロー: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック（オプション）
      - 差分更新ロジック: DB の最終取得日から未取得分のみ取得し、デフォルトで backfill_days=3 により過去 n 日を再取得して API の後出し修正を吸収
      - カレンダーは lookahead_days=90 日先まで先読みして営業日調整に利用
      - ETLResult データクラスで処理結果（取得件数、保存件数、品質問題、エラー）を返す
      - 各ステップは個別に例外ハンドリングされるため、1 ステップ失敗でも残りを継続して実行
    - audit:
      - 監査ログ（signal_events, order_requests, executions）テーブルを定義する init_audit_schema / init_audit_db を実装
      - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を設計
      - 全ての TIMESTAMP を UTC で保存する（init で SET TimeZone='UTC' を実行）
      - order_request_id は冪等キー、broker_execution_id は約定の冪等キーとして扱う
      - 状態管理や制約（CHECK、FK、created_at / updated_at）を含むテーブル設計および検索用インデックスを提供
    - quality:
      - データ品質チェック機能（quality.run_all_checks を呼ぶ想定）
      - 実装済のチェック:
        - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は除外）
        - スパイク検出 (check_spike): LAG を用いた前日比の急騰・急落検出（デフォルト閾値 0.5 = 50%）
        - （設計上は重複・日付不整合なども想定。現行コードでは上記チェックを中心に実装）
      - QualityIssue データクラスで検出結果（check_name, table, severity, detail, rows）を表現
      - 各チェックは最大 10 件のサンプル行を含めて結果を返し、呼び出し元が重大度に応じて処理を決定できる設計
  - パッケージ初期化 (__init__.py) でバージョンを "0.1.0" として公開

Changed
- 初回リリースのため過去の変更履歴は無し

Fixed
- 初回リリースのため過去の修正履歴は無し

Notes / Implementation details
- デフォルト設定の主な値:
  - J-Quants API レート: 120 req/min（最小間隔 0.5 秒）
  - API 再試行回数: 3 回（指数バックオフ）
  - ETL のバックフィル: 3 日
  - カレンダー先読み: 90 日
  - データベース: デフォルト DuckDB パスは data/kabusys.duckdb、SQLite は data/monitoring.db（環境変数で上書き可能）
- セキュリティ:
  - 環境変数の未設定は明示的エラーにし、安全なデフォルトを回避する設計（トークン等は必須）
  - .env 読み込みでは OS 環境変数を保護する機構（protected set）を用意
- ロギング:
  - 各主要処理にログ出力を追加（info/warning/error レベル）

Breaking Changes
- 初回リリースのため破壊的変更はありません

今後の予定（抜粋）
- quality モジュールのチェック追加（重複チェック、日付不整合チェック等の拡充）
- run_all_checks の実装と監査ログ連携（ETL -> 監査の自動記録）
- execution / strategy 層の具体的な発注ロジック・ブローカー連携の実装
- 単体テスト・統合テストの追加と CI の導入

--- 

（注）この CHANGELOG は提供されたコードベースから推測して作成しています。アプリケーション要件や実運用フローに基づく追加の変更点や修正が存在する場合は、適宜追記してください。