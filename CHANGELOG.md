# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはコードベースから推測して生成した初期リリースノートです。

現在のバージョン: 0.1.0 - 2026-03-17

## [0.1.0] - 2026-03-17

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎機能を追加。
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージバージョン (0.1.0) と公開サブモジュール ([data, strategy, execution, monitoring]) を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動読み込み（読み込み優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出（.git または pyproject.toml による）に基づく自動ロード。ルートが見つからない場合はスキップ。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート。
  - .env パーサー: export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 環境変数保護: OS 環境変数を保護するための上書き制御（.env.local が .env を上書き可能だが既存 OS 環境変数は保護）。
  - 必須設定取得ヘルパー (_require) と型変換（Path へ変換等）を持つ Settings クラスを提供。
  - 設定検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の妥当性チェック、 is_live / is_paper / is_dev のプロパティを追加。

- J-Quants データクライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得機能:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 設計方針の実装:
    - API レート制限制御（_RateLimiter、デフォルト 120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx のリトライ）を実装。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - id_token キャッシュ共有（モジュールレベル）によりページング間でトークンを再利用。
  - DuckDB への保存関数（冪等に保存: ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ: _to_float / _to_int（妥当性チェック、空値ハンドリング等）。
  - fetched_at の UTC 記録によりデータの取得時刻をトレース。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集、前処理、DB 保存、銘柄紐付けのフローを提供。
  - 主な機能:
    - fetch_rss: RSS 取得、XML パース（defusedxml を使用）、content:encoded / description の優先処理、pubDate パース（RFC 2822）、記事リスト生成。
    - preprocess_text: URL 除去、空白正規化。
    - URL 正規化と記事 ID 生成: トラッキングパラメータ除去、クエリソート、SHA-256（先頭32文字）で記事IDを生成。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストのプライベートアドレス判定（IP 直接判定および DNS 解決から A/AAAA レコードを判定）。
      - リダイレクト時にスキーム/プライベートアドレスを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - XML パース失敗やサイズ超過などの健全性チェックで安全にスキップしログを残す。
    - DB 保存: save_raw_news（INSERT ... RETURNING を使い、チャンク単位でトランザクション処理）、save_news_symbols（銘柄紐付け）、内部バルク処理用 _save_news_symbols_bulk。
    - 銘柄コード抽出: 正規表現による 4 桁数字抽出と既知コードフィルタ（extract_stock_codes）。
    - run_news_collection: 複数ソースの統合収集ジョブ、ソース単位で隔離されたエラーハンドリング、既知銘柄が与えられた場合は紐付け処理を実行。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataPlatform に基づく 3 層構造（Raw / Processed / Feature）と Execution 層のテーブル DDL を定義。
  - 主なテーブル群:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約、PRIMARY/FOREIGN KEY、インデックス定義を含む。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成、DDL 実行、インデックス作成を行い接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン基礎 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果を構造化（取得数、保存数、品質問題、エラー等）。
  - 差分更新サポート:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパーで最終取得日を取得。
    - run_prices_etl: 差分 ETL ロジック（一部実装: date_from の自動算出、backfill_days デフォルト 3 日、fetch + save の呼び出し）。
  - 市場カレンダーヘルパー: _adjust_to_trading_day により非営業日を直近営業日に補正（最大30日探索、カレンダー未取得時はフォールバック）。
  - ETL の設計方針（差分更新、backfill による後出し修正対策、品質チェックの継続処理）を実装。

- その他
  - モジュール / パッケージの空 __init__ ファイルを配置（strategy, execution, data）。
  - ロギングを適切に配置（各主要処理で info/warning/exception）。

### Security
- SSRF/外部入力対策を強化:
  - ニュース収集で URL スキーム制限、プライベートアドレス判定、リダイレクト時検査を実装。
  - XML パースに defusedxml を使用して XML Bomb などを防止。
  - レスポンス最大バイト数を制限（メモリ DoS 対策）。
  - .env 読み込み時のファイル読み取り失敗は警告により安全にスキップ。
- 認証トークンの取り扱い:
  - J-Quants の id_token キャッシュと自動リフレッシュにより、意図しない挙動や再帰を防止するため allow_refresh フラグを導入。

### Changed
- 初回公開のため変更履歴なし（初回追加の集合）。

### Fixed
- 初回公開のため修正履歴なし。

### Deprecated
- なし

### Removed
- なし

---

注意:
- 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。細部（公開 API の追加説明、リリース日、マイナー/パッチ番号の運用方針など）は実際のリリースフローに合わせて更新してください。
- run_prices_etl の戻り値や pipeline 内の一部処理はコード断片のため補完が必要な箇所がある可能性があります。実運用前に完全なテストとレビューを推奨します。