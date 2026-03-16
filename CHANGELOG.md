Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に従っています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基本実装を追加。
  - パッケージ構成:
    - kabusys.__init__ にバージョン情報と公開サブパッケージを定義（data, strategy, execution, monitoring）。
  - 設定 / 環境変数管理 (kabusys.config):
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化するオプションを提供。
    - export KEY=val 形式、クォート・エスケープ、行内コメント等に対応するパーサ実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを公開。
    - 必須環境変数未設定時は ValueError を送出する _require 実装。

  - データ取得クライアント (kabusys.data.jquants_client):
    - J-Quants API クライアントを実装。取得対象: 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー。
    - API レート制御: 固定間隔スロットリングで 120 req/min 相当の RateLimiter を実装。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx/ネットワークエラーに対応。
    - 401 Unauthorized 発生時はリフレッシュトークンで id_token を自動更新して1回だけリトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ保存する idempotent な save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を用い重複を排除。
    - 取得時間（fetched_at）は UTC ISO8601 形式で記録（Look-ahead Bias 防止のため取得時刻を保存）。
    - 値変換ユーティリティ (_to_float / _to_int) を実装（安全な変換・不正値を None にする挙動を含む）。
    - モジュールレベルで id_token キャッシュを保持してページネーションで共有。

  - DuckDB スキーマ定義 (kabusys.data.schema):
    - Raw / Processed / Feature / Execution の多層スキーマ DDL を追加。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores の Feature テーブル。
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance の Execution テーブル。
    - 頻出クエリに対するインデックスを多数定義。
    - init_schema(db_path) によりディレクトリ作成・DDL 実行して接続を返す (冪等)。
    - get_connection(db_path) で既存 DB へ接続。

  - ETL パイプライン (kabusys.data.pipeline):
    - 日次 ETL を実装: run_daily_etl をエントリーポイントとして、順に market calendar → prices → financials を差分取得・保存・品質チェック。
    - 差分更新ロジック: DB の最終取得日からの差分取得、backfill_days による再取得（デフォルト 3 日）。
    - calendar は target_date + lookahead_days（デフォルト 90 日）まで先読みして営業日調整に利用。
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別実行可能。
    - ETLResult dataclass を追加し、取得件数・保存件数・品質問題リスト・エラーを集約して返却。
    - 各ステップは個別に例外処理され、1ステップの失敗でも後続ステップは継続（Fail-Fast ではない設計）。

  - 監査ログ（トレーサビリティ） (kabusys.data.audit):
    - 戦略 → シグナル → 発注要求 → 約定 への一貫した監査テーブル群を実装（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして二重発注を防止する設計。
    - 全 TIMESTAMP を UTC 保存するため init_audit_schema は "SET TimeZone='UTC'" を実行。
    - init_audit_db(db_path) による専用 DB 初期化を提供。
    - 監査用インデックスを複数定義し検索性能を考慮。

  - データ品質チェック (kabusys.data.quality):
    - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
    - 欠損データ検出 check_missing_data（raw_prices の OHLC 欠損を検出、重大度 error）。
    - スパイク検出 check_spike（前日比での急騰・急落を検出、しきい値はデフォルト 50%）。
    - 重複・日付不整合等のチェック設計（SQL + パラメータバインドで実装方針）。  

Other
- ドキュメントや設計意図をコード内 docstring に記載（レート制御、リトライ、冪等性、時刻の取り扱い等の設計原則を明示）。
- テスト容易性を意識した設計（id_token の注入、KABUSYS_DISABLE_AUTO_ENV_LOAD による環境設定の制御など）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（特筆すべきセキュリティ修正はなし）

注記 / マイグレーション
- 初回リリースのため破壊的変更はありませんが、init_schema により DuckDB のテーブルとインデックスが作成されます。既存の DB を上書きはせず、CREATE IF NOT EXISTS / ON CONFLICT を多用するため既存データは基本的に保護されます。
- 環境変数の必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings プロパティで参照時にチェックされます。CI / 実行環境では .env の準備または環境変数の設定が必要です。

参考
- バージョン情報は kabusys.__version__ = "0.1.0"。