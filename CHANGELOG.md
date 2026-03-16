# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコア機能を実装しました。主要な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - src/kabusys/__init__.py に公開モジュール一覧（data, strategy, execution, monitoring）を導入。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート判定ロジック（.git または pyproject.toml を探索）を導入し、カレントワーキングディレクトリに依存しない自動ロードを実現。
  - .env ファイルパーサを実装。以下に対応:
    - 空行・コメント行、先頭に `export ` を付けた形式。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの値に対するインラインコメント処理（直前が空白/タブの場合）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - OS 環境変数を保護するための protected キーセットを導入し、.env.local の上書き制御が可能。
  - Settings クラスを追加し、以下の設定項目をプロパティで提供・検証:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ブールヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアントを実装。取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - レート制御: 固定間隔スロットリングを用いて 120 req/min（min interval を自動算出）。
  - リトライロジック: 指数バックオフ（base=2.0）、最大リトライ回数 3 回、ネットワーク/429/408/5xx を考慮。
  - 401 に対する自動トークンリフレッシュを実装（1 回の再試行まで）。トークン取得時の再帰を防止するオプションを提供。
  - 429 の場合は Retry-After ヘッダを優先して待機。
  - ページネーション対応（pagination_key を採用）およびページ間での ID トークンキャッシュ共有。
  - JSON デコードエラー・HTTP/ネットワークエラーの適切な例外処理とログ出力。
  - データ取得関数を実装:
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB への保存関数（冪等性: ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes(...)
      - fetched_at を UTC タイムスタンプ（Z）で保存
      - PK 欠損行はスキップし警告ログを出力
    - save_financial_statements(...)
    - save_market_calendar(...)
      - HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を判定
  - データ変換ユーティリティを実装:
    - _to_float / _to_int（空値や不正値を安全に None にする）

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform の 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - 運用で頻出するクエリに対応する索引（indexes）を多数作成。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・接続を返す（冪等）。
  - get_connection(db_path) を提供（既存 DB 接続取得用）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のワークフローを実装:
    - 市場カレンダー ETL（先読み）
    - 株価日足 ETL（差分 + バックフィル）
    - 財務データ ETL（差分 + バックフィル）
    - 品質チェック（オプション）
  - 差分更新ロジック:
    - DB 側の最終取得日に基づき自動で date_from を決定
    - デフォルトバックフィル日数 = 3 日
    - カレンダー先読みデフォルト = 90 日
    - 初回ロード時の最小日付は 2017-01-01
  - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー一覧を保持）。
  - 個別ジョブ関数:
    - run_prices_etl(...)
    - run_financials_etl(...)
    - run_calendar_etl(...)
    - run_daily_etl(...)（上記を統合、失敗しても他ステップは継続する設計）
  - ETL は品質チェックで fatal 相当の問題が見つかっても即時停止せず、呼び出し元が判断できる形で結果を返す（Fail-Fast ではない）。
  - 市場カレンダー取得後に営業日調整するユーティリティを実装（_adjust_to_trading_day）。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までを UUID の連鎖で完全にトレースする監査テーブルを実装。
  - テーブル:
    - signal_events（戦略が生成した全シグナルを記録、棄却されたものも含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社から返る約定ログ、broker_execution_id をユニークキーとして冪等）
  - order_requests のチェック制約（limit/stop/market の価格必須条件）を導入。
  - ステータス遷移を想定した status カラムと制約を追加。
  - init_audit_schema(conn) は UTC タイムゾーンを全体に適用してテーブル/索引を作成。
  - init_audit_db(db_path) で監査専用 DB を初期化するユーティリティを提供。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data(conn, target_date=None)
      - raw_prices の OHLC 欠損検出（volume は許容）
      - サンプル行（最大 10 件）を返却し、問題件数をログに出力
      - 検出時は severity="error"
    - check_spike(conn, target_date=None, threshold=0.5)
      - LAG ウィンドウ関数を用いて前日比のスパイク（デフォルト 50%）を検出
      - サンプル行を返却
  - 設計方針: 各チェックは全件収集して QualityIssue リストを返す（Fail-Fast ではない）。
  - SQL はパラメータバインドを利用しインジェクションリスクを低減。

- 共通・補助
  - duckdb を主要な永続化層として採用し、IDEMPOTENT な保存を前提とした設計。
  - ロギング（各モジュールで logger を使用）・型注釈・詳細な docstring を整備し、テスト容易性を向上。

### Changed
- （該当なし：初回リリース）

### Fixed
- （該当なし：初回リリース）

### Notes / Design decisions
- ETL 処理は「継続的稼働」を念頭に設計しており、単一ステップの失敗でパイプライン全体を止めない方針です。呼び出し元は ETLResult を基に運用判断（再実行・アラートなど）を行います。
- DuckDB の制約/インデックスは運用上の主要クエリパターン（銘柄×日付のスキャン、ステータス検索等）を想定して設計しています。
- J-Quants API のリトライ/レート制御は、API レート制限（120 req/min）とネットワークの不安定性を考慮した保守性重視の実装です。

---

今後の予定（例）
- strategy / execution / monitoring レイヤーの具体実装（戦略ロジック、リアルタイム監視、証券会社接続等）
- 品質チェックの追加（重複チェック、将来日付チェックなどの完全実装）
- 単体テスト・統合テストの充実、および CI/CD パイプラインの整備

（以上）