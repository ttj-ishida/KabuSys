# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース: [0.1.0] - 2026-03-17

---

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を実装しました。主要な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート探索ロジックを導入（.git または pyproject.toml を基準）。
  - .env 自動ロード機能（OS 環境 > .env.local > .env、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート有無での扱い差分）
  - 環境変数取得ユーティリティ `_require` と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、実行環境判定などのプロパティを備える）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の有効値チェック。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ `_request` を実装（JSON デコード、タイムアウト、エラーハンドリング）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行/バックオフ: 指数バックオフ、最大 3 回リトライ。対象ステータス（408, 429, 5xx）に対応。429 の場合は Retry-After ヘッダを尊重。
  - 認証トークン: リフレッシュトークンから ID トークンを取得する `get_id_token`、モジュールレベルのトークンキャッシュと自動リフレッシュ処理（401 で 1 回のみリフレッシュして再試行）を実装。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等保存を目指す実装）:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を用いて重複を更新）
  - 値変換ユーティリティ `_to_float`, `_to_int` を実装（空値・不正値対策、"1.0" からの int 変換時の安全性確保）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集から DuckDB への永続化までのワークフロー実装。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - HTTP/HTTPS スキーム以外を拒否し SSRF を防止。
    - リダイレクト時にスキームとホスト/IP を検査する専用ハンドラ（_SSRFBlockRedirectHandler）。
    - ホストのプライベート/ループバック/リンクローカル判定（IP 直接解析 + DNS 解決の全 A/AAAA レコードを検査）。DNS 解決失敗時は安全側の扱い。
    - レスポンス受信上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を緩和。gzip 解凍後も上限検査。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去してクエリをソート、フラグメント削除などを行う `_normalize_url` 実装。
    - 記事IDは正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性保証）。
  - テキスト前処理 `preprocess_text`（URL 除去、空白正規化）。
  - RSS 抽出ロジック（content:encoded 優先、guid の代替使用、pubDate パース）。
  - DB 保存:
    - save_raw_news（チャンク分割、トランザクション、INSERT ... RETURNING で実際に挿入された ID を返す）
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄コードの紐付けを一括保存、重複排除、トランザクション）
  - 銘柄コード抽出 `extract_stock_codes`（4桁数字の候補から known_codes に存在するもののみを返す）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ定義と初期化関数 `init_schema` を提供。
  - 3 層（Raw / Processed / Feature）＋Execution 層に相当するテーブル群を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）や型を設定。
  - よく使うクエリ向けのインデックスを作成（コード×日付、ステータス検索など）。
  - `get_connection` による既存 DB 接続取得 API を提供。
  - init_schema は親ディレクトリ自動作成や ":memory:" サポートを含む冪等な初期化を行う。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針に基づくパイプライン基盤を実装。
  - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラーの集約）。品質問題は辞書化して出力可能。
  - 差分更新のためのヘルパー:
    - テーブル存在チェック `_table_exists`
    - 最大日付取得 `_get_max_date`
    - 市場カレンダーを用いた営業日調整 `_adjust_to_trading_day`
    - last date を返す get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl の雛形を実装（差分取得ロジック、backfill_days による再取得、J-Quants からの取得→保存フロー）。（注: ファイル末尾は続きが想定されるが、差分ETL の主要ロジックと設計は含まれる）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに対して defusedxml を採用し、XML 関連の脆弱性緩和を実施。
- RSS フィード取得時に SSRF 緩和対策を多数導入（スキーム検証、プライベートアドレス判定、リダイレクト時の検査）。
- .env 読み込みは OS 環境変数を保護する仕組み（protected set）を実装し、意図しない上書きを防止。

### 既知の制限 / 注意点 (Known issues / Notes)
- jquants_client の _request は urllib を直接利用しており、SSL や接続設定の細かい調整が今後必要になる可能性があります。
- pipeline.run_prices_etl のファイル末尾は続き（戻り値などの詳細）を想定しており、将来的な拡張や品質チェック（quality モジュールとの連携）が必要です。
- news_collector の DNS 解決失敗時の振る舞いは「非プライベート」と見なす方針であり、環境によっては別途制御が必要になる場合があります。
- デフォルト RSS ソースは最小構成（yahoo_finance）。追加ソースは run_news_collection の引数で渡して利用可能。

---

今後の予定（例）
- pipeline の各 ETL ジョブ（財務、カレンダー、ニュース）を完全実装・結合し、品質チェック（quality モジュール）との統合を強化。
- execution / strategy / monitoring パッケージの実装とエンドツーエンドテストの追加。
- テスト用モックや CI ワークフローの整備（外部 API 依存のテストを安定化）。

---

作者: KabuSys チーム
（このCHANGELOGはコードベースから推測して自動生成されています。実際のリリースノートとして利用する際は必要に応じて調整してください。）