CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。
リリース日付は本リポジトリの現在の状態（初版リリース）に基づき記載しています。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-18
-------------------

Added
-----
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: KabuSys
  - バージョン: 0.1.0
  - パッケージ公開モジュール: data, strategy, execution, monitoring（パッケージ構成をエクスポート）

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: __file__ を基準に .git または pyproject.toml を探索してルートを特定
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ: コメント・export 形式・クォート文字列・インラインコメント等に対応する堅牢なパーサを実装
  - Settings クラスを提供し、以下の必須/オプション設定をプロパティで取得可能
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本設計
    - API レート制限（120 req/min）を守る固定間隔スロットリングの RateLimiter 実装
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）と再試行
    - モジュールレベルで ID トークンをキャッシュしページネーション間で共有
    - レスポンス取得時の JSON デコードチェック、エラーメッセージの整備
    - データ取得時に fetched_at を UTC タイムスタンプ形式で記録（Look-ahead Bias 対策）
    - DuckDB への保存は冪等性を保つ（ON CONFLICT DO UPDATE）
  - 公開 API
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(id_token, code, date_from, date_to) -> list[dict]
    - fetch_financial_statements(id_token, code, date_from, date_to) -> list[dict]
    - fetch_market_calendar(id_token, holiday_division) -> list[dict]
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集・前処理・DB 保存フローを実装
  - セキュリティと堅牢性
    - defusedxml を用いた XML パース（XML Bomb 等対策）
    - SSRF 対策: URL スキーム検証、ホストがプライベートアドレスかの検査、リダイレクト検査用カスタムハンドラ
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip Bomb 対策）
    - 受け入れスキームは http/https のみ
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化
  - データ処理
    - URL 正規化と記事 ID は正規化後の SHA-256 ハッシュ先頭32文字で生成（冪等性確保）
    - テキスト前処理（URL 除去、空白正規化）
    - RSS の pubDate を UTC に変換（パース失敗時は現在時刻で代替）
    - extract_stock_codes(text, known_codes) で 4 桁銘柄コードを抽出（重複除去）
  - DB との連携
    - save_raw_news(conn, articles) -> list[str]
      - INSERT ... RETURNING を使い、実際に挿入された記事 ID リストを返す
      - バルクチャンク挿入、トランザクション管理（コミット/ロールバック）
    - save_news_symbols(conn, news_id, codes) -> int
    - _save_news_symbols_bulk(conn, pairs) -> int
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[source_name, saved_count]

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md に基づく初期スキーマ定義を実装（Raw / Processed / Feature / Execution 層）
  - 主なテーブル（抜粋）
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約・PRIMARY KEY を設定
  - 頻出クエリ向けにインデックスを作成する DDL を準備
  - init_schema(db_path) -> DuckDB 接続を提供（ファイルパスの親ディレクトリ自動作成、冪等的にテーブル/インデックス作成）
  - get_connection(db_path) -> 既存 DB への接続（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 設計方針に沿った差分取得・保存・品質検査の骨格を実装
  - ETLResult データクラスで実行結果（取得数、保存数、品質問題、エラー）を集約
  - 差分更新ユーティリティ
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day で非営業日は直近の営業日に調整（market_calendar 使用）
  - run_prices_etl(...) の骨組みを実装
    - 差分算出: DB の最終取得日から backfill_days 前を date_from として再取得
    - デフォルト backfill_days は 3 日
    - J-Quants から取得して jq.save_daily_quotes で保存

- その他
  - data パッケージ内で各モジュールを分割して実装（jquants_client, news_collector, schema, pipeline, …）
  - strategy, execution, monitoring パッケージのプレースホルダ __init__ を追加（実装可能なモジュール構造を確立）

Security
--------
- RSS パーサで defusedxml を使用し XML 攻撃を緩和
- ニュースフェッチにおいて SSRF 対策（スキーム検証、プライベートホスト検査、リダイレクト検査）を実施
- レスポンス受信時に最大バイト数チェックを行いメモリ DoS を防止
- .env 読み込み時に protected set（既存 OS 環境変数）を考慮して上書きを制御可能

Known issues / Notes
--------------------
- run_prices_etl の戻り値に関する不整合:
  - 現状ソース中で最後に "return len(records)," のようにコンマ付きで返しており、宣言された戻り値型 (tuple[int, int]) と合致しない（単一要素の tuple を返す / あるいは構文が途中で切れている可能性）。ETL の呼び出し側で期待される (fetched_count, saved_count) の形に合わせる修正が必要です。
- pipeline モジュールは品質チェック（quality モジュール）との連携を想定しているが、quality モジュールの具体的実装は本差分からは確認できないため、実行時に外部実装が必要。
- strategy / execution / monitoring パッケージはパッケージ構成が用意されているが、各機能の実装は本リリースでは最小または未提供の可能性がある（プレースホルダ）。

Upgrade / Migration Notes
-------------------------
- 初回セットアップ:
  - DuckDB スキーマを作成するには:
    - from kabusys.data.schema import init_schema
    - conn = init_schema(settings.duckdb_path)
  - 必須環境変数を .env または環境に設定してください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- テスト・CI で自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ニュース収集で銘柄紐付けを行うには known_codes のセット（有効な 4 桁銘柄コードの集合）を run_news_collection に渡してください。

Breaking Changes
----------------
- 初期リリースにつき該当なし。

Deprecated
----------
- なし。

Removed
-------
- なし。

Fixed
-----
- 初版リリースにつき過去の修正履歴なし。

Contributors
------------
- 初回実装コードに基づいて作成

もし追加でリリースノートの粒度（コミット単位、モジュール単位など）や英語版 CHANGELOG の出力が必要であれば指示してください。