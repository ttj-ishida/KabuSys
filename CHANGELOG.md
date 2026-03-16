# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトの初期バージョンとしてのリリースノートを、コードベースから推測して作成しています。

全般:
- セマンティクス: 主要なモジュールは kabusys パッケージ配下に整理（data, strategy, execution, monitoring を __all__ として公開）
- バージョン: パッケージバージョンは 0.1.0（src/kabusys/__init__.py）

## [Unreleased]

（新規追加や今後予定の変更はここに記載してください）

## [0.1.0] - 2026-03-16

### Added
- 基本パッケージ構成を追加
  - パッケージエントリポイント（src/kabusys/__init__.py）にバージョン & 公開 API を定義。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込み。
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env 自動読み込みを実行（CWD 非依存）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース/タブに基づく扱い）に対応。
  - Settings クラスで主要な設定値をプロパティとして公開（J-Quants, kabu API, Slack, DB パス, 環境 / ログレベルの検証等）。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - データ取得: 株価日足（OHLCV）、財務諸表（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - 認証: リフレッシュトークンから id_token を取得する get_id_token を実装。
  - ページネーション対応（pagination_key を利用）。
  - レート制御: 固定間隔スロットリングで 120 req/min 相当の RateLimiter を実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx に対してリトライ、429 の場合は Retry-After ヘッダを尊重。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）と再試行の実装。
  - DuckDB への保存（save_* 関数）: ON CONFLICT DO UPDATE を用いた冪等な保存処理（raw_prices, raw_financials, market_calendar）。
  - データ整形ヘルパ（_to_float, _to_int）を実装し、不正値を安全に取り扱い。
  - fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias のトレーサビリティを確保。
- データベーススキーマおよび初期化モジュールを追加（src/kabusys/data/schema.py）
  - 3 層構造（Raw / Processed / Feature）＋ Execution 層のテーブル定義を含む包括的な DDL を実装。
  - Raw: raw_prices, raw_financials, raw_news, raw_executions など。
  - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols など。
  - Feature: features, ai_scores など。
  - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など。
  - 適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を定義してスキーマ整合性を担保。
  - 運用を想定したインデックス定義（頻出クエリパターン向け）。
  - init_schema(db_path) による冪等な初期化と get_connection() を提供。親ディレクトリ自動作成対応。
- ETL パイプラインを追加（src/kabusys/data/pipeline.py）
  - 差分更新（データベースの最終取得日に基づく差分取得）を実装。
  - backfill_days による後出し修正吸収のための再取得（デフォルト 3 日）。
  - 市場カレンダーの先読み（デフォルト 90 日）をサポートし、営業日調整に利用。
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別 ETL ジョブ実装。
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の順で安全に実行する統合エントリポイント。各ステップは独立してエラーハンドリング。
  - ETLResult データクラスを導入し、実行結果（取得数、保存数、品質問題、エラー一覧）を構造化して返却。
  - id_token の注入を可能にしてテスト容易性を確保。
- 監査ログ（トレーサビリティ）モジュールを追加（src/kabusys/data/audit.py）
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を設計。
  - signal_events, order_requests（冪等キー order_request_id）, executions テーブルを定義。
  - 全 TIMESTAMP を UTC で保存する（init_audit_schema は TimeZone='UTC' を設定）。
  - ステータス管理、FOREIGN KEY による参照整合性、要約検索向けインデックスを定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
- データ品質チェックモジュールを追加（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, sample rows）。
  - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欄の NULL を検出（volume は除外）。
  - 異常値（スパイク）検出（check_spike）: LAG ウィンドウで前日比を計算し閾値超の変動を検出（デフォルト 50%）。
  - 重複チェック・日付不整合検出（設計に記載されているが、実装済みのチェックは上記参照）。
  - 各チェックは全件収集（Fail-Fast ではなく呼び出し元で重大度に応じて処理を判断可能）。
  - DuckDB を用いた SQL 実行で効率的に実行。パラメータバインドを使用している点を明示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Implementation details
- .env パーシングはシェル互換の全てのケースを網羅するものではないが、実用的な多くのパターン（export, quoted values, escaped characters, inline comments）に対応。
- jquants_client は標準ライブラリの urllib を使用しており、タイムアウトやエラーハンドリングを独自実装している。
- DuckDB の INSERT..ON CONFLICT を利用した冪等保存により、ETL を繰り返し実行しても上書きで最新化される設計。
- 全体的に「冪等性」「トレーサビリティ」「外部 API に対する堅牢性（レート制限・リトライ・トークン更新）」を重視した実装になっている。

### Breaking Changes
- なし（初回リリース）

---

この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリース日付は運用状況に合わせて調整してください。必要であれば、各ファイルごとの更に詳細な変更点（関数シグネチャ・制約の説明など）を追記します。どのフォーマットで出力するか（Markdown、リリースノートの言語、日付）に指定があれば調整します。