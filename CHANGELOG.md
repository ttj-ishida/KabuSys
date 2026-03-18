# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

なお、本CHANGELOGはコードベースの内容から推測して作成しています（実装済み機能・設計意図に基づく説明）。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- パッケージエントリポイント
  - kabusys パッケージを公開。__version__ = "0.1.0"。
  - パッケージトップで data, strategy, execution, monitoring を __all__ にて公開。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を探索。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサは export 形式、クォート・エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、以下の設定プロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト有り）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - リトライ機構（指数バックオフ、最大 3 回）を導入。HTTP 408/429/5xx をリトライ対象に設定。
    - 401 Unauthorized を検知した場合、自動でリフレッシュ（1 回のみ）して再試行する仕組みを実装（get_id_token と統合）。
    - ページネーション対応（pagination_key を用いたループ）。
    - JSON デコードエラーハンドリングと適切なエラーメッセージ。
  - データ取得関数:
    - fetch_daily_quotes（株価日足: OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時刻を記録するための fetched_at ポリシー（Look-ahead bias 対策、UTC で記録の慣習を使用）
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE（主キー: date, code）
    - save_financial_statements: raw_financials テーブルへ INSERT ... ON CONFLICT DO UPDATE（主キー: code, report_date, period_type）
    - save_market_calendar: market_calendar テーブルへ INSERT ... ON CONFLICT DO UPDATE（主キー: date）
  - ユーティリティ変換関数: _to_float / _to_int（安全な変換と失敗時の None 返却）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集と DuckDB 保存処理を実装。
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - fetch_rss: RSS フィード取得 → XML パース → 記事リスト生成。
      - defusedxml を使用して XML ベース攻撃（XML bomb 等）に対策。
      - HTTP/HTTPS スキーム検証とプライベートIP/ループバック検査による SSRF 防止。
      - リダイレクト時にスキーム・ホスト検査を行う専用ハンドラを実装。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - URL 正規化（小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）。
      - 記事IDは正規化 URL の SHA-256 先頭32文字で生成（冪等性保証）。
      - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存関数:
      - save_raw_news: raw_news テーブルにチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id（挿入された新規 id のリストを返す）。トランザクションでまとめて処理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの (news_id, code) 紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用して実際に追加された件数を取得）。
    - 銘柄コード抽出:
      - extract_stock_codes: テキストから 4 桁数字候補を抽出し、known_codes に存在するもののみ返却（重複除去）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋ Execution Layer のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（NOT NULL、PRIMARY KEY、CHECK 制約）を定義してデータ品質を担保。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - 初期化 API:
    - init_schema(db_path): 親ディレクトリの自動作成、全テーブルとインデックスの作成（冪等）。
    - get_connection(db_path): 既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL ヘルパーとジョブを実装（DataPlatform の方針に準拠）。
    - 差分更新のための最終取得日取得関数（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日調整ヘルパー（_adjust_to_trading_day）：非営業日の場合は過去最も近い営業日に調整するロジック。
    - run_prices_etl（株価日足差分 ETL）を実装（差分算出、backfill_days による後方再取得、jquants_client との連携、保存処理、ログ出力）。
  - ETL 実行結果を表す ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーの集約）。品質問題は quality.QualityIssue を想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集側で複数のセキュリティ対策を実施:
  - defusedxml による XML パース（XML 関連攻撃の緩和）。
  - SSRF 対策: URL スキーム検証、ホストがプライベートIPかの検査、リダイレクト先の事前検証。
  - レスポンス読み込み上限（MAX_RESPONSE_BYTES）と gzip 解凍後サイズチェックによるメモリ DoS 対策。
- J-Quants クライアントにおける認証トークン更新処理は allow_refresh フラグを用いて無限再帰を防止。

### Notes / Limitations
- DuckDB スキーマ定義は現時点での想定クエリパターンに最適化されていますが、大規模データ投入時のパフォーマンスチューニング（パーティショニングや VACUUM 相当の運用）は今後の課題。
- ETL の品質チェック（quality モジュール）の具体的な実装は別モジュール（kabusys.data.quality）に依存する想定。ETL は品質問題を検出しても継続する設計（呼び出し元での判断を想定）。
- news_collector の URL 正規化やトラッキングパラメータ除去ルールは既知のプレフィックスに基づく（拡張が必要な場合あり）。

-----------------------------------------
今後のリリースでは以下の点を想定:
- strategy, execution, monitoring モジュールの具象実装（ポートフォリオ最適化、発注実行、モニタリング／アラート機能）。
- 品質チェックモジュールの実装と ETL の自動通知（Slack 連携等）。
- テストカバレッジ強化、エラーハンドリングの詳細な改善。