CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog 準拠です。
リリース日はコードベースの現時点（ファイル内の __version__ に準拠）から推測して記載しています。

Unreleased
----------

- 今後の変更予定はここに記載します。

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの骨格を実装。
  - パッケージエントリポイント (kabusys.__init__) を追加。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（__file__ ベースで探索するため CWD に依存しない）。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 独自の .env パーサ実装:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - .env の上書き制御（override）と OS 環境変数保護（protected set）をサポート。
  - Settings クラスを提供し、以下等の必須/既定設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV の妥当性チェック (development / paper_trading / live)
    - LOG_LEVEL の妥当性チェック (DEBUG/INFO/...)
    - is_live / is_paper / is_dev の簡易判定プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能:
    - 日次株価（OHLCV）、財務諸表（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - 考慮点 / 実装:
    - API レート制限 (120 req/min) を守る固定間隔スロットリング（内部 RateLimiter）。
    - リトライ戦略: 指数バックオフ (最大 3 回)、408/429/5xx を再試行対象に。
    - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動再取得して一度だけリトライ。
    - id_token のモジュールレベルキャッシュを保持してページネーション間で共有。
    - JSON デコードエラー時の詳細エラーメッセージ。
    - データ取得時に fetched_at を UTC で記録して Look‑ahead bias を抑制する設計思想。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 冪等性確保のため INSERT ... ON CONFLICT DO UPDATE を使用（重複を排除して最新値で更新）。
    - PK 欠損行はスキップしログ出力。
  - ユーティリティ:
    - 型変換ユーティリティ (_to_float, _to_int) を提供し不正な入力に耐性あり。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集して raw_news に保存する一連処理を実装。
  - セキュリティ / 堅牢性:
    - defusedxml を用いて XML Bomb 等の攻撃に対処。
    - SSRF 対策: HTTP リクエスト前のホスト検査、リダイレクトハンドラでスキームとプライベートアドレスの検査、http/https スキームのみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリDoSを防止。Gzip 解凍後も上限チェック。
  - データ処理:
    - URL 正規化 (_normalize_url) とトラッキングパラメータ除去 (utm_*, fbclid 等)。
    - 記事 ID は正規化 URL の SHA‑256（先頭32文字）で生成し冪等性を担保。
    - テキスト前処理（URL除去、空白正規化）。
    - pubDate の解析は RFC2822 形式に対応し、失敗時は警告ログと現在時刻で代替。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、実際に挿入された記事IDの一覧を返す。チャンク分割して単一トランザクションで挿入。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING で安全に保存。チャンク/トランザクションを使用し挿入数を正確に返す。
  - 銘柄抽出:
    - テキスト中の 4 桁数字を候補にし、既知銘柄集合 (known_codes) でフィルタした上で重複除去して返す関数を実装。
  - 統合ジョブ:
    - run_news_collection により複数ソースを順次処理。各ソースは独立してエラーハンドリングし、1 ソース失敗でも他ソースは継続。戻り値はソースごとの新規保存件数。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル群定義を実装。
  - テーブル群:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）を設定してデータ整合性を強化。
  - インデックスを作成して典型的なクエリパターン（銘柄×日付、ステータス検索等）を最適化。
  - init_schema(db_path) により DB ファイル親ディレクトリを自動作成し、全DDLを冪等的に実行して接続を返す。
  - get_connection(db_path): スキーマ初期化を行わず既存 DB に接続するユーティリティ。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult データクラスを導入し ETL 実行結果、品質問題、エラーを集約可能に。
  - 差分更新のためのユーティリティ:
    - テーブル存在確認、最大日付取得 (_get_max_date, _table_exists)。
    - 市場カレンダーを参照して非営業日を直近営業日に調整するヘルパ (_adjust_to_trading_day)。
    - raw_prices/raw_financials/market_calendar の最終取得日を取得する関数群。
  - run_prices_etl:
    - 差分更新ロジックを実装。date_from 指定がない場合は DB の最終取得日から backfill_days（デフォルト 3）分を巻き戻して再取得することで API の後出し修正を吸収する設計。
    - J-Quants クライアントを用いた取得→保存（冪等）を行うフローを実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集で SSRF 対策を組み込み（スキーム検証、プライベートホスト検出、リダイレクト時の検査）。
- XML パーシングに defusedxml を使用して XML 関連攻撃を緩和。
- .env 読み込みで OS 環境変数を保護する仕組み（protected keys）。

Notes / Implementation choices
- J-Quants API のリトライでは 429 レスポンスの Retry-After ヘッダを優先し、存在しない場合は指数バックオフを使用。
- save_* 系関数は DuckDB の SQL を直接実行しており、ON CONFLICT による冪等制御と fetched_at の更新を行うことで後続の差分処理で最新情報に追随できるようにしている。
- ニュース記事IDは追跡用パラメータ削除 → 正規化 → SHA-256 の先頭32文字で決定しているため、トラッキングパラメータの違いによる重複挿入を抑制する設計。
- run_news_collection は known_codes を任意で与えることで銘柄抽出／紐付けを制御できる（提供しない場合は紐付けをスキップ）。

連絡先
- 不明点や追加機能の提案があればリポジトリの issue にて議論してください。