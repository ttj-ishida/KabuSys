# CHANGELOG

すべての変更点は「Keep a Changelog」準拠で記載しています。  
このリポジトリの初期リリースに相当する変更内容を、ソースコードから推測してまとめています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Deprecated / Removed / Security）に分けて記載しています。
- 日付はパッケージの __version__ に合わせた初版（0.1.0）のリリース日として記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__version__ = 0.1.0）を追加。
  - パッケージの公開モジュール群（data, strategy, execution, monitoring）を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - .env, .env.local の読み込み順および OS 環境変数の保護（protected keys）を実装。
    - 環境変数自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - プロジェクトルートの検出は __file__ を起点に .git / pyproject.toml を探索するため、CWD に依存せず配布後も動作。
  - .env 行パーサ（_parse_env_line）を実装し、以下に対応：
    - コメント行・空行の無視、`export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートなしは直前が空白/タブの場合にコメント判定）
  - Settings クラスを実装し、必須値取得（_require）や型変換、デフォルト値、検証を提供：
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティを提供（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path 等）
    - KABUSYS_ENV の有効値チェック (development, paper_trading, live) とログレベル検証（DEBUG 等）
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装：
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライ機構（指数バックオフ、最大3回）、対象ステータス（408, 429, 5xx）を考慮。
    - 429 の場合は Retry-After ヘッダを優先。
    - JSON デコード失敗時の明示的エラー。
    - 401 受信時のトークン自動リフレッシュを 1 回まで行うガード（allow_refresh による無限再帰防止）。
    - ページネーション対応（pagination_key）のハンドリング。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - 認証補助関数 get_id_token を実装（refresh_token から idToken を取得）。
  - データ取得関数を実装：
    - fetch_daily_quotes（株価日足 OHLCV、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - いずれも fetched_at トレース方針（Look-ahead Bias 対策）やログ出力を考慮。
  - DuckDB への保存関数（冪等に実行可能）を実装：
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE による冪等性と PK 欠損行のスキップロジックを備える。
  - 値変換ユーティリティ（_to_float, _to_int）を追加し、空値・不正値を安全に処理。

- DuckDB スキーマ定義 & 初期化（kabusys.data.schema）
  - 3層（Raw / Processed / Feature / Execution）を想定したスキーマ DDL を追加。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス（頻出クエリを想定）を作成する SQL を追加。
  - init_schema(db_path) でディレクトリ自動作成→接続→DDL/インデックス実行の初期化処理を提供（冪等）。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない旨明記）。

- ETL パイプライン（kabusys.data.pipeline）
  - 全体 ETL の設計方針を盛り込み、差分更新・バックフィル・品 質チェックのフローを実装。
  - 定数: 最小データ日 (2017-01-01), カレンダー先読み 90 日, デフォルトバックフィル 3 日等。
  - ETLResult dataclass を実装し、取得件数・保存件数・品質問題・エラーを集約。has_errors / has_quality_errors / to_dict を提供。
  - 差分更新ヘルパー: テーブル存在チェック、最大日付取得ユーティリティ。
  - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day を実装（最大 30 日遡る）。
  - 個別ジョブを実装:
    - run_calendar_etl（lookahead に基づく先読み取得）
    - run_prices_etl（差分 + backfill）
    - run_financials_etl（差分 + backfill）
  - run_daily_etl: 上記を順に実行し、品質チェック（quality.run_all_checks）をオプションで実行。各ステップは独立して例外を捕捉し、他ステップへ影響しない設計。

- 監査ログ（kabusys.data.audit）
  - 戦略→シグナル→発注要求→約定 へと連鎖可能な監査用テーブルを追加。
    - signal_events, order_requests（冪等キー order_request_id）, executions
  - 監査用インデックス群を追加（ステータス検索 / JOIN 最適化 等）。
  - init_audit_schema(conn) で UTC タイムゾーン設定およびテーブル/インデックス初期化を実行。
  - init_audit_db(db_path) で専用 DB の初期化を提供。
  - 設計原則としてすべての TIMESTAMP を UTC で保存、監査ログは削除しない（ON DELETE RESTRICT を基本）等を明記。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（severity: error）
    - check_spike: LAG を用いた前日比スパイク（閾値デフォルト 50%）検出
    - （設計上）重複チェック・日付不整合チェックも想定（モジュール設計で扱う旨をドキュメント化）
  - 各チェックはサンプル行（最大10件）を返し、Fail-Fast ではなく全件収集する方針を採用。
  - SQL はパラメータバインドを使用し、効率的に実行。

### Changed
- （初版のため該当なし）

### Fixed
- J-Quants API 呼び出しでのリフレッシュ無限ループ問題に対処：
  - _request は allow_refresh フラグと内部 _token_refreshed フラグを使い、401 リフレッシュを 1 回に制限して無限再帰を防止。
- .env ファイル読み込みでの OS 環境変数上書きを制御するため、読み込み時に protected keys を考慮する実装を採用。

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 認証トークンの取り扱い:
  - ID トークンはモジュール内キャッシュを利用し、必要時のみ get_id_token により取得・更新する設計。
  - HTTP Authorization ヘッダを Bearer トークンで送付。
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能（テスト等での安全対策）。

---

注記（開発者向け）
- DB 初期化: 初回は data.schema.init_schema() を利用し、その後は get_connection() を使って既存 DB に接続すること。
- ETL 実行: run_daily_etl は市場カレンダー取得→営業日調整→株価・財務取得→品質チェックの順で実行し、各ステップの失敗は結果オブジェクト（ETLResult.errors）に記録されるため、運用側で適切にハンドリングしてください。
- jquants_client._request は外部ネットワークや API 仕様変更で例外を投げる可能性があります。運用時はログと ETLResult の errors を監視してください。

以上が、このコードベースから推測した CHANGELOG（初期リリース: 0.1.0）です。必要であれば、各変更点をチケットやリリースノート用にさらに分解して整理できます。