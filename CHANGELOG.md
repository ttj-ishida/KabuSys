# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムの基盤となる以下の主要コンポーネントを実装。

### 追加 (Added)
- パッケージ公開情報
  - 初期パッケージメタ情報を src/kabusys/__init__.py に実装（__version__ = "0.1.0"）。モジュール群を外部に公開（data, strategy, execution, monitoring）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり）。
  - .env のパース機能を実装（export プレフィックス対応、クォート・エスケープ処理、インラインコメント処理）。
  - Settings クラスでアプリ設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル、is_live/is_paper/is_dev 判定など）。
  - 環境変数の必須チェックと妥当性検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装。
  - レートリミッタ実装（120 req/min、固定間隔スロットリング）。
  - リトライロジックを実装（指数バックオフ、最大3回、対象: 408/429/5xx、429 の Retry-After 優先）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ（ページネーション間共有）。
  - ページネーション対応（pagination_key を用いた全ページ取得）。
  - DuckDB に対する冪等保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも ON CONFLICT DO UPDATE を使用。
  - データ変換ユーティリティ (_to_float, _to_int) を実装（空値・不正値に対する堅牢な変換と挙動の明確化）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録（Look-ahead Bias 対策）。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の多層データモデルに基づく DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層を定義。
  - features, ai_scores など Feature 層を定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層を定義。
  - 想定されるクエリパターンに合わせたインデックス群を作成。
  - init_schema(db_path) によりディレクトリ作成を含めた DB 初期化とテーブル作成を行う API を提供。get_connection() で既存 DB への接続を取得可能。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の実装（run_daily_etl）。処理順序はカレンダー → 株価 → 財務 → 品質チェック。
  - 差分更新ロジック：DB の最終取得日を元に自動で date_from を算出し、backfill_days による再取得をサポート。
  - カレンダー先読み（デフォルト 90 日）と営業日調整ロジック（非営業日は直近営業日に調整）。
  - 個別ジョブ API: run_prices_etl, run_financials_etl, run_calendar_etl（各々取得・保存を行い、取得数/保存数を返す）。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラー情報を集約して返却。
  - 品質チェックの実行フラグやスパイク閾値等のパラメータ化。
- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - signal_events / order_requests / executions の監査テーブルを実装し、UUID 連鎖によるトレーサビリティを確保。
  - order_request_id による冪等キー設計、各テーブルのステータス管理、タイムスタンプは UTC を前提に設定。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。
  - 監査用のインデックス群を用意（status や日付/銘柄検索等を高速化）。
- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを導入して品質問題を表現。
  - 欠損データ検出（OHLC 欄の NULL 検出: check_missing_data）。
  - スパイク検出（前日比の変動率が閾値超の場合を検出: check_spike）。SQL（LAG ウィンドウ）ベースで実行。
  - 重複・将来日付・営業日外検出等の設計を文書化（実装のうち主要チェックを提供）。
- パッケージ構成
  - data モジュールの下に jquants_client, schema, pipeline, audit, quality を配置。
  - strategy および execution パッケージをプレースホルダとして作成（将来の戦略・発注ロジックを想定）。

### 変更 (Changed)
- 初版リリースにつき、特に既存コードからの変更はなし（初回導入）。

### 修正 (Fixed)
- 初版リリースにつき、特にバグ修正項目はなし。

### セキュリティ (Security)
- 環境変数の保護機構：
  - .env 読み込み時に既存 OS 環境変数を protected として上書きしない振る舞い（.env.local は override=True で上書き可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途を想定）。

### 注意事項 / 既知の設計方針
- J-Quants API 呼び出しはレート制限・リトライ・トークンリフレッシュの設計を含むが、実運用では追加の監視やメトリクス収集が推奨される。
- DuckDB スキーマは冪等性（IF NOT EXISTS / ON CONFLICT / INDEX IF NOT EXISTS）を前提にしているため、既存データベースへの導入は安全に行える。
- quality モジュールのチェックは Fail-Fast ではなく問題をすべて収集して返却する設計。呼び出し元で重大度に応じた運用判断を行う必要がある。
- 時刻は原則 UTC で扱う（監査ログ・fetched_at 等）。

---

今後の予定（例）
- strategy 層の具体的な戦略実装とバックテスト機能の追加
- execution 層のブローカー連携（kabu ステーション等）と注文処理の実装
- 品質チェック項目の拡充（重複・将来日付チェック等の追加実装）
- ロギング・メトリクス・監視連携の強化

-- End of CHANGELOG --