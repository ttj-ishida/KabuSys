Keep a Changelogフォーマットに準拠した CHANGELOG.md を以下に作成しました。コード内容から実装されている機能・設計方針・重要な実装上の注意点を推測して記載しています。

CHANGELOG.md
=============
所有するバージョンはパッケージの __version__ に合わせて 0.1.0 としています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージのトップレベルモジュールを定義（kabusys）。
  - version: 0.1.0

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装。
    - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索してプロジェクトルートを特定。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され上書きされない。
  - .env ファイルの堅牢なパーサを実装。
    - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、無効行のスキップ。
  - Settings クラスを提供（プロパティ経由で安全に設定取得）。
    - J-Quants / kabu API / Slack / DB 路径 / システム設定をカプセル化。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（限定された値セット）。
    - is_live / is_paper / is_dev の補助プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本設計:
    - レート制限（120 req/min）を遵守する固定間隔スロットリング _RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大3回）を実装。ステータス 408/429/5xx を対象に再試行。
    - 401 Unauthorized を受けた場合はリフレッシュトークンで id_token を自動リフレッシュして1回リトライ。
    - ページネーション対応（pagination_key を追跡）。
    - API レスポンスの JSON デコード失敗・ネットワーク異常に対する適切なエラー処理。
  - API 呼び出しユーティリティ _request を提供。
  - 認証ユーティリティ get_id_token（リフレッシュトークン→idToken）を提供。
  - データ取得関数:
    - fetch_daily_quotes (OHLCV 日足、ページネーション対応)
    - fetch_financial_statements (四半期 BS/PL、ページネーション対応)
    - fetch_market_calendar (JPX 市場カレンダー)
  - DuckDB に対する保存関数（冪等性を担保）:
    - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE で保存、fetched_at を UTC ISO 形式で記録。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE。HolidayDivision を解釈して取引日/半日/SQ を判定。
  - ユーティリティ関数 _to_float / _to_int を提供（安全な型変換。int 変換時に小数部が存在する場合は None を返す等の保護ロジック）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュースを収集して raw_news / news_symbols に保存する一連の処理を実装。
  - セキュリティ/堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等に対処）。
    - SSRF 対策: リダイレクト時のスキーム検証・内部アドレス判定を行う専用ハンドラ _SSRFBlockRedirectHandler と事前ホスト検証。
    - URL スキーム検証 (http/https のみ許可)。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Content-Length と実読込サイズをチェック。gzip 解凍後のサイズも再検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を指定して取得。
  - フィード解析と前処理:
    - URL 正規化 (_normalize_url): スキーム/ホストを小文字化、トラッキングパラメータ（utm_等）除去、フラグメント削除、クエリソート。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字を採用（冪等性確保）。
    - テキスト前処理 preprocess_text: URL 除去、空白正規化。
    - pubDate のパース（RFC2822 を UTC に正規化）。失敗時は warning を出して現在時刻で代替。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのみ返却。チャンク分割して1トランザクションで挿入（挿入に失敗した場合はロールバック）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... ON CONFLICT DO NOTHING RETURNING で一括挿入し、挿入件数を正確に返す。重複除去/チャンク処理を行う。
  - 銘柄コード抽出:
    - extract_stock_codes: 正規表現で4桁数字を抽出し、known_codes に存在するものだけを返す（重複除去、順序維持）。

- DuckDB スキーマ定義 & 初期化（kabusys.data.schema）
  - DataPlatform 構成に基づくスキーマ実装（Raw / Processed / Feature / Execution レイヤ）。
  - テーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに制約（NOT NULL, PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - インデックスを多数定義（code/date のスキャンやステータス検索等を高速化）。
  - init_schema(db_path) を提供: ディレクトリを自動作成し、DDL をすべて実行して接続を返す（冪等）。
  - get_connection(db_path) を提供: 既存 DB へ接続（初回は init_schema を推奨）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の設計方針に沿ったユーティリティとジョブを実装:
    - ETLResult dataclass: ETL 実行結果（取得数、保存数、品質問題、エラー一覧）を保持。品質問題は辞書化可能。
    - テーブル存在チェック / 最大日付取得ユーティリティ (_table_exists / _get_max_date)。
    - 市場カレンダー補助: _adjust_to_trading_day（非営業日を直前の営業日に調整）。
    - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 個別 ETL ジョブ run_prices_etl（差分取得・backfill ロジックあり）。
      - 差分処理: 最終取得日から backfill_days 分遡って再取得することで API の後出し修正を吸収。
      - 最小データ開始日 _MIN_DATA_DATE を定義（2017-01-01）。
      - 市場カレンダーの先読み日数設定 _CALENDAR_LOOKAHEAD_DAYS。

- パッケージ構成の雛形
  - strategy/ と execution/ モジュールを作成（現時点ではパッケージ初期化用に空の __init__.py を配置）。以降の戦略・実行ロジック実装のための足場を用意。

Security
- RSS 収集における SSRF 対策、XML パースの安全化、レスポンスサイズ制限、外部からの不正 URL スキーム拒否などを実装。外部コンテンツ取り扱いのセキュリティに留意。

Performance
- API レート制御（固定間隔スロットリング）とリトライバックオフにより安定した取得を実現。
- DuckDB へのバルク挿入（チャンク処理）と INSERT ... RETURNING による効率的な挿入判定。
- スキーマに適切なインデックスを追加してクエリ性能を向上。

Notes
- run_prices_etl の戻り値の最後の return がソースの途中で終わっているように見える（コードスニペット終端による断片）。実装を継続する必要があるかもしれません（ただし主要な差分ロジックは含まれている）。
- execution/strategy モジュールは現時点で雛形のみのため、発注ロジックや戦略の具現化は今後の実装対象。

Deprecated
- なし

Removed
- なし

Fixed
- なし

今後の提案（補助）
- run_prices_etl 等の ETL ジョブの単体テストと、外部 API 依存部分のモック化パターンを整備することを推奨。
- news_collector の DNS 依存テストを安定化するための抽象化（_urlopen の差し替えを利用）や、既知銘柄リストの定期更新フローの確立を検討してください。
- 運用時は KABUSYS_DISABLE_AUTO_ENV_LOAD と .env の取り扱いポリシーを明確にし、機密情報の管理に注意してください。

以上が、このコードベースから推測して作成した CHANGELOG.md の内容です。変更項目の文言や日付をプロジェクト実情に合わせて修正することを推奨します。必要であれば英語版や、より細かなコミット単位の履歴に分解したバージョンも作成できます。