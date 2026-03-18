CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従っています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- 初期公開: KabuSys 日本株自動売買システムの基本モジュール群を追加
  - パッケージ構成
    - kabusys (トップレベルパッケージ)
    - サブパッケージ: data, strategy, execution, monitoring（strategy/execution はパッケージ初期化ファイルのみのステブを含む）
  - バージョン: 0.1.0 を設定

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（配布後も動作）
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）
  - .env 解析は export 形式やクォート、インラインコメント等に対応
  - 設定アクセス用 Settings クラスを提供
    - 必須変数の取得（未設定時は ValueError）
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV 等
    - 値検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
    - convenience プロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - OHLCV（株価日足）、財務データ、マーケットカレンダーの取得実装（ページネーション対応）
  - 高信頼性設計
    - API レート制限遵守（120 req/min）: 固定間隔スロットリング実装 (_RateLimiter)
    - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ
    - JSON デコード失敗時の明示的エラー
  - fetched_at を UTC ISO8601 で保存し Look-ahead Bias をトレース可能に
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を利用して上書き
    - PK 欠損行はスキップして警告ログ出力
    - 型変換ユーティリティ (_to_float / _to_int) を提供

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と raw_news への保存を実装
  - セキュリティ・堅牢性対策
    - defusedxml を使用した XML パース（XML Bomb 対策）
    - URL スキーム検証（http/https のみ許可）とリダイレクト時のスキーム/ホスト検査（SSRF 対策）
    - リダイレクト先がプライベート/ループバック/リンクローカル/マルチキャストの場合を遮断
    - レスポンスサイズ上限（デフォルト 10MB）でメモリ DoS を防止、gzip 解凍後も検査
    - 受信ヘッダの Content-Length を先にチェック
  - 記事 ID はトラッキングパラメータ除去後の URL を SHA-256 でハッシュ化し先頭 32 文字を利用（冪等性保証）
  - URL 正規化（クエリのソート・トラッキングパラメータ削除・フラグメント削除）
  - テキスト前処理: URL 除去・空白正規化
  - DB 保存
    - raw_news: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用、1 トランザクションで挿入
    - news_symbols: 記事と銘柄コードの紐付けを INSERT ... RETURNING で正確に集計、トランザクション管理
    - bulk 保存の内部ユーティリティ（重複除去・チャンク化）
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、既知のコードセットでフィルタ（重複除去）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブルを定義
  - 代表的なテーブル
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_* など
  - 型チェック / CHECK 制約を多用してデータ品質を向上
  - よく使われるクエリ向けのインデックスを作成
  - init_schema(db_path) でディレクトリ作成（必要時）→ テーブルとインデックス作成（冪等）
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（差分取得）を行う ETL ジョブ基盤
    - DB の最終取得日を参照して自動で date_from を決定（backfill_days により遡り再取得）
    - 市場カレンダーは先読み（デフォルトで将来 90 日分を検討）
    - 最小データ開始日を定義（_MIN_DATA_DATE）
  - ETLResult データクラスを導入（取得数、保存数、品質問題、エラー等を集約）
    - has_errors / has_quality_errors 等のユーティリティ
    - to_dict() で品質チェック結果をシリアライズ可能
  - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）
  - run_prices_etl 実装（差分計算、jq.fetch_daily_quotes の取得と jq.save_daily_quotes への保存、ログ出力）
  - 品質チェックは quality モジュールと連携する設計（収集は継続し、呼び出し元で対処を決定）

Changed
- （初版）該当なし

Fixed
- （初版）該当なし

Security
- ニュース取得処理に以下のセキュリティ対策を導入
  - defusedxml による安全な XML パース
  - SSRF 対策: スキーム検証、リダイレクト先の検査、プライベートアドレス拒否
  - レスポンスサイズ制限と gzip 解凍後のサイズチェック（Gzip-bomb 対策）
- J-Quants クライアントは認証トークンの自動リフレッシュとリトライで安定性を確保

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 初回は schema.init_schema(settings.duckdb_path) でスキーマ初期化を行ってください
- jquants_client の rate limit は内部で 120 req/min に制限されています。高頻度の並列取得は設計上制限されます。

Acknowledgements
- 本リリースはデータ取得・保存・ETL の基盤を中心に実装しています。戦略実装（strategy）や発注実行（execution）などは今後のリリースで拡張予定です。