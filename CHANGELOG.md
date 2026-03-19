Keep a Changelog
=================

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

[Unreleased]
------------

- （現在の配布における初期リリースは下記 0.1.0 を参照してください）

[0.1.0] - 2026-03-19
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を追加しました。主な追加点・設計上の注意点は以下の通りです。

Added
- パッケージ基盤
  - パッケージエントリポイント src/kabusys/__init__.py を追加。バージョンは 0.1.0。
  - サブパッケージ配下に data, strategy, execution, monitoring 等のモジュール群を想定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（環境変数より下位、.env.local は .env を上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
  - .env の文法パーサ実装（export プレフィックス、クォート、インラインコメント処理、エスケープ対応）。
  - Settings クラスを提供し、必要な設定値をプロパティで取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境（KABUSYS_ENV）は development / paper_trading / live の検証を行い不正値は例外を送出。
  - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
  - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。Path オブジェクトで取得。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ（_request）を実装：JSON デコード、例外処理、ページネーション対応。
  - レート制限（120 req/min）を固定間隔スロットリングで実装する RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象にし、429 の場合は Retry-After を優先。
  - 401 Unauthorized を検出した場合、リフレッシュ処理を 1 回行って再試行する仕組み（トークンキャッシュと get_id_token）。
  - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）でページネーションをサポート。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除。
  - 型変換ユーティリティ _to_float/_to_int により文字列を安全に数値化（"1.0" などの扱いに注意）。

- ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得・前処理・DB 保存ワークフローを実装（fetch_rss, save_raw_news, save_news_symbols 等）。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト検査用ハンドラ、ホストがプライベート/ループバック/リンクローカルでないことの検証。
    - URL スキームは http/https のみ許可。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - トラッキングパラメータの除去（utm_*, fbclid 等）と URL 正規化。
  - テキスト前処理（URL 除去・空白正規化）。
  - DuckDB への保存はチャンク化・トランザクション化し、INSERT ... RETURNING を使って新規挿入分のみ識別。
  - 銘柄抽出ユーティリティ（4桁数字検出と known_codes フィルタリング）と複数記事分の一括紐付け保存ロジック。

- DuckDB スキーマ初期化（src/kabusys/data/schema.py）
  - Raw Layer テーブルの DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
  - データレイヤ（Raw / Processed / Feature / Execution）を想定したスキーマ設計の土台を実装。

- 研究用ユーティリティ（src/kabusys/research/）
  - feature_exploration.py:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB から一度に取得。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）計算。十分なデータが無ければ None。
    - rank, factor_summary: 同順位の平均ランク処理、基本統計量計算（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装（テスト容易性・配布軽量化）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: ATR(20) / atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を厳密に管理。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（EPS が 0/欠損なら None）。
  - research パッケージ __init__ で主要関数をエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサに defusedxml を使用、SSRF を防ぐリダイレクト検査、プライベートアドレス判定、受信バイト数制限を実装。
- J-Quants クライアントはトークン自動リフレッシュを扱うが、無限再帰を防ぐため get_id_token 呼び出し時は allow_refresh=False を尊重。

Notes / Breaking changes / 注意事項
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティ呼び出し時に未設定だと ValueError を送出します。アプリ起動前に設定してください。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。
- DuckDB を使用するため実行環境に duckdb パッケージが必要です。news_collector は defusedxml へ依存します。
- research モジュールは標準ライブラリのみで実装されており pandas 等を使用しません。大量データ処理の最適化は今後の改善点です。
- _to_int の仕様に注意: "1.0" のような文字列は int に変換できますが、"1.9" のように小数部が 0 以外の場合は None を返します（意図しない切り捨てを防止するため）。
- J-Quants API のレート制限・リトライ挙動およびトークンリフレッシュの実装は基本的な堅牢性を提供しますが、運用上の観察に基づくチューニングが必要になる可能性があります。

Acknowledgements / Implementation notes
- 設計方針として、Research 系関数は外部 API にアクセスしない純粋関数的な実装を目指しています（DuckDB の prices_daily / raw_financials テーブルのみ参照）。
- ニュース収集は再現性と冪等性を重視しており、記事 ID の正規化・ハッシュ化と DB 側の UNIQUE 制約で重複を回避します。
- DB 保存処理はトランザクションでまとめられ、失敗時はロールバックして例外を再送出します。

今後の予定（抜粋）
- Processed / Feature Layer 向けの ETL パイプラインおよびインデックス整備。
- strategy / execution モジュールの具体的なアルゴリズム実装とテスト。
- パフォーマンス改善（大量データでの DuckDB クエリ最適化、並列取得など）。
- 追加のデータソース（複数 RSS、ニュース API）や NLP ベースの銘柄抽出改善。

--- 

この CHANGELOG は、ソースコードから想定される変更点・機能を基に作成しています。追加のリリースや修正があれば適宜更新してください。