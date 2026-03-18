# Keep a Changelog
すべての注目すべき変更点を記載します。  
このファイルは Keep a Changelog の形式に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回リリース。日本株の自動売買/データ基盤ライブラリの基本機能を追加。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョン 0.1.0 を設定。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を追加し、CWD に依存しない読み込みを実現。
  - .env のパーサーを実装（export プレフィックス対応、引用符内のエスケープ、インラインコメント処理など）。
  - .env と .env.local の読み込み順序と override/protected キーの扱いを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト向け）。
  - Settings クラス（jquants/slack/DBパス/環境/ログレベル等）を提供し、必須変数のチェックと値検証（KABUSYS_ENV / LOG_LEVEL）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch 関数を追加（ページネーション対応）。
  - API レート制御（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、対象: 408/429/5xx）を実装。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。id_token のモジュールキャッシュ共有。
  - データの取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 対策を意識。
  - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を追加。ON CONFLICT DO UPDATE による冪等保存を実現。
  - 値変換ユーティリティ（_to_float、_to_int）を実装（空値・変換失敗は None、_to_int は "1.0" を許容し小数を検出）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得（fetch_rss）と前処理パイプラインを追加。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）および記事ID を SHA-256 の先頭32文字で生成（_make_article_id）。
  - セキュリティ対策：defusedxml を利用した XML パース、防止のための受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）、HTTP/HTTPS 以外のスキーム拒否。
  - SSRF 対策：リダイレクト時のスキーム/ホスト検査を行うカスタムハンドラ（_SSRFBlockRedirectHandler）、およびホストのプライベート/ループバック判定（_is_private_host）。
  - テキスト前処理（URL 除去、空白正規化）、RSS pubDate のパース（タイムゾーン考慮）を実装。
  - DuckDB への冪等保存（save_raw_news、save_news_symbols、_save_news_symbols_bulk）を実装。トランザクションでまとめ、INSERT ... RETURNING により実際に挿入された件数を返す。
  - 銘柄コード抽出ユーティリティ（extract_stock_codes、4桁数字パターン）を追加。
  - 統合収集ジョブ run_news_collection を実装（複数ソース処理、各ソース独立したエラーハンドリング、既知銘柄紐付け処理）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋Execution）に対応するテーブル群を定義：
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種チェック制約、主キー、外部キーを含めた DDL を実装。
  - 検索性を考慮したインデックスを定義（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) によりファイル作成（親ディレクトリ自動作成）→ テーブル作成 → インデックス作成を行う。get_connection も提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に基づく差分更新パイプラインの基礎を実装。
  - ETLResult dataclass を追加（取得件数、保存件数、品質問題、エラー等を集約）。
  - テーブル存在確認・最終日取得ユーティリティ（_table_exists、_get_max_date、get_last_price_date 等）を追加。
  - _adjust_to_trading_day による非営業日の調整ロジックを実装（market_calendar を参照して最大30日遡る）。
  - run_prices_etl（株価の差分ETL）を実装（差分取得ロジック、backfill_days による再取得、fetch→save の流れ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサーに defusedxml を使用して XML 関連の攻撃を緩和。
- RSS フェッチ時に SSRF 防止（スキーム検証、プライベートアドレスチェック、リダイレクト検査）を実装。
- レスポンスサイズおよび gzip 解凍後サイズチェックでメモリ DoS / Gzip bomb を緩和。
- J-Quants クライアントのネットワークエラー・HTTP リトライとトークン管理により異常時の誤動作を減らす。

### Notes / 開発上の留意点
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。配布後などで自動検出が不適切な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_prices_etl や他の ETL ジョブは差分取得・バックフィルの基本ロジックを備えていますが、運用でのスケジューリングや品質チェックの閾値等は別途調整が必要です。
- DuckDB のスキーマは冪等性を考慮しているため、既存 DB に対しても安全に init_schema を実行できます。
- news_collector の extract_stock_codes は known_codes に依存するため、使用時は既知銘柄リストを渡してください。

### Breaking Changes
- なし（初回リリース）

----------

このリリースでは、データ取得・保存・ETL・ニュース収集・環境設定の基盤的機能を提供します。今後は戦略実装（strategy）、発注実行（execution）、監視（monitoring）の具体的実装や品質チェックの追加、テスト拡充を予定しています。