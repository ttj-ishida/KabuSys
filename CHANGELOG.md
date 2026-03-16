# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です（実際のコミット履歴ではありません）。

※ 現在のパッケージバージョンは src/kabusys/__init__.py の __version__ に基づき 0.1.0 です。

Unreleased
----------
- 今後の変更・修正をここに記載します。

[0.1.0] - 2026-03-16
-------------------
Added
- パッケージ初期リリースとして基本的なモジュール群を追加。
  - kabusys パッケージ基本情報（src/kabusys/__init__.py）。
  - モジュール公開 (data, strategy, execution, monitoring) を __all__ で宣言。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境変数上書き挙動（override, protected）を考慮。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能：
    - J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）/システム環境（env, log_level）等。
  - env や log_level の値検証（許可値チェック）とヘルパー is_live / is_paper / is_dev。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 取得対象: 株価日足(OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装（RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス (408, 429, 5xx)。
  - 401 Unauthorized 発生時の自動トークンリフレッシュ（1 回のみ）と再試行。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - id_token のモジュールレベルキャッシュと共有（ページネーション間のトークン再利用）。
  - fetch_* 系 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar) を提供。
  - 保存用ユーティリティ: DuckDB に対する idempotent な保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
    - fetched_at を UTC で記録し Look-ahead Bias のトレーサビリティを確保。
    - PK 欠損行をスキップして警告ログ出力。
  - JSON デコードエラーやタイムアウト等のエラーに対する明確な例外メッセージとログ。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - 3 層データモデル（Raw / Processed / Feature）と Execution 層のテーブル DDL を定義。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリを想定したインデックス群を定義。
  - 依存関係を考慮したテーブル作成順を用意。
  - init_schema(db_path) により DB ファイル親ディレクトリの自動作成とテーブル初期化を行い、接続を返す。
  - get_connection(db_path) により既存 DB へ接続（スキーマ初期化は行わない）。

- 監査（Audit）モジュールを追加（src/kabusys/data/audit.py）。
  - トレーサビリティ用テーブルを定義:
    - signal_events（戦略が生成したシグナルを全件記録）
    - order_requests（発注要求、order_request_id を冪等キーとして利用）
    - executions（証券会社からの約定情報）
  - データ設計上の原則（UTC タイムスタンプ、削除禁止（ON DELETE RESTRICT）、created_at/updated_at 等）をドキュメント化。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供し、監査テーブルとインデックスを初期化。
  - 発注に関するチェック制約（limit/stop/market の price 条件など）を定義。

- データ品質チェックモジュールを追加（src/kabusys/data/quality.py）。
  - 主なチェック項目:
    - 欠損データ検出（OHLC の NULL を raw_prices から検出）
    - 異常値（スパイク）検出（前日比の絶対変化率で閾値判定、デフォルト 50%）
    - 重複チェック（主キー重複の検出）
    - 日付不整合検出（未来日付・market_calendar による非営業日データ）
  - QualityIssue データクラスを定義し、各チェックは QualityIssue のリストを返す（Fail-Fast ではない）。
  - DuckDB 上で SQL を実行して効率的にチェックを行い、サンプル行（最大 10 件）を返却。
  - run_all_checks により一括で全チェックを実行できる。

- パッケージ構造のスケルトン追加
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（サブパッケージのプレースホルダ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（protected set）を導入し、.env による上書きから重要な OS 環境を守る。

Migration / Upgrade Notes
- 初回導入時:
  - データ格納用 DuckDB を作成するには schema.init_schema(settings.duckdb_path) を呼び出してください（db_path の親ディレクトリは自動作成されます）。
  - 監査ログのみ別 DB に分ける場合は data.audit.init_audit_db() を使用できます。
- 環境変数:
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings の各プロパティ取得時に存在チェックされ、未設定時は ValueError を送出します。
  - テスト中に .env の自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

既知の制限 / 今後の改善予定（コードから推測）
- strategy / execution / monitoring サブパッケージはプレースホルダのまま（実ロジックは未実装）。
- エラーハンドリングやリトライの挙動は概ね実装済みだが、メトリクス計測や詳細な監視連携（例: Slack 通知）は今後の追加が想定される。
- 単体テスト・統合テスト用のテストヘルパーは現状明示されておらず、将来的に追加予定。
- J-Quants API のレート制御は固定間隔スロットリングを採用しているが、より柔軟なバースト制御やトークンバケットの導入検討の余地あり。

---

最初のリリース（0.1.0）は主にデータ取り込み・保存・品質管理・監査の基盤を提供します。戦略や発注フローの実装は今後のバージョンで順次追加される想定です。