Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての注目すべき変更はここに記載します。SemVer に従います。

Unreleased
----------
- （現在なし）

[0.1.0] - 2026-03-16
-------------------
初回リリース — 日本株自動売買システム "KabuSys" の基本コンポーネントを実装しました。

Added
- パッケージ情報
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
  - __all__ に主要サブパッケージを公開: data, strategy, execution, monitoring

- 環境設定モジュール (kabusys.config)
  - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルートの自動検出: 親ディレクトリに .git または pyproject.toml を探索
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサ実装（_parse_env_line）
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理
  - 環境変数保護/上書き制御をサポートする .env ローダー（_load_env_file）
  - 必須変数取得ヘルパー (_require) と Settings クラスを提供
    - J-Quants、kabuステーション、Slack、DBパス等の設定プロパティを用意
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証
    - Path 型での DB パス取り扱い（expanduser 対応）
    - is_live / is_paper / is_dev 補助プロパティ

- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装
    - 基本URL、レートリミット設定（120 req/min）
    - 固定間隔スロットリングによる RateLimiter 実装
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 を検出した場合の自動 ID トークンリフレッシュ（1回のみ）
    - ページネーション対応（pagination_key 共有）
    - Look-ahead Bias 対策として fetched_at を UTC タイムスタンプで記録
    - モジュールレベルの ID トークンキャッシュ（ページ間で共有）
  - データ取得関数
    - fetch_daily_quotes（株価日足 / OHLCV、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）
    - save_daily_quotes（raw_prices への upsert: ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials へ upsert）
    - save_market_calendar（market_calendar へ upsert、holidayDivision を解釈）
  - 型変換ユーティリティ
    - _to_float / _to_int（空値や不正値に対して安全に None を返す。float 文字列からの int 変換時の注意あり）

- データベーススキーマ (kabusys.data.schema)
  - DuckDB 用のスキーマ定義を実装（Data Platform の 3 層設計）
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）と適切なデータ型を指定
  - パフォーマンス向けのインデックスを定義（銘柄×日付スキャン、ステータス検索等）
  - init_schema(db_path) による冪等な初期化、get_connection() ヘルパーを提供
  - db_path の親ディレクトリ自動作成、":memory:" サポート

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の実装（run_daily_etl を中心に）
    - 処理フロー: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック
    - 差分更新ロジック: DB の最終取得日をもとに不足分のみ取得、既定のバックフィル日数(3日)で後出し修正を吸収
    - カレンダーの先読み（既定 90 日）をサポートして営業日調整に使用
    - 各ステップは独立してエラーハンドリング（1ステップ失敗でも他ステップは継続）
    - id_token の注入可能性（テスト容易性）
  - 個別ジョブの実装
    - run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ差分取得と保存を実行）
  - ETL 実行結果を表す ETLResult データクラスを追加
    - 取得数 / 保存数 / 品質問題 / エラー概要 を保持
    - has_errors, has_quality_errors, to_dict を提供
  - DB の最終取得日取得ユーティリティ（get_last_price_date 等）
  - 営業日調整ヘルパー (_adjust_to_trading_day)

- データ品質チェック (kabusys.data.quality)
  - 品質チェックフレームワークを実装
    - QualityIssue データクラス（check_name, table, severity, detail, rows）
    - チェック実装（SQL ベース）
      - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は除外）
      - スパイク検出 (check_spike): LAG を用いた前日比スパイク検出（デフォルト閾値 50%）
      - （設計上）重複チェック、日付不整合検出も対象（関数化が想定されている）
    - 各チェックは問題を全件収集してリストで返す（Fail-Fast ではない）
    - SQL はパラメータバインドを使用してインジェクションリスクを低減

- 監査ログ・トレーサビリティ (kabusys.data.audit)
  - シグナルから約定に至るトレーサビリティ用テーブルを実装
    - signal_events（戦略が生成したシグナル。棄却されたものも含む）
    - order_requests（冪等な order_request_id を持つ発注要求ログ、価格チェックの整合性チェック付き）
    - executions（証券会社から返った約定情報。broker_execution_id をユニークキーとして冪等性を担保）
  - ステータス遷移や制約を定義（ON DELETE RESTRICT を採用、監査ログは削除しない方針）
  - タイムゾーンを UTC に固定して初期化（conn.execute("SET TimeZone='UTC'")）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（冪等）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の読み込みで OS 側の既存環境変数を保護する仕組みを実装（.env 上書き制御）
- HTTP リクエスト部で Authorization ヘッダを適切に扱う（トークン管理とリフレッシュ）
- SQL 実行はパラメータバインド（?）を利用する方針（quality モジュール等で採用）

Notes / Implementation details
- DuckDB をメインのデータ層に使用。init_schema は既存テーブルをそのままにして冪等に実行可能。
- J-Quants API のレート制限 (120 req/min) を守るため単純な固定間隔スロットリングを採用（_RateLimiter）。
- リトライでは 429 の Retry-After ヘッダを優先し、なければ指数バックオフを使用。
- 日付・数値変換は堅牢化されており、不正な値は None として扱うことで後続処理でのクラッシュを防止。
- ETL は「品質チェックでエラーが見つかっても全体を止めない」設計（呼び出し元で対処判断）。

今後の予定（想定）
- strategy / execution / monitoring サブパッケージの実装拡充（現在はパッケージ位置のみ）
- 追加の品質チェック（重複・未来日付検出）の具体実装
- 単体テスト・統合テストの追加（env 自動ロードの無効化フラグ等）
- 外部ブローカー（kabuステーション）との実際の送受信ロジック実装および retry/再送制御

References
- この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の仕様や計画はリポジトリのドキュメント（DataPlatform.md / DataSchema.md 等）を参照してください。