# Keep a Changelog
すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

全般:
- リリースバージョンはパッケージ内の __version__ に合わせて v0.1.0 としています。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期実装を追加。モジュール構成:
  - kabusys (パッケージルート)
    - data (データ取得・保存・ETL)
    - strategy (戦略用プレースホルダ)
    - execution (実行/発注用プレースホルダ)
    - monitoring (モニタリング用プレースホルダ、まだ未実装)
- 環境設定管理モジュール (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を読み込む仕組みを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に探索するため、CWDに依存しない自動読み込みが可能。
  - 自動読み込みの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパースは以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート内のエスケープ文字処理
    - インラインコメントの扱い（クォート無しの場合のスペース直前の `#` をコメントとみなす等）
  - settings オブジェクトを公開。必須環境変数取得用の `_require()` を実装。
  - 既定値・検証:
    - KABU_API_BASE_URL のデフォルト
    - DUCKDB_PATH / SQLITE_PATH のデフォルト
    - KABUSYS_ENV の有効値検査 (development / paper_trading / live)
    - LOG_LEVEL の有効値検査
  - 必須環境変数（呼び出し時に未設定だと例外）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足、財務データ、JPXマーケットカレンダーの取得関数を実装:
    - fetch_daily_quotes (ページネーション対応)
    - fetch_financial_statements (ページネーション対応)
    - fetch_market_calendar
  - 認証処理:
    - get_id_token(refresh_token=None) によりリフレッシュトークンから ID トークンを取得
    - モジュールレベルで id_token をキャッシュしページネーション間で共有
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ
  - レート制御、リトライ、エラーハンドリング:
    - レート制限 120 req/min を固定間隔スロットリングで遵守 (_RateLimiter)
    - 再試行ロジック（最大 3 回、指数バックオフ、408/429/5xx をリトライ対象）
    - 429 の場合は Retry-After ヘッダを優先
  - DuckDB への保存関数（冪等性を担保）:
    - save_daily_quotes: raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials へ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar へ INSERT ... ON CONFLICT DO UPDATE
  - データ変換ユーティリティ:
    - _to_float / _to_int（安全に None を返す等）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得と raw_news 保存機能を実装:
    - fetch_rss (RSS を取得して正規化済み記事リストを返す)
    - save_raw_news (DuckDB の raw_news テーブルへバルク挿入、INSERT ... RETURNING を使用)
    - save_news_symbols / _save_news_symbols_bulk (記事と銘柄コードの紐付けをバルク保存)
    - extract_stock_codes (テキストから 4 桁銘柄コードを抽出)
    - run_news_collection (複数ソースを巡回して収集・保存・紐付け)
  - セキュリティ・堅牢性対策:
    - defusedxml を利用して XML Bomb 等を防御
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - ホスト/IP がプライベート・ループバック・リンクローカル・マルチキャストであれば拒否
      - リダイレクト時に検査するカスタムハンドラ (_SSRFBlockRedirectHandler)
    - レスポンス上限: MAX_RESPONSE_BYTES = 10 MB を設定してメモリ DoS を防止
    - gzip 圧縮に対応し、解凍後もサイズ検証（Gzip bomb 対策）
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化、SHA-256 ハッシュ先頭 32 文字を記事 ID として採用（冪等性）
    - HTTP ヘッダで Accept-Encoding:gzip を要求し、User-Agent をセット
  - DB 保存戦略:
    - 挿入はチャンク化して 1 トランザクションでまとめる（パフォーマンスと整合性）
    - ON CONFLICT で重複をスキップし、実際に挿入された ID を RETURNING で収集
    - news_symbols の一括挿入もチャンク化して RETURNING で挿入数を計測
  - テストのしやすさ:
    - HTTP オープン処理を _urlopen でラップしておりモック可能

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - DataPlatform.md に基づく3層設計のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY、CHECK 等）を定義
  - よく使われるクエリ向けのインデックス群を定義
  - init_schema(db_path) によりディレクトリ作成（必要に応じ）→ DuckDB のテーブル・インデックスを冪等的に作成
  - get_connection(db_path) を提供（既存 DB への単純接続）

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL 実行結果を表す ETLResult データクラスを実装（品質問題・エラーの集約を含む）
  - 差分更新ヘルパー:
    - テーブル存在確認、最大日付取得ユーティリティ (_table_exists, _get_max_date)
    - market_calendar を参照した営業日補正 (_adjust_to_trading_day)
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl（株価差分 ETL）の骨組みを実装:
    - 最終取得日から backfill_days 分遡って再取得するロジック（デフォルト backfill_days=3）
    - J-Quants から差分取得して保存する流れ（fetch -> save）
    - ETL の品質チェック呼び出し箇所用のフック（quality モジュールを利用する設計）
  - 設計方針のドキュメント注記:
    - レンジ差分更新、品質チェックは Fail-Fast ではなく問題を集約して呼び出し元が判断する方式

- パッケージ初期化と公開 API
  - パッケージの __init__ にて __version__ を設定 (0.1.0) と __all__ を定義し主要サブパッケージを公開

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサーで defusedxml を使用し XML 攻撃を緩和。
- RSS フェッチ時に SSRF を検出してブロック（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
- .env 読み込みで OS 環境変数（protected set）を上書きしない安全な初期読み込みロジック。
- J-Quants API クライアントでトークンの自動リフレッシュと最小限のリトライ制御を実装。

### 既知の制限・TODO
- strategy と execution パッケージは初期プレースホルダで具体的な戦略や注文ロジックは未実装。
- pipeline.run_prices_etl 等の ETL ワークフローは基本ロジックを実装しているが、品質チェック (quality モジュール) の呼び出しや全体の管理機能は試験段階。運用にあたっては更なる検証が必要。
- monitoring 周りはまだ未実装・もしくは限定的。
- 一部関数のエッジケースやスレッドセーフティ（例: モジュールレベルのトークンキャッシュ）は想定された使用方法では問題ないが、極端な同時実行環境での検証が推奨される。

### 移行・導入手順（概要）
1. 必要環境変数を設定:
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
   - 必要に応じて KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等を設定
2. データベース初期化:
   - from kabusys.data.schema import init_schema
   - conn = init_schema(settings.duckdb_path) もしくは init_schema("data/kabusys.duckdb")
3. ETL 実行:
   - pipeline モジュールの run_prices_etl 等を呼び出してデータ取得・保存を行う
4. テスト時:
   - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - news_collector._urlopen をモックしてネットワークアクセスを制御可能

### 開発者向けメモ
- 単体テストを容易にするため、ネットワークアクセスや時間依存部分はモック可能な形で設計（例: _urlopen, _get_cached_token の引数注入）。
- DuckDB の SQL は実行時に文字列連結で実行している箇所があるため、将来的に ORM ライクなラッパー導入を検討してもよい。
- 大量データの INSERT はチャンク化しているが、実運用ではトランザクションサイズやパフォーマンス監視が必要。

---

（注）この CHANGELOG はソースコードの内容とドキュメント文字列から推測して作成した初回リリース記録です。運用や追加実装に応じて随時更新してください。