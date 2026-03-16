# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
セマンティック バージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-16

初回リリース — 日本株自動売買プラットフォームの基盤となるコア機能を実装しました。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージの初期化（src/kabusys/__init__.py）とバージョン設定（0.1.0）。
- 設定管理
  - 環境変数・設定管理モジュール（src/kabusys/config.py）を追加。
    - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
    - 環境変数パースの強化（export 構文、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い）。
    - 必須変数チェック（_require）と Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル検証など）。
    - 有効な環境値・ログレベルの検証ロジックを組み込み（development / paper_trading / live、DEBUG 等）。
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API から株価日足、財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - レートリミッタ（固定間隔スロットリング）を実装して API レート（120 req/min）を遵守。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。429 の場合は Retry-After を優先。
  - 401 受信時にトークン自動リフレッシュ＆1回再試行（無限ループ回避）。
  - ページネーション対応および id_token のモジュールレベルキャッシュ共有（ページ間でトークンを再利用）。
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保。
  - データ変換ユーティリティ（_to_float, _to_int）、取得時刻（fetched_at）を UTC タイムスタンプで記録（Look-ahead Bias 防止のため）。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - 3層（Raw / Processed / Feature / Execution）を想定したテーブル定義を実装。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主要なインデックス定義を含む（コード×日付、ステータス検索など）。
  - init_schema(db_path) による初期化処理と get_connection を提供。ディレクトリ自動作成対応。":memory:" サポート。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新・バックフィル・品質チェックを含む日次 ETL 実装（run_daily_etl）。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（差分取得ロジック、backfill の取り扱い）。
  - ETLResult データクラス（処理結果の集約、品質問題やエラー情報の収集）。
  - 市場カレンダー取得の先読み（デフォルト 90 日）と営業日調整機能（_adjust_to_trading_day）。
  - 最小データ開始日（2017-01-01）などの定数設定。
  - 各ステップは独立して例外ハンドリングし、1 ステップの失敗で全体を中断しない設計（Fail-Fast ではない）。
- 監査ログ（Audit）モジュール（src/kabusys/data/audit.py）
  - シグナル→発注→約定の全トレーサビリティを担保する監査テーブル群を実装。
    - signal_events, order_requests, executions の DDL を提供。
  - order_request_id を冪等キーとして採用。タイムスタンプは UTC（init_audit_schema で SET TimeZone='UTC'）。
  - 監査用インデックス群を定義。init_audit_db による専用 DB 初期化を提供。
- 品質チェックモジュール（src/kabusys/data/quality.py）
  - 欠損データ検出（OHLC 欄の NULL 検出, error として扱う）、スパイク検出（前日比の変動、デフォルト 50%）、
    重複チェック、日付不整合検出の方針。SQL ベースで効率的に実行。
  - QualityIssue データクラスを提供し、複数問題を収集して返却する設計。
- パッケージ構成ファイル（各 __init__.py）を追加し、モジュールがパッケージとして利用可能。
- ドキュメント的要素をソース内 docstring とコメントで充実（設計原則、DataPlatform / DataSchema に基づく旨を明記）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- HTTP 通信のタイムアウトやリトライ制御、トークンの自動リフレッシュ等を設計に組み込み、API 呼び出しの堅牢性を高めました。

### 注意事項 / マイグレーションノート
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の _require() によって未設定時は ValueError を送出）。
  - DB のデフォルトパス: DUCKDB_PATH = data/kabusys.duckdb、SQLITE_PATH = data/monitoring.db（環境変数で上書き可）。
  - 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ初期化は init_schema() を利用してください。スキーマ定義は冪等に作られるため、既存 DB に対して何度でも実行可能です。
- 監査テーブルは init_audit_schema / init_audit_db で追加初期化します。監査用タイムスタンプは UTC で保存されます。
- run_daily_etl は複数のステップで例外を分離して扱うため、一部のステップで失敗があっても他が実行されます。結果は ETLResult に集約されます。
- J-Quants API のレート上限および再試行ポリシーは実装済みですが、実運用時はさらに上位のスロットリングや監視を組み合わせてください。

---

今後のリリースでは、実行（kabu API）連携、戦略実行モジュール、モニタリング・Slack 通知の具現化、より細かな品質チェックやバックテスト用機能の追加を予定しています。