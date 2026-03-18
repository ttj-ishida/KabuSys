KEEP A CHANGELOG形式に準拠した日本語の CHANGELOG.md を作成しました（初回リリース v0.1.0）。コードから推測して実装された主要機能・設計方針・セキュリティ対策などを記載しています。必要なら日付や表現の調整、追加の注釈を加えます。

CHANGELOG.md
=============
すべての変更は Keep a Changelog の慣例に従って分類しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-18
--------------------
初回公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。バージョンを 0.1.0 に設定。パッケージ公開用の __all__ を整備。

- 環境設定管理 (kabusys.config)
  - .env / .env.local と OS 環境変数を統合して読み込む自動ローダーを実装。プロジェクトルートは __file__ を起点に .git または pyproject.toml から検出。
  - .env パーサーの実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト向け）。
  - OS 環境変数の上書きを防ぐ protected セットをサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（環境・ログレベル）をプロパティ経由で取得。値検証（有効な env 値・ログレベル）を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL）(fetch_financial_statements)
    - JPX マーケットカレンダー (fetch_market_calendar)
  - 設計上の特徴:
    - API レート制限 (120 req/min) を守る固定間隔スロットリングを実装（_RateLimiter）。
    - リトライ戦略（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 受信時にリフレッシュトークンで id_token を自動再取得して 1 回のみ再試行。
    - ページネーション対応（pagination_key を用いた継続フェッチ）。
    - id_token のモジュールレベルキャッシュと強制リフレッシュを提供。
  - DuckDB への保存関数を実装（冪等性を重視）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各 save_* は ON CONFLICT DO UPDATE を用いて重複を排除し、fetched_at を記録。
  - 入力変換ユーティリティ（_to_float/_to_int）を実装し、不正値や空値の扱いを定義。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事取得・前処理・DB保存のワークフローを実装。
  - セキュリティ/堅牢性:
    - defusedxml による XML パースを導入（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカルアドレスの検出と拒否、リダイレクト時の事前検証ハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再チェックを行い、メモリ DoS を防止。
    - User-Agent・Accept-Encoding ヘッダ設定。
  - フィード処理:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化URLの SHA-256 の先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate の RFC2822 互換パースと UTC 変換、失敗時は警告ログを出して現在時刻で代替。
    - fetch_rss によるフィード収集、記事の抽出。
  - DuckDB への保存:
    - save_raw_news: バルク挿入をチャンクで行い、INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて実際に挿入された記事IDを返す。トランザクションで一括コミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（重複除去、RETURNING で実挿入数を返す）。
  - 銘柄コード抽出: テキスト中の 4 桁数字候補から既知コード集合でフィルタする extract_stock_codes を提供。
  - 統合ジョブ run_news_collection: 複数ソースを処理し、新規保存数・銘柄紐付けを行う。各ソースは独立して例外ハンドリング（1ソース失敗でも他は継続）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）+ Execution レイヤーのテーブル DDL を実装。
  - 主要テーブル（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を定義。
  - 適切な型・制約（CHECK, PRIMARY KEY, FOREIGN KEY）および頻出クエリ用のインデックスを作成するDDLを提供。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成、全テーブルとインデックスを作成して接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL パイプラインの基盤を実装。
  - ETLResult データクラス: 各 ETL 実行のメタ情報（取得数・保存数・品質問題・エラー等）を格納・辞書化する機能を提供。
  - DB の最終取得日を参照して差分（差分開始日）を自動算出するヘルパーを用意（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 非営業日の調整ヘルパー (_adjust_to_trading_day) と市場カレンダー先読みロジック。
  - run_prices_etl の骨格実装: backfill_days による再取得（デフォルト 3 日）、_MIN_DATA_DATE による初回ロードの開始日補正、J-Quants からの取得と jquants_client.save_daily_quotes による保存を呼び出す設計（差分取得戦略、保存＆ログ記録）。品質チェックモジュール（quality）との統合箇所を想定するインフラを整備。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサーに defusedxml を利用し安全に XML をパース。
- RSS/HTTP 周りで SSRF 対策を実装（スキーム検証、プライベートIP検出、リダイレクト時検査）。外部リソース取得時の Content-Length/最大読み取りバイト数チェックを追加。
- .env 読み込み時に OS 環境変数の上書きを保護する仕組みを実装（protected set）。

Notes / Implementation details
- J-Quants API のリトライ対象ステータスや backoff の挙動、429 時の Retry-After 優先等は実運用を考慮して実装済み。
- DuckDB 側の保存は SQL の ON CONFLICT を使った冪等処理を採用。news_collector は INSERT ... RETURNING を多用して実挿入数を正確に把握する。
- ニュース記事IDは URL 正規化後の SHA-256 の先頭32文字を用いることでトラッキングパラメータ差分による重複を低減。
- コード中の docstring/コメントで DataPlatform.md / DataSchema.md / Section などの設計資料に準拠する旨を明記している（設計ドキュメントとの整合を想定）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

参照
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実装済ファイル:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/news_collector.py
  - src/kabusys/data/schema.py
  - src/kabusys/data/pipeline.py
  - その他パッケージ初期ファイル（__init__.py 等）

今後の予定（提案）
- pipeline.run_prices_etl 等の ETL 関数のエラーハンドリング・品質チェック結果の上位伝播と自動通知（Slack 等）を充実化。
- 単体テスト・統合テストの追加（HTTP クライアント・DB 操作のモックを含む）。
- news_collector の既知銘柄一覧更新戦略（定期取得/差分更新）や NLP による銘柄検出精度向上。
- jquants_client のページネーションにおける大規模取得時のメモリ使用最適化（ストリーム処理）や並列取得時のレート制御改善。

--- END ---