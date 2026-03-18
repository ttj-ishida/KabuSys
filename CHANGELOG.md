Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目すべき変更を時系列で記録します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
- (なし)

[0.1.0] - 2026-03-18
Added
- 初期リリース: KabuSys 日本株自動売買システムのコア実装を追加。
  - パッケージ基盤
    - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
    - モジュール構成: data, strategy, execution, monitoring を公開。
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env パーサー実装（export 形式、クォート処理、インラインコメントの扱いなどに対応）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラス: J-Quants / kabuステーション / Slack / DB パス等のプロパティ、値検証（環境種別・ログレベル等）。
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しユーティリティ（_request）を実装。JSON デコードエラーハンドリング。
    - レート制御（固定間隔スロットリング）で 120 req/min を遵守する RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ機能。
    - ページネーション対応のデータ取得: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
    - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を使用）、fetched_at に UTC タイムスタンプを記録。
    - 型変換ユーティリティ: _to_float、_to_int（安全なパースと None ハンドリング）。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィード収集: fetch_rss、記事整形（preprocess_text）、記事IDの生成（URL 正規化→SHA-256 の先頭32文字）。
    - URL 正規化: トラッキングパラメータ除去（utm_ 等）、キーソート、フラグメント除去。
    - セキュリティ対策: defusedxml による XML パース、SSRF 対策（スキーム検証、プライベートホスト検査、リダイレクト時の事前検証）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip の解凍後サイズチェック（Gzip bomb 対策）。
    - DuckDB への保存: save_raw_news（チャンク分割・トランザクション・INSERT ... RETURNING を利用し新規挿入IDを返す）、save_news_symbols、内部バルク保存 _save_news_symbols_bulk。
    - 銘柄コード抽出ロジック（4桁数字の抽出と known_codes フィルタ）。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを定義。
  - スキーマ定義 (src/kabusys/data/schema.py)
    - DuckDB のスキーマ一式を定義（Raw / Processed / Feature / Execution 層）。
    - テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - インデックス定義（頻出クエリに対する索引）。
    - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等実行）と get_connection().
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETLResult データクラス（実行結果の収集、品質検出のまとめ、辞書変換）。
    - 差分更新ヘルパー: テーブル存在チェック、最大日付取得ユーティリティ。
    - 市場カレンダーに基づく取引日の調整ヘルパー。
    - 差分 ETL のための run_prices_etl（date_from/backfill の自動算出、fetch → save のフロー）。
    - 初期定数: _MIN_DATA_DATE（2017-01-01）、カレンダー先読み日数、デフォルト backfill 日数等。

Security
- XML パーサで defusedxml を使用して XML Bomb 等に対処。
- RSS フェッチ時の SSRF 対策:
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベートアドレスかを判定しアクセス遮断（DNS 解決の A/AAAA 検査含む）。
  - リダイレクト時にもスキームとホストを検証するカスタムハンドラを導入。
- レスポンスサイズ上限と gzip 解凍後チェックでメモリDoS（圧縮爆弾）を防止。
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected keys）。

Reliability / Performance
- J-Quants API コールに対してレート制御、リトライ（429 の Retry-After 優先）、指数バックオフを実装。
- id_token のモジュールキャッシュを導入しページネーション間でトークン再利用。
- DuckDB への保存は冪等性を意識（ON CONFLICT）、大量挿入はチャンク（_INSERT_CHUNK_SIZE）に分割してトランザクションで実行。
- save_* 系は挿入・更新数をログで報告。

Fixed
- (初版のため該当なし)

Changed
- (初版のため該当なし)

Removed
- (初版のため該当なし)

Notes / Known issues
- run_prices_etl の実装において、ファイル末尾付近に不完全な return 文（"return len(records), "）があり、保存数を返す期待通りのタプルが未完成となっている箇所が存在する。実行時にエラーや不完全な戻り値を招く可能性があり、修正が必要。
- デフォルト RSS ソースは単一（Yahoo）であり、運用ではソース追加やフィード管理が必要。
- 一部の機能（pipeline の他ジョブや strategy/execution/monitoring の実装）はスケルトンであり、実稼働には追加実装が必要。
- DuckDB スキーマは初期化されるが、外部システム（kabuステーション、Slack 連携等）との統合設定・運用ルールは別途整備が必要。
- .env の自動読み込みはプロジェクト検出ロジックに依存するため、配布先で .git や pyproject.toml が存在しない場合はロードがスキップされる点に注意。

Authors
- コードベースに基づき推測して自動生成。

ライセンスやその他メタ情報はソースリポジトリを参照してください。