Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース。基本構成:
  - kabusys パッケージ本体とサブパッケージ骨格 (data, strategy, execution, monitoring を公開)
  - バージョン: 0.1.0
- 環境設定管理 (kabusys.config):
  - .env/.env.local ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント扱いのルール。
  - OS 環境変数を保護する protected 機能（.env.local は既存キーを上書き可能）。
  - Settings クラスを提供し、必須値取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）・既定値（KABU_API_BASE_URL, DB パス等）・値検証（KABUSYS_ENV, LOG_LEVEL）・実行環境フラグ（is_live / is_paper / is_dev）を公開。
- J-Quants クライアント (kabusys.data.jquants_client):
  - API 呼び出しユーティリティを実装（_request）。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大 3 回。HTTP 408/429 と 5xx を再試行対象。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ（再帰防止フラグあり）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期 BS/PL)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等設計、ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データ変換ユーティリティ: _to_float / _to_int（堅牢な型変換、空値/異常値ハンドリング）
  - id_token キャッシュ（モジュールスコープ）とページネーション間のトークン共有
- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS から記事を収集して raw_news に保存するフローを実装。
  - セキュアな XML パーサ（defusedxml）を使用して XML Bomb 等の攻撃を防御。
  - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_*, fbclid 等）の除去、フラグメント削除、クエリパラメータのソート。
  - 記事 ID: 正規化 URL の SHA-256 の先頭32文字を使用（冪等性確保）。
  - SSRF 対策:
    - fetch_rss で事前にホストがプライベートアドレスでないことを検証。
    - リダイレクト時にスキーム/ホストを検査する _SSRFBlockRedirectHandler を導入。
    - http/https 以外のスキームを拒否。
  - レスポンスサイズ保護:
    - MAX_RESPONSE_BYTES = 10 MB の上限チェック（Content-Length と実際の読み込み両方）。
    - gzip 解凍後にもサイズチェック（Gzip Bomb 対策）。
  - RSS のパースと記事整形:
    - content:encoded 名前空間対応、description 優先フォールバック、pubDate の安全なパース（UTC 変換・フォールバック）。
    - URL 除去と空白正規化の前処理。
  - DB 保存:
    - save_raw_news はチャンク化（_INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk で記事と銘柄の紐付けをトランザクション単位で行い、INSERT ... RETURNING で挿入数を正確に取得。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字候補を抽出し、known_codes に基づいてフィルタ（重複排除）。
  - 統合ジョブ run_news_collection を実装（ソース毎に独立してエラーハンドリング、既知コードがあれば news_symbols の一括登録）。
- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema):
  - Raw / Processed / Feature / Execution の 3 層 + 実行レイヤーのテーブル定義を含む DDL を提供。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など（各種制約・チェック・PK/外部キーを含む）。
  - インデックス定義（頻出クエリ向け）。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・接続返却、get_connection(db_path) で既存 DB へ接続。
- ETL パイプライン (kabusys.data.pipeline):
  - ETL の設計方針・差分更新・バックフィル機能を実装。
  - ETLResult dataclass を導入し、取得数、保存数、品質問題、エラーを集約。品質問題は to_dict でシリアライズ可能。
  - 差分ヘルパー: テーブル存在チェック、最大日付取得ユーティリティ。
  - 市場カレンダーヘルパー: 非営業日の調整ロジック（直近の営業日にロールバック）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date ユーティリティ。
  - run_prices_etl の差分ロジック（最終日から backfill_days デフォルト 3 日で再取得）。初期データ開始日: 2017-01-01。
  - カレンダー先読み日数定数（_CALENDAR_LOOKAHEAD_DAYS = 90）などの設定。
- その他:
  - コードベースにログ出力箇所を多数実装（情報・警告・例外ログ）。
  - テスト容易性を考慮した設計（_urlopen のモック差し替えや id_token 注入可能など）。

Security
- ニュース収集における SSRF 対策（ホスト種別判定・リダイレクト検査）を実装。
- XML パースに defusedxml を使用して XML 関連攻撃に対処。
- レスポンスサイズと gzip 解凍後サイズの上限チェックを導入（メモリ DoS・Gzip Bomb 対策）。
- .env の読み込みはデフォルトで実行されるが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストでの安全な振る舞いを確保）。
- 環境変数上書き時に OS 環境変数を保護する仕組みを実装。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Notes / Implementation details
- J-Quants API のレート制限とリトライ挙動（120 req/min、最大 3 回、429 の Retry-After 優先など）はクライアント側で管理しているため、呼び出し側は単純に fetch_* を使用可能。
- DuckDB 側の保存は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）しているため、再実行に強い。
- news_collector の記事 ID はトラッキングパラメータを除去した上でハッシュ化するため、同一コンテンツの重複登録を低減する設計。

Known limitations / TODO
- strategy / execution / monitoring の実装は骨格のみで詳細ロジックは未実装（将来的に発注ロジック・戦略・監視機能を追加予定）。
- quality モジュール連携は参照しているが、品質チェックの具体的なルールやエラー処理の運用ポリシーは今後整備予定。

-----
本 CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートと差異がある場合があります。