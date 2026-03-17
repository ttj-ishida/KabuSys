CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。主にパッケージの初期リリース向けの変更点をコードベースから推測して記載しています。

フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（次回以降の変更をここに記載）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - public API エクスポート: data, strategy, execution, monitoring（strategy と execution は初期は空パッケージ）
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル / 環境変数の自動読み込みを実装（プロジェクトルートを .git または pyproject.toml で判定）
  - 自動ロード無効フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でスキップ可能
  - .env のパース実装:
    - 空行・コメント行対応、export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープを考慮した解析
    - インラインコメントの扱い（クォートあり/なしでの差異）
  - OS 環境変数の上書きを防ぐ protected 機能を実装し、.env.local は上書き優先で読み込む
  - Settings クラスを提供（主要プロパティ）:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別検証: KABUSYS_ENV ∈ {development, paper_trading, live}
    - ログレベル検証: LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}
    - ヘルパ: is_live/is_paper/is_dev
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース機能:
    - レート制御: 固定間隔スロットリング（120 req/min を守る _RateLimiter）
    - リトライ戦略: 指数バックオフ、最大リトライ回数 3、HTTP 408/429 と 5xx を再試行対象
    - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）とリトライ
    - ページネーション対応（pagination_key）
    - JSON デコードエラーのハンドリング
    - fetched_at を UTC ISO8601 で付与して Look-ahead Bias を防止
  - データ取得 API:
    - fetch_daily_quotes: 日次株価（OHLCV）をページネーションで取得
    - fetch_financial_statements: 四半期財務データのページネーション取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB に対する保存（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供
    - 各関数は ON CONFLICT DO UPDATE による冪等保存を行う
    - PK 欠損行はスキップしてログ出力
  - 型変換ユーティリティ: _to_float, _to_int（"1.0" などのケースに配慮）
  - モジュールレベルの ID トークンキャッシュ実装（ページネーション間で共有可能）
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集処理:
    - fetch_rss: RSS を安全に取得して記事リストを返す
      - defusedxml による XML パース（XML Bomb 等の防御）
      - HTTP/HTTPS スキーム検証（mailto:, file: 等は拒否）
      - リダイレクト検査による SSRF 防御（_SSRFBlockRedirectHandler）
      - ホストがプライベート/ループバック/リンクローカルかを検査してブロック
      - コンテンツ長チェックと実際の読み込みでの上限（MAX_RESPONSE_BYTES = 10MB）検査（Gzip 対応）
      - コンテンツ解凍後のサイズ検査（Gzip bomb 対策）
      - content:encoded 優先の本文取得、pubDate のパース（UTC で正規化、失敗時は現在時刻で代替）
      - URL 正規化: トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除
      - 記事ID: 正規化 URL の SHA-256 の先頭32文字で生成して冪等性を担保
      - テキスト前処理: URL 除去、空白正規化
    - save_raw_news: DuckDB に対するチャンク挿入（INSERT ... RETURNING id）を実装。トランザクションで一括コミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING + RETURNING で正確にカウントして保存
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出し、known_codes でフィルタ。重複除去。
    - run_news_collection: 複数 RSS ソースを横断して収集・保存・銘柄紐付けを行う。各ソースは独立してエラーハンドリング（1 ソース失敗でも他は継続）
  - セキュリティ/堅牢化:
    - SSRF 対策（スキーム検証・プライベートホストチェック・リダイレクト事前検査）
    - defusedxml による XML パース
    - レスポンスサイズ上限・Gzip 解凍後サイズ検査
    - 受信サイズ制限によりメモリDoSを軽減
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 4 層に対応したテーブル定義を含む DDL を実装
    - 例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など
  - チェック制約や外部キーを多用してデータ整合性を強化
  - 運用に応じたインデックス定義を提供（頻出クエリ向け）
  - init_schema(db_path) でディレクトリ作成を含む初期化を行い、冪等でテーブル/インデックスを作成
  - get_connection(db_path) による既存 DB への接続を提供（初期化は行わない）
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新 / バックフィル戦略を実装
    - _MIN_DATA_DATE = 2017-01-01（初回ロードの下限）
    - カレンダー先読み日数 _CALENDAR_LOOKAHEAD_DAYS = 90
    - デフォルトバックフィル日数 _DEFAULT_BACKFILL_DAYS = 3
  - ETLResult dataclass を導入（取得/保存数、品質問題、エラー等を集約）
  - ヘルパ関数:
    - _table_exists, _get_max_date: テーブル存在・最大日付判定
    - _adjust_to_trading_day: 非営業日調整（market_calendar がない場合はフォールバック）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl:
    - 差分算出（last date と backfill_days に基づく date_from の自動算出）
    - jq.fetch_daily_quotes → jq.save_daily_quotes を経て取得・保存を実行
    - （実装の意図は (fetched, saved) を返却）

Security
- SSRF 対策を複数箇所で実装:
  - URL スキーム検証（http/https のみ）
  - ホストのプライベートアドレス判定（直接 IP と DNS 解決の両方）
  - リダイレクト先の検査（_SSRFBlockRedirectHandler）
- XML パースに defusedxml を使用して XML 攻撃を軽減
- レスポンスの最大読み込みサイズ（10 MB）と解凍後サイズチェックでメモリ攻撃を軽減

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Migration
- 初期セットアップ:
  - 必須環境変数を .env に設定してください（例 .env.example を参照）。
  - DuckDB の初期化は data/schema.init_schema(db_path) を呼び出してください。デフォルト DB パスは data/kabusys.duckdb。
- テスト支援:
  - news_collector._urlopen はテストでモック可能（SSRF ハンドラを差し替えやすい設計）。
  - jquants_client のトークン取得は _get_cached_token(force_refresh=True) により制御可能。
- ログ:
  - 各主要処理は logger を出力します。LOG_LEVEL で制御可能。

Known issues / TODO
- run_prices_etl の戻り値に関する実装不整合:
  - 現在の実装（提供されたコードの末尾）では最後の return 文が "return len(records), " のように単一要素のタプルないし想定と異なる形になっており、呼び出し側が期待する (fetched_count, saved_count) のタプルと不一致になる可能性があります。実行時に正しい2要素のタプルを返すよう修正が必要です。
- strategy, execution, monitoring パッケージは初期は空実装（拡張予定）
- 品質チェック（quality モジュール）との統合は ETL の設計に含まれているが、quality モジュール本体は今回のコードセットに未掲載のため、統合テストが必要

貢献・報告
- バグ報告・改善提案は issue を立ててください。セキュリティ上の問題は公開リポジトリの issue ではなく、プライベートチャネルで報告してください。

--- 

（この CHANGELOG はコードベースを読んで推測に基づき作成しています。実行時の挙動や未公開のモジュールにより差異が発生する場合があります。）