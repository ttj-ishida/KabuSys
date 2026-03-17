CHANGELOG.md
==============

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。
このプロジェクトはセマンティックバージョニングを使用します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-17
--------------------

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を提供します。

Added
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を設定。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に追加。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - ルート探索は __file__ を起点に .git または pyproject.toml を検出してプロジェクトルートを特定（CWD に依存しない挙動）。
  - .env と .env.local の読み込み優先順位を実装（OS 環境変数保護、.env.local が上書き）。
  - 行パーサはコメント、export プレフィックス、クォート有無、インラインコメント（スペースで区切られた #）等に対応。
  - 必須環境変数取得ヘルパ `_require()` と Settings クラスを導入。以下の主要設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (`development`, `paper_trading`, `live` の検証実装)
    - LOG_LEVEL（DEBUG/INFO/... の検証実装）
    - ヘルパプロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本設計:
    - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408, 429, 5xx。429 の場合は Retry-After を優先。
    - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動リフレッシュして1回だけ再試行（無限再帰防止の allow_refresh 管理）。
    - ページネーション対応（pagination_key）。
    - レスポンス JSON デコードエラーの明示的エラーメッセージ。
    - fetched_at を UTC ISO8601 で付与し「いつデータを知り得たか」をトレース可能に。
    - DuckDB への保存は冪等化（ON CONFLICT DO UPDATE）。
  - 提供 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - 型変換ユーティリティ: `_to_float`, `_to_int`（堅牢な空値/不正値処理）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し DuckDB の raw_news へ保存する ETL 機能。
  - 設計上の特徴:
    - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストの事前検証を行うカスタム RedirectHandler。
      - ホスト名→IP 解決時にプライベート/ループバック/リンクローカル/マルチキャストを拒否。
      - 初回アクセス前のホスト事前検証（SSRF 前置検証）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip 解凍後のサイズチェックあり（Gzip-bomb 対策）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_ 等）除去、フラグメント削除、クエリキーでソート。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化。
    - DB 保存:
      - save_raw_news(conn, articles) はチャンク（1000 件）で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDだけを返す。全てを 1 トランザクションでまとめる。
      - save_news_symbols / _save_news_symbols_bulk により (news_id, code) 紐付けをバルク挿入（ON CONFLICT DO NOTHING RETURNING 1）。
    - 銘柄抽出: 正規表現で 4 桁数字を候補とし、known_codes に含まれるもののみ返す（重複除去）。
    - fetch_rss 関数はエラーごとにロギングし、個別ソース失敗でも他ソースは継続する。

- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema.md に基づく3層スキーマを提供（Raw / Processed / Feature / Execution）。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - データ検証用 CHECK 制約や適切な PRIMARY KEY / FOREIGN KEY を定義。
  - 各種インデックス（頻繁クエリ向け）を作成。
  - 公開 API:
    - init_schema(db_path) -> duckdb connection（親ディレクトリ自動作成、冪等で DDL 実行）
    - get_connection(db_path) -> duckdb connection（既存 DB へ接続、スキーマ初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass により ETL の結果・品質問題・エラーを構造化。
  - 差分更新支援:
    - DB の最終取得日を確認するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 最小データ開始日を定義（_MIN_DATA_DATE = 2017-01-01）。
    - 市場カレンダー先読み用の lookahead 設定。
    - バックフィル仕様: デフォルト backfill_days = 3（最終取得日の数日前から再取得して API 後出し修正を吸収）。
    - run_prices_etl の骨子（差分計算、fetch_daily_quotes → save_daily_quotes 呼び出し、ログ出力）を実装（取得/保存数を返す）。
  - 品質チェック設計に関する記述（quality モジュールと連携して欠損・スパイク・重複等を検出する設計。品質問題は致命度を持ちつつ ETL 継続という方針）。

Security
- RSS パーサに defusedxml を利用。SSRF、Gzip/XML-bomb、悪意あるスキームへの対処など複数のセキュリティ対策を導入。
- .env 読み込みは OS 環境変数を保護（protected set）し、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。

Documentation / Usability
- settings の各プロパティに検証ロジックを実装し、誤った値は ValueError で明確に通知。
- モジュール内部でテスト時に差し替え可能なポイントを残す（例: news_collector._urlopen をモック可能）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Notes / Known limitations
- strategy, execution, monitoring パッケージは __init__ が存在するが実装は未提供（拡張ポイント）。
- pipeline.run_prices_etl はファイル中で末尾が切れている（コードベースの一部抜粋のため、実装の続きがある想定）。完全な ETL フローは quality モジュールや他の run_* 関数と連携する想定。
- テストカバレッジおよびエンドツーエンド検証は別途実施が必要。

Contributors
- コードベースからは個別の名前情報が取得できないため記載省略。

注: この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・PR・リリースノート原稿を参照して補完してください。