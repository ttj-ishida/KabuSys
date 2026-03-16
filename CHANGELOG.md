# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」の慣習に従っています。

リリースはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読込する仕組みを実装。
  - 読み込み順序: OS環境変数 > .env.local > .env。テスト等で自動読込を無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応。
  - export KEY=val 形式、クォート付き値、行内コメント等に耐性のある .env パーサ実装。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / データベースパス 等の設定をプロパティで提供。
  - 設定値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
  - デフォルトのデータベースパス（DuckDB, SQLite）をサポート（ユーザホーム展開含む）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装:
    - レート制限（_RateLimiter）: 120 req/min を固定間隔スロットリングで保護。
    - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx を再試行対象に設定。
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とページネーション間でのトークンキャッシュ共有。
    - JSON デコード失敗時の明確なエラー報告。
  - get_id_token(): リフレッシュトークンから ID トークンを取得する POST 実装。
  - データ取得関数:
    - fetch_daily_quotes(): 株価日足（OHLCV、ページネーション対応）
    - fetch_financial_statements(): 財務（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar(): JPX マーケットカレンダー（祝日・半日・SQ）
  - DuckDB への冪等保存関数:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - ON CONFLICT DO UPDATE を使った冪等性を実現
    - fetched_at を UTC で記録（ISO8601 形式、末尾に Z）
  - 値変換ユーティリティ:
    - _to_float(), _to_int()：空値や不正値への耐性と仕様（"1.0" → int 変換、非整数小数→ None など）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataPlatform に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - 主要テーブルをDDLで網羅的に定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - よく使うクエリ向けにインデックスも定義（銘柄×日付スキャン、ステータス検索等）。
  - init_schema(db_path) を実装し、DBファイルの親ディレクトリ作成→DDL実行→接続返却（冪等）。
  - get_connection(db_path) により既存DBへの接続を取得可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の統合エントリ run_daily_etl() を実装:
    - 市場カレンダー取得（先読み lookahead）
    - 株価日足 ETL（差分更新 + backfill）
    - 財務データ ETL（差分更新 + backfill）
    - 品質チェック（オプション）
  - 差分更新ロジック:
    - DB の最終取得日から backfill_days 分遡って再取得する既定動作（デフォルト backfill_days=3）。
    - 市場カレンダーは target_date + lookahead_days まで先読み（デフォルト 90 日）。
    - 非営業日は直近の営業日に調整するヘルパーを実装（_adjust_to_trading_day）。
  - 個別ジョブ実装:
    - run_prices_etl(), run_financials_etl(), run_calendar_etl()（それぞれ取得→save→ログ）
  - ETLResult データクラスで結果/品質問題/エラーを集約し、監査・ログに利用可能。
  - 各ステップは独立エラーハンドリング（1 ステップ失敗でも他は継続）する設計。

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブルを実装:
    - signal_events（戦略シグナルログ）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キー）
  - すべての TIMESTAMP を UTC で扱うため init_audit_schema() は SET TimeZone='UTC' を実行。
  - init_audit_db(db_path) を提供し、監査用 DB を初期化して接続を返却。
  - 監査向けインデックスも定義（signal_events の日付/戦略検索、order_requests のステータス検索など）。
  - ステータス列・チェック制約でデータ整合性・状態遷移を明示。

- データ品質チェック基盤（kabusys.data.quality）
  - QualityIssue データクラスを定義し、チェック名・テーブル・重大度・詳細・サンプル行を扱う。
  - 実装済みチェック（例）:
    - check_missing_data(): raw_prices の OHLC 欠損を検出（欠損はエラー扱い、サンプルを返却）。
    - check_spike(): 前日比スパイク（閾値デフォルト 50%）を検出するクエリを実装（サンプル + 件数集計）。
  - SQL を使用した効率的なチェック設計、パラメータバインドを利用して注入リスクを排除。
  - 品質チェックは全件収集型（Fail-Fast ではなく、呼び出し側が重大度に応じて処理判断）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

備考:
- コード内のドキュメント（DataPlatform.md / DataSchema.md 等）に基づく設計意図や注意点が多数コメントされています。  
- 一部のモジュール（strategy, execution, monitoring）はパッケージ構成上のプレースホルダとして存在しますが、機能は順次追加される想定です。