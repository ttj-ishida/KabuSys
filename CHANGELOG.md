# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

現在のバージョン: 0.1.0

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システムの基盤モジュール群を追加しました。

### Added
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py
  - パッケージ公開対象: data, strategy, execution, monitoring
  - バージョン: 0.1.0

- 環境設定管理モジュールを追加
  - src/kabusys/config.py
  - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルートの .git または pyproject.toml を基準に探索）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト向け）
  - 複雑な .env 行パース対応（コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ）
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供
    - 必須項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 設定値の検証:
    - KABUSYS_ENV は development / paper_trading / live のいずれか
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか

- J-Quants API クライアントを追加
  - src/kabusys/data/jquants_client.py
  - 機能:
    - ID トークン取得 (get_id_token)
    - 日足株価 (fetch_daily_quotes)、財務データ (fetch_financial_statements)、JPX マーケットカレンダー (fetch_market_calendar) の取得（ページネーション対応）
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
  - 信頼性・レート制御:
    - 固定間隔スロットリングによるレート制限（既定: 120 req/min、最小間隔 = 60 / 120 秒）
    - リトライロジック（最大 3 回、指数バックオフ、対象: ネットワークエラー・408/429/5xx）
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰を防止）
    - JSON デコード失敗時の明確な例外
  - Look-ahead bias に配慮し、取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ定義・初期化モジュールを追加
  - src/kabusys/data/schema.py
  - 3 層構造に基づくテーブル定義 (Raw / Processed / Feature / Execution)
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル定義は各種 CHECK 制約や PRIMARY KEY を含む
  - 頻出クエリ向けのインデックスを定義
  - init_schema(db_path) によりファイル・メモリ DB の初期化とテーブル作成を行う（冪等）
  - get_connection(db_path) により既存 DB への接続を返す（スキーマ初期化は行わない）
  - DB ファイルの親ディレクトリを自動作成

- DuckDB への保存ユーティリティ（J-Quants 連携）
  - jquants_client 内に、取得結果を DuckDB に保存する関数を追加
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 挿入は ON CONFLICT DO UPDATE を用いて冪等性を担保
  - PK 欠損レコードはスキップして警告ログを出力
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換と不整合値の扱いを定義）

- 監査ログ（トレーサビリティ）モジュールを追加
  - src/kabusys/data/audit.py
  - システムのシグナルから約定までを UUID 連鎖で完全にトレースする監査テーブルを定義
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして扱う設計
  - すべての TIMESTAMP を UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）
  - init_audit_schema(conn) により既存接続に監査テーブルを追加（冪等）
  - init_audit_db(db_path) により監査専用 DB を初期化して接続を返す
  - インデックスを追加し、検索性能と callback 紐付けを考慮

- 空のパッケージ初期化ファイルを追加（プレースホルダ）
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py

### Notes / 使用上の注意
- 初回セットアップ
  - 必須環境変数を設定してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - データベース初期化:
    - DuckDB メイン DB: from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)
    - 監査 DB（別ファイルにしたい場合）: from kabusys.data.audit import init_audit_db; conn = init_audit_db("path/to/audit.duckdb")
  - デフォルトの DuckDB パス: data/kabusys.duckdb（settings.duckdb_path）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動で .env を読み込まなくなります（テスト時の環境制御に便利）。

- 設定検証
  - KABUSYS_ENV の不正値や LOG_LEVEL の不正値は Settings プロパティアクセス時に ValueError を送出します。起動前に環境変数を確認してください。

- J-Quants API の利用
  - API レート制限（120 req/min）をライブラリ層で制御しますが、大量並列で呼ぶ場合は呼び出し側でも注意してください（モジュールローカルの RateLimiter を用いているため、プロセス内並列呼び出しの競合により制限を超える可能性があります）。
  - get_id_token は refresh_token を環境変数から取得します。未設定の場合は ValueError。

- データ整合性
  - DuckDB スキーマには多くの CHECK 制約と外部キーを設定しています。投入データはスキーマに合うように前処理してください。
  - save_* 系関数は PK を欠く行をスキップします（ログに警告を出力）。

### Breaking Changes
- 初回リリースのため、該当なし。

### Security
- 初回リリースで既知の重大なセキュリティ問題はありません。ただし、API トークン等の扱いには注意してください（.env ファイルは機密情報を含み得るためバージョン管理に含めないでください）。

### Contributors
- 初期実装チーム（コードベースより）  

(以上)