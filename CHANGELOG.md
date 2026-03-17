# Changelog

すべての変更は Keep a Changelog の仕様に準拠しています。  
このプロジェクトの初期リリース（v0.1.0）に含まれる主要な実装内容と設計上の決定を日本語でまとめます。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

### Added
- パッケージ基本情報
  - パッケージ名 "KabuSys"、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パッケージの公開APIとして data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート判定は .git または pyproject.toml を使用）。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パース機能（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱いなど）。
  - 必須設定取得のヘルパー _require。
  - 有効な環境値チェック（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL の検証）。
  - 各種設定プロパティ：J-Quants トークン、kabu API、Slack トークン・チャンネル、DB パス（DuckDB/SQLite）、ランタイム判定（is_live/is_paper/is_dev）など。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本的な API 呼び出しユーティリティと JSON パース。
  - レート制限（120 req/min）を満たす固定間隔スロットリング実装（_RateLimiter）。
  - リトライ戦略（最大 3 回、指数バックオフ、408/429/5xx に対するリトライ）を実装。
  - 401 Unauthorized 受信時に refresh token から id_token を自動更新して 1 回リトライするロジック。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPXマーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 数値変換ユーティリティ (_to_float, _to_int) を実装し、安全に None を扱う挙動を定義。
  - fetched_at（UTC）を記録し、データの「システムがいつ知り得たか」をトレース可能に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し DuckDB に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対策）。
    - URL スキーム検証（http/https のみ許可）と SSRF 緩和（ホストがプライベート/ループバック/リンクローカルであれば拒否）。
    - リダイレクト時にもスキームとホスト検証を行うカスタムリダイレクトハンドラ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _TRACKING_PARAM_PREFIXES）。
  - 記事ID の生成: 正規化 URL の SHA-256 ハッシュ先頭 32 文字で冪等性を担保。
  - テキスト前処理（URL除去・空白正規化）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い挿入された記事IDのみを返却。チャンク挿入かつ単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING + RETURNING で保存。
  - 銘柄コード抽出 (extract_stock_codes): テキストから4桁の候補を抽出し、known_codes セットによるフィルタリング。
  - run_news_collection: 複数 RSS ソースを順に処理し、個々のソースは独立してエラーハンドリング（1ソース失敗でも継続）。新規保存数の集計と銘柄紐付けのバルク実行を行う。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。

- データベーススキーマ (src/kabusys/data/schema.py)
  - DuckDB 用 DDL を定義し、Raw / Processed / Feature / Execution 層のテーブルを実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY など）を付与。
  - 頻出クエリのためのインデックスを作成（例: code×date インデックス、orders/status 等）。
  - init_schema(db_path) による初期化関数と get_connection の公開。init_schema は親ディレクトリ自動作成を行い、冪等にテーブル作成を実行。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づくユーティリティを実装:
    - ETLResult dataclass: 実行結果、品質チェック、エラー一覧を保持する（to_dict によるシリアライズ対応）。
    - _table_exists, _get_max_date ユーティリティ（DuckDB での最終日取得等）。
    - 市場カレンダーに基づく営業日調整 _adjust_to_trading_day（過去方向に調整、最大30日遡り）。
    - 差分更新用ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - run_prices_etl（株価日足差分ETL）: 差分更新ロジック（最終取得日の backfill を考慮）、J-Quants からの取得と保存呼び出し。デフォルトの backfill_days は 3、データの最小開始日 _MIN_DATA_DATE を 2017-01-01 に設定。
  - 品質チェックモジュール（quality）と連携する設計（品質問題は集約して返却・呼び出し元で判断）。

### Fixed
- 初期リリースにつき「既知の bugfix」は特になし。

### Security
- ニュース収集での XML パースに defusedxml を採用し、XML ベース攻撃を緩和。
- RSS フェッチでの SSRF 対策（スキーム検証、プライベートホスト検出、リダイレクト時の検査）。
- レスポンス読み込みサイズと gzip 解凍後サイズチェックでメモリDoS / Zip bomb を軽減。
- 環境変数自動読み込みで OS 環境変数の保護（.env.local 上書きの際に既存 OS 環境変数を保護する仕組み）。

### Performance
- API クライアントでのレートリミット待機により J-Quants のレート制限を遵守（120 req/min）。
- news_collector の DB バルク挿入はチャンクサイズ（デフォルト _INSERT_CHUNK_SIZE=1000）で実施しオーバーヘッドを抑制。
- DuckDB への冪等保存は ON CONFLICT を活用し重複処理を DB 側で効率化。

### Notes / Known limitations
- 初期リリースのため、strategy / execution / monitoring の実装はパッケージ階層に用意されているが（__all__ にも宣言）、今回の提供コードでは各パッケージの中身は未開発または空の __init__（プレースホルダ）となっています。
- run_prices_etl の戻り値・処理フローは基本実装済みですが、パイプライン全体（品質チェック呼び出しやカレンダー先読み統合など）の統合テスト・運用試験は今後必要です。
- J-Quants API 呼び出しは urllib を利用した実装のため、より高度な機能（接続プールや timeout/keepalive の最適化）が必要な場合は HTTP クライアントの変更を検討してください。
- README / Usage examples や .env.example の整備は今後の課題。

### Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

開発・運用に関する補足や、特定の機能（例: ETL のスケジューリング、strategy 実装の優先度、CI/テスト方針）について CHANGELOG に追記したい場合は指示してください。