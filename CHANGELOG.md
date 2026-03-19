CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

[Unreleased]
------------

（現在のリポジトリ状態は最初の公開バージョン 0.1.0 に相当します。以降の変更はここに追加してください。）

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージの初期リリース。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定し、公開モジュールを定義。
- 環境設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）と OS 環境変数から設定値を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に自動検索（CWD 非依存）。
  - .env 行パーサ実装: export 形式、クォート文字列のエスケープ、インラインコメント処理などを考慮。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト等で利用）。
  - Settings クラスを提供し、主要な設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と便利プロパティ（duckdb/sqlite パス、env/log_level 判定、is_live/is_paper/is_dev）を公開。
  - 設定値検証（KABUSYS_ENV / LOG_LEVEL の有効値チェック、必須環境変数未設定時は ValueError）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限管理（120 req/min）を固定間隔のスロットリングで実装する RateLimiter を導入。
  - 冪等かつ実用的なリトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）を実装。
  - 401 Unauthorized を検出した場合、自動でトークンをリフレッシュして 1 回だけリトライする機能を実装。
  - ページネーション対応（pagination_key）で全ページを取得する fetch_* 系関数を提供:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数を提供（冪等化: ON CONFLICT DO UPDATE / DO NOTHING）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、文字列データや空値を安全に扱う。
  - id_token のモジュールレベルキャッシュを導入し、ページネーションや複数呼び出しで共有。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する一連の処理を実装。
  - セキュリティ/堅牢性対策を多数導入:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リクエスト前・リダイレクト時にスキームチェック（http/https のみ）・プライベート IP/ループバック/リンクローカル判定を実施。専用の RedirectHandler (_SSRFBlockRedirectHandler) を使用。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 不正スキームや大容量レスポンスはログを残して安全にスキップ。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_* 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート等を行う _normalize_url。
    - 正規化 URL から SHA-256（先頭32文字）の記事 ID を生成する _make_article_id。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース（UTC に正規化）。
  - DB 保存処理:
    - save_raw_news はチャンク挿入（INSERT ... RETURNING id）で新規挿入 ID を返す。トランザクションでまとめて実行し、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk による記事と銘柄の紐付けを一括挿入（ON CONFLICT で重複スキップ）。
  - 銘柄抽出ロジック（extract_stock_codes）を実装（4桁数字を検出し known_codes によるフィルタリング、重複除去）。
  - run_news_collection で複数 RSS ソースを順次取得・保存し、既知コードに基づく紐付けを行う。デフォルトに Yahoo Finance のビジネス RSS を追加（DEFAULT_RSS_SOURCES）。

- リサーチモジュール (kabusys.research)
  - 特徴量探索・ファクター計算を提供するモジュール群を追加。
  - feature_exploration:
    - calc_forward_returns: DuckDB の prices_daily を使い複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損や非有限値の除外、十分なデータがなければ None を返す。
    - rank: 同順位の平均ランクを採るランク関数（丸め誤差対策に round を適用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - これらは標準ライブラリのみで実装（pandas 等に依存しない設計）。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m と 200日移動平均乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播を意識した実装。
    - calc_value: raw_financials から最新の財務（target_date 以前）を取得して PER（EPS ベース）、ROE を計算。prices_daily と結合して返す。
    - 各関数は DuckDB 接続と prices_daily / raw_financials テーブルのみを参照し外部 API には依存しない。
  - kabusys.research.__init__ では主要ユーティリティ／関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL を実装し、Raw / Processed / Feature / Execution 層を想定したテーブル定義を追加（raw_prices, raw_financials, raw_news, market_calendar, raw_executions 等のスキーマ定義を含む、存在チェック付きで CREATE TABLE IF NOT EXISTS を利用）。
  - スキーマの詳細な制約（NOT NULL / PRIMARY KEY / CHECK 等）を定義。

Security
- ニュース収集で SSRF 対策、XML パースの安全化（defusedxml）、受信サイズの上限、gzip 解凍後のサイズ検査を実装。
- J-Quants クライアントでトークン自動リフレッシュの制御と再試行制御を実装し、不正な再帰や無制限 retry を回避。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Removed
- （初回リリースのため履歴なし）

Notes / Usage hints
- 環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）が未設定の場合、Settings のプロパティアクセスで ValueError が発生します。.env.example を参考に .env を用意してください。
- 自動 .env ロードをテストや特殊ケースで抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector.fetch_rss は不正なレスポンスやサイズ超過時に安全に空リストを返しますが、ネットワークエラーは呼び出し側へ伝播します（run_news_collection は個々のソースごとにエラーハンドリングを行い次のソースへ継続します）。
- research モジュールの一部関数は外部ライブラリに依存せず標準ライブラリで実装されていますが、DuckDB (duckdb パッケージ) と defusedxml は実行環境に必要です。

今後の改善候補（参考）
- 要求されるスキーマの初期化ユーティリティ（create_all_tables 等）の提供。
- テストカバレッジ向上（各ネットワーク呼び出し・DBトランザクションのユニットテスト／統合テスト）。
- ニュース本文の言語処理（形態素解析等）や高度なノイズ除去。
- research モジュールに並列化・ベクトル化による高速化オプション（大量銘柄の一括処理向け）。

----------