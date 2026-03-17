# Changelog

すべての変更は Keep a Changelog の形式に従います。  
安定リリースやバージョン履歴を明確に保つため、重要な追加・変更・修正・既知の問題を記載します。

- ホームページ: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - src/kabusys/__init__.py にパッケージ情報を追加（__version__ = 0.1.0, __all__ に data, strategy, execution, monitoring を公開）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイル及び環境変数から設定を読み込む仕組みを実装。
    - プロジェクトルート探索: .git または pyproject.toml を基準に自動検出（CWD に依存しない実装）。
    - .env の堅牢なパーサ実装:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - コメント・インラインコメントの扱い（クォート有無での挙動差）
    - 自動ロード優先順位: OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス等のプロパティ）。入力値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
    - デフォルトの DB パス（DuckDB/SQLite）を設定可能。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API ベース実装（_BASE_URL = https://api.jquants.com/v1）。
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter 実装。
    - リトライロジック:
      - 最大試行回数 3 回、指数バックオフ（base=2.0 秒）。
      - HTTP 408/429 および 5xx 系をリトライ対象。
      - 429 の場合は Retry-After ヘッダを優先。
      - ネットワークエラー（URLError / OSError）もリトライ。
    - 認証:
      - get_id_token(refresh_token) による ID トークン取得（POST /token/auth_refresh）。
      - モジュールレベルの ID トークンキャッシュと、401 発生時の自動リフレッシュ（1 回のみリトライ）。
    - データ取得関数（ページネーション対応）:
      - fetch_daily_quotes（日足 OHLCV）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
      - 取得時に pagination_key を用いたページ繰り返しを実装。
    - DuckDB への保存関数（冪等・ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - 取得時刻 (fetched_at) を UTC 形式で保存し Look-ahead Bias を防止。
    - ユーティリティ: 型変換関数 _to_float / _to_int（失敗時は None を返す、安全な変換ロジック）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードからの記事収集と DuckDB への保存ロジックを実装。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb 等の防御）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルなら拒否、リダイレクト時も検査する _SSRFBlockRedirectHandler。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip 圧縮解凍後もサイズ検査。
    - URL 正規化:
      - トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga 等）を除去、クエリをソート、フラグメント除去して正規化。
      - 正規化 URL から SHA-256（先頭32文字）で記事IDを生成し冪等性を確保。
    - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
    - 銘柄抽出: 4桁数字パターンで候補抽出し known_codes に基づくフィルタ（extract_stock_codes）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に新規挿入された記事IDを返す。チャンク挿入（_INSERT_CHUNK_SIZE）とトランザクションで効率化。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをチャンクで保存、ON CONFLICT DO NOTHING と RETURNING で正確な新規件数を取得。
    - デフォルト RSS ソースに Yahoo Business を登録（yahoo_finance）。

- DuckDB スキーマ
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の 4 層データモデルを DDL で定義。
    - 主要テーブル:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
    - 検索を高速化するためのインデックス群を定義。
    - init_schema(db_path) でディレクトリ作成（必要時）→ DuckDB 接続 → 全DDLとインデックスを実行して初期化（冪等）。
    - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 差分更新（差分取得・バックフィル）を行う ETL ロジック骨格を実装。
    - 設計:
      - 最小データ開始日 _MIN_DATA_DATE = 2017-01-01
      - カレンダー先読み _CALENDAR_LOOKAHEAD_DAYS = 90
      - デフォルト backfill_days = 3（後出し修正を吸収）
    - ETLResult dataclass を追加（ターゲット日・取得/保存件数・品質問題・エラー等を格納）。品質チェックの重大度を判別するヘルパを提供。
    - DB ヘルパ: テーブル存在チェック、テーブルの最大日付取得（_get_max_date）を実装。
    - 市場カレンダー補正: 非営業日の場合に直近営業日へ調整する _adjust_to_trading_day を実装。
    - 差分取得ヘルパ: get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
    - run_prices_etl: 差分取得→jquants_client を使った取得と保存の流れを実装（date_from 自動算出, backfill_days 対応）。

### 変更 (Changed)
- 無し（初回リリース）

### 修正 (Fixed)
- 無し（初回リリース）

### セキュリティ (Security)
- news_collector にて SSRF と XML の脆弱性対策を実装:
  - defusedxml の採用、URL スキームチェック、プライベートアドレス拒否、リダイレクト時の検査、レスポンスサイズ制限、gzip 解凍後のサイズチェック。

### 既知の問題 (Known Issues)
- run_prices_etl の戻り値が不完全
  - src/kabusys/data/pipeline.py の最後にある run_prices_etl では、現状 return 文が "return len(records), " のように途中で終わっており（保存件数を返すべきところが欠落）、タプルが不正に構築される可能性があります。ユニットテストや本番実行前に修正が必要です（期待される戻り値は (fetched_count, saved_count)）。

- 一部のモジュールは未実装/空ファイル
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py が空のまま。実装を追加する必要があります。

## 参考・補足
- J-Quants API 関連:
  - レート制限: 120 req/min を固定間隔で遵守
  - リトライ: 最大 3 回、429 の場合は Retry-After を尊重
  - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰回避済み）

- NewsCollector の記事ID設計:
  - URL 正規化後に SHA-256 を取り、先頭32文字を ID とすることで utm_* 等のトラッキング差分による重複挿入を防止。

- DB 保存は可能な限り冪等性を重視:
  - raw_* の保存は ON CONFLICT DO UPDATE / DO NOTHING を使用し、重複挿入や後出し修正に対応。

---

将来的なリリースでは次の点を予定/検討してください:
- run_prices_etl のバグ修正と単体テストの追加
- strategy・execution モジュールの実装（信号生成・注文送信・ポジション管理）
- 品質チェックモジュール (kabusys.data.quality) の実装と pipeline との統合
- DB マイグレーション戦略・バージョン管理の導入

---