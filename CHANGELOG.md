# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-17
### Added
- パッケージ初期リリース: kabusys - 日本株自動売買システムの骨組みを追加。
  - public API: kabusys.__init__ により data, strategy, execution, monitoring モジュールを公開。
  - バージョン: 0.1.0

- 環境設定モジュール (kabusys.config)
  - .env / .env.local を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - パッケージ配布後でも動作するように、__file__ を起点にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env を探す。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で利用）。
  - .env パーサーの実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理。
    - クォートなし値のインラインコメント扱いは直前が空白/タブの場合にのみ認識。
    - 無効行（空行、コメント、キーなし等）はスキップ。
  - 上書き制御:
    - _load_env_file に override と protected 引数を用意し、OS環境変数を保護した上で .env.local による上書きを実現。
  - Settings クラス: 環境変数から設定値を取得するプロパティを提供。
    - J-Quants: jquants_refresh_token (必須)
    - kabuステーション API: kabu_api_password、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token、slack_channel_id（いずれも必須）
    - DBパス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - システム設定: env (development/paper_trading/live の検証)、log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の補助プロパティ
  - 必須環境変数未設定時は ValueError を投げて早期検出。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API 利用:
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダー を取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証:
    - リフレッシュトークンから id_token を取得する get_id_token。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で使い回す実装。
    - 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - レート制御・リトライ:
    - 固定間隔スロットリングで 120 req/min を守る RateLimiter を実装。
    - ネットワーク/サーバエラー（408/429/5xx 等）に対する指数バックオフ付きリトライ（最大 3 回）。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
    - ネットワークエラー（URLError/OSError）に対するリトライ。
  - DuckDB 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - ON CONFLICT DO UPDATE による冪等保存（重複/再取り込みに安全）。
    - fetched_at を UTC (Z) 形式で記録し、データ取得時刻のトレーサビリティを確保（Look-ahead Bias 対策）。
    - PK 欠損行はスキップして警告ログを出力。
  - ユーティリティ関数:
    - _to_float / _to_int: 安全な数値変換（空値・不正値は None、"1.0" のような float 文字列を int に変換する際の切捨て検出等）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と raw_news 保存の実装。
    - デフォルトソース: Yahoo Finance のビジネスカテゴリ RSS。
    - fetch_rss: RSS を取得・パースして NewsArticle リストを返す。
      - defusedxml を使用して XML Bomb 等を防御。
      - gzip 圧縮レスポンスの処理と解凍後サイズチェック（Gzip bomb 対策）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリDoS を防止。
      - 最終 URL に対してもスキーム検証とプライベートホスト検証を実施（SSRF 対策）。
      - リダイレクト時にスキーム/ホスト検査を行うカスタム RedirectHandler を使用。
      - <link> がない場合は guid を代替 URL として利用（http/https のみ）。
      - content:encoded を優先して本文を取得。
      - pubDate を RFC 2822 形式としてパースし UTC に正規化。パース失敗時は警告ログの上で現在時刻（UTC）を代替。
    - URL 正規化:
      - _normalize_url でスキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid 等）除去、フラグメント除去、クエリパラメータソートを実施。
      - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を担保。
    - テキスト前処理:
      - URL 除去、連続空白を単一スペース化、トリム。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID を返す（チャンク分割、1 トランザクション内で実行）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク/トランザクションで保存し、INSERT ... RETURNING により挿入数を正確に返却。
    - 銘柄コード抽出:
      - 4桁数字パターンを用いてテキストから候補を抽出し、known_codes セットに基づいて有効性を判定、重複除去して返す。
    - run_news_collection:
      - 複数 RSS ソースをループして収集。各ソースは独立してエラーハンドリングし、1 ソースの失敗が他を停止させない設計。
      - 新規記事のみを対象に銘柄紐付けを一括保存するオプション（known_codes を指定）。

- DuckDB スキーマ・初期化モジュール (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル定義を追加。
    - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
    - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature テーブル: features, ai_scores
    - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な PRIMARY KEY、CHECK 制約、外部キー（必要箇所）を定義。
  - 頻出クエリに対応するインデックス群を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を実装:
    - :memory: 対応。
    - parent ディレクトリ自動作成。
    - 既存テーブルがあればスキップする冪等作成。
  - get_connection(db_path): 既存 DB への接続を返すユーティリティ。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の方針と差分更新ロジックを実装。
    - ETLResult dataclass で実行結果、品質問題、エラー等を構造化して返却。
    - 差分更新ヘルパー: テーブルの最終取得日を確認するための get_last_* 関数群。
    - 市場カレンダー参照による営業日調整 helper (_adjust_to_trading_day) を実装（未取得時はフォールバック）。
    - run_prices_etl を実装（差分取得、backfill_days による後出し修正吸収、取得→保存の流れ）。  
      - J-Quants の差分取得は date_from を自動算出し、ページネーション対応 fetch を利用してデータ取得後に save_daily_quotes にて冪等保存。
    - 品質チェックのフック（quality モジュール）と重大度ハンドリングを想定（品質エラーがあっても ETL を継続する設計）。

### Security
- ニュース収集における SSRF 対策:
  - URL スキーム検証 (http/https のみ)、リダイレクト先のスキーム/ホスト検査、ホストがプライベートアドレスかを判定して内部ネットワークアクセスを阻止。
  - defusedxml の採用により XML ベースの攻撃（XML Bomb 等）を軽減。
  - レスポンスサイズ上限の導入と gzip 解凍後のサイズチェックによりメモリ DoS を軽減。
- J-Quants クライアント:
  - 認証トークンの安全な取り扱いと自動リフレッシュ、無限再帰防止ロジックを実装。

### Notes / Limitations
- jquants_client の _request による HTTP 実行は urllib を直接利用しており、細かな HTTP クライアント制御（コネクションプール等）は行っていない。
- pipeline.run_prices_etl の実装は差分取得・保存の主要ロジックを備えるが、quality モジュールの具体的なチェック実装は外部に委ねられる設計（quality モジュールが別実装）。
- RSS フィードのソースは DEFAULT_RSS_SOURCES で初期化されるが、run_news_collection 呼び出し時に sources を注入可能。

---

（この CHANGELOG はコードベースからの仕様・実装内容を推測して作成しています。実際の運用や追加の変更がある場合は適宜更新してください。）