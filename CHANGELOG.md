# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。

### Added
- 基本パッケージ定義
  - パッケージ初期化: kabusys のバージョンを "0.1.0" として定義（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env/.env.local の読み込み順と override 挙動（OS 環境変数保護）を実装。
  - .env 行パーサーを実装（コメント、export プレフィックス、クォート内のエスケープ、インラインコメント処理対応）。
  - Settings クラスを実装し、J-Quants トークンや kabu API パスワード、Slack トークン／チャンネル、DB パス、実行環境（development/paper_trading/live）やログレベルの検証付きプロパティを提供。
  - 環境値未設定時は明示的に例外を上げる require ロジックを実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（JSON デコードエラーハンドリング、タイムアウト）。
  - レート制御: 固定間隔スロットリングで 120 req/min を守る RateLimiter を実装。
  - リトライ戦略: 指数バックオフ・最大試行回数（3回）、HTTP 408/429/5xx によるリトライ、429 の Retry-After 優先対応を実装。
  - 401 Unauthorized 受信時の id_token 自動リフレッシュ（1 回のみ）を実装し、ページネーション間でのトークンキャッシュを保持。
  - get_id_token（リフレッシュトークンから idToken を取得）を実装。
  - データ取得関数を実装（ページネーション対応）:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数を実装（冪等性を重視: ON CONFLICT DO UPDATE）:
    - save_daily_quotes
    - save_financial_statements
    - save_market_calendar
  - データ変換ユーティリティ: _to_float / _to_int（型安全な変換、空値・不正値処理）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存するフルスタック実装。
  - 設計/セキュリティ上の配慮:
    - defusedxml による XML パース（XML Bomb 等への防御）。
    - SSRF 対策: リダイレクト先やホストがプライベートアドレスでないことを検査するハンドラを導入（_SSRFBlockRedirectHandler）、および URL スキーム検証。
    - レスポンス最大バイト数（MAX_RESPONSE_BYTES）チェックと gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化時にトラッキングパラメータを除去し、SHA-256（先頭32文字）で記事IDを生成して冪等性を担保。
    - HTTP/HTTPS スキームのみ許可し、mailto:, file: 等を排除。
  - パース・前処理機能:
    - 前処理（URL 除去、空白正規化）の preprocess_text。
    - RSS pubDate のパース（タイムゾーンを UTC に正規化）とフォールバック。
    - content:encoded の優先処理、description のフォールバック。
  - DB 保存/バルク処理:
    - save_raw_news: INSERT ... RETURNING id を用いたチャンクインサート（トランザクションでまとめて挿入）を実装。新規挿入された記事IDのリストを返却。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING、INSERT ... RETURNING を用いて実際に保存された件数を返す）。
    - チャンクサイズ制御による SQL 長・パラメータ数対策。
  - 銘柄抽出ロジック:
    - 正規表現ベースで4桁銘柄コードを抽出し、既知銘柄セットでフィルタして重複排除する extract_stock_codes。
  - 統合収集ジョブ:
    - run_news_collection により複数 RSS ソースを順次処理し、ソース単位でのエラーハンドリング（1ソース失敗しても他を継続）と、新規記事取得数の結果レポートを返却。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを作成する SQL 文群を定義。
  - init_schema(db_path) を実装：必要に応じて親ディレクトリを作成し、全テーブル・インデックスを冪等に作成して接続を返す。
  - get_connection(db_path) を実装：既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL 実行結果を表す dataclass ETLResult を実装（結果集約、品質問題リスト、エラー一覧、シリアライズ用 to_dict）。
  - スキーマ・テーブル存在チェック、最大日付取得ユーティリティを実装（_table_exists / _get_max_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー _adjust_to_trading_day を実装（過去方向に調整、最大30日遡る）。
  - 差分更新用ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - 個別 ETL ジョブ（差分取得）:
    - run_prices_etl を実装（最終取得日からの差分再取得、backfill_days による後出し修正吸収、取得 → 保存の流れ）。品質チェックモジュールへの連携を意識した設計（quality モジュールとの連携点を持つ）。

### Security
- RSS 処理における複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 防止のためのスキーム検証・プライベートホスト拒否・リダイレクト検査。
  - レスポンスサイズ制限と Gzip 解凍後の検査（DoS / Gzip bomb 対策）。
- 環境変数読み込みで OS 環境を保護する protected キーの概念を導入（.env による上書きを制御）。

### Notes
- 多数の関数で DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を直接受け取る設計にしており、テスト時に in-memory DB (":memory:") を利用可能。
- jquants_client の API 呼び出しはページネーション・トークン共有・自動リフレッシュ・レート制御を考慮して実装しているため、本番運用での安定性を重視した設計となっている。
- run_prices_etl の末尾がコード内で切れている（返り値のタプルが途中で終わっている）ため、実装の続きを追加する必要がある可能性があります（現状は取得件数を返す実装が未完）。（注: コードベースから推定した未完了箇所の注記）

---

今後の変更はこのファイルに追記します。問題や追加要望があれば changelog に反映します。