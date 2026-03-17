# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-17
初回リリース

### Added
- パッケージ基本情報
  - パッケージ名: KabuSys。バージョン定義: `__version__ = "0.1.0"`。
  - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理 (`kabusys.config`)
  - .env/.env.local からの自動読み込みを実装（プロジェクトルートは `.git` または `pyproject.toml` を探索して特定）。
  - 自動読み込みを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env 読み込みロジック: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを考慮したパーサを実装。
  - `.env.local` は `.env` 上書きとして読み込まれる（OS 環境変数は保護される）。
  - 必須環境変数取得ヘルパー `_require()` と、Settings クラスにより以下の設定をプロパティとして提供:
    - J-Quants/J-Quants Refresh Token（JQUANTS_REFRESH_TOKEN）
    - kabuステーション API 設定（KABU_API_PASSWORD, KABU_API_BASE_URL）
    - Slack 設定（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - DB パス（DUCKDB_PATH, SQLITE_PATH）を Path オブジェクトで返す
    - 実行環境（KABUSYS_ENV: development/paper_trading/live の検証）や LOG_LEVEL 検証
    - is_live / is_paper / is_dev のブールヘルパー

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本設計:
    - レート制限を厳守（120 req/min）する固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ、対象ステータス: 408, 429, 5xx）。
    - 401 受信時は ID トークンを自動リフレッシュして最大1回リトライ。モジュールレベルでトークンキャッシュを保持。
    - JSON デコード失敗やリトライ上限超過時の明確な例外化。
  - API 呼び出しユーティリティ `_request()` を実装。
  - 認証ヘルパー `get_id_token()`（refresh token → idToken の取得）。
  - データ取得関数（ページネーション対応）:
    - `fetch_daily_quotes()`：株価日足（OHLCV）
    - `fetch_financial_statements()`：四半期財務データ
    - `fetch_market_calendar()`：JPX マーケットカレンダー
  - DuckDB への保存（冪等）関数:
    - `save_daily_quotes()`：raw_prices への INSERT ... ON CONFLICT DO UPDATE
    - `save_financial_statements()`：raw_financials への INSERT ... ON CONFLICT DO UPDATE
    - `save_market_calendar()`：market_calendar への INSERT ... ON CONFLICT DO UPDATE
  - 値変換ユーティリティ: `_to_float()` / `_to_int()`（安全な変換、空値ハンドリング、"1.0"→int の挙動制御など）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード収集と前処理フロー実装:
    - デフォルトソース: Yahoo Finance のビジネス RSS。
    - レスポンスサイズ上限: `MAX_RESPONSE_BYTES = 10MB`（読み込み時に超過を検出してスキップ）。
    - gzip 圧縮解凍の対応と Gzip-bomb 対策（解凍後サイズチェック）。
    - XML パースは defusedxml を利用して安全に処理。
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリソート。
    - 記事ID は正規化 URL の SHA-256 ハッシュの先頭32文字で生成（冪等性確保）。
    - テキスト前処理: URL 除去、連続空白を単一スペースに正規化、トリム（preprocess_text）。
    - RSS の pubDate パース（RFC2822 形式）を UTC に変換。パース失敗時は警告ログと現在時刻で代替。
    - SSRF 対策:
      - フェッチ前にホストがプライベートアドレスかを判定（IP 直接判定 + DNS 解決で A/AAAA をチェック）。
      - リダイレクト時にスキームとホストの検査を行うカスタム HTTPRedirectHandler（_SSRFBlockRedirectHandler）。
      - 許可スキームは http/https のみ。
    - フィード解析は柔軟に <content:encoded> を優先、description をフォールバック。
  - DB 保存:
    - `save_raw_news()`：raw_news テーブルへチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。トランザクションで安全にコミット。
    - `save_news_symbols()`：news_symbols テーブルへ個別記事の銘柄紐付け（INSERT ... RETURNING で挿入数を返す）。
    - `_save_news_symbols_bulk()`：複数記事分をチャンクで一括保存（重複除去、トランザクション）。
  - 銘柄コード抽出:
    - 日本株に一般的な4桁数値パターンで抽出（正規表現 \b(\d{4})\b）し、known_codes セットでフィルタリングする `extract_stock_codes()` を提供。
  - 統合ジョブ `run_news_collection()`：複数ソースを独立に処理し、new_ids に基づいて銘柄紐付けを一括保存する。

- データベーススキーマ (`kabusys.data.schema`)
  - DuckDB 用スキーマ定義ファイルを実装。3層（Raw / Processed / Feature）+ Execution 層のテーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date 等）。
  - `init_schema(db_path)`：ディレクトリ自動作成、全DDL とインデックスを冪等で実行して接続を返す。
  - `get_connection(db_path)`：既存DBへの接続取得（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL 設計方針と差分更新ロジックの実装方針（差分更新、backfill、品質チェック継続方針など）を実装。
  - ETL 結果を表す dataclass `ETLResult`（品質課題・エラーの集約、has_errors / has_quality_errors プロパティ、辞書変換）。
  - DB ユーティリティ:
    - テーブル存在チェック `_table_exists()`。
    - 指定カラムの最大日付取得 `_get_max_date()`。
    - market_calendar に基づく営業日調整 `_adjust_to_trading_day()`。
    - raw テーブル最終取得日取得ヘルパー: `get_last_price_date()`, `get_last_financial_date()`, `get_last_calendar_date()`。
  - 個別 ETL ジョブ（差分ETL）:
    - `run_prices_etl()`：差分取得のための date_from 自動算出（最終取得日から backfill 日数を考慮）、J-Quants からの取得と保存（fetch/save の呼び出し）。（※ ソース抜粋のため一部実装が続く想定）

### Security
- XML パースに defusedxml を使用し XML 攻撃（XML bomb 等）に対処。
- RSS フェッチにおける SSRF 対策を複数レイヤーで実装:
  - フェッチ前のホスト（プライベートチェック）
  - リダイレクト時の検査（_SSRFBlockRedirectHandler）
  - 許可スキームの制限（http/https のみ）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後の再検査によりメモリ DoS を防止
- .env 読み込みでは OS 環境変数を保護する仕組みを導入（protected set）。

### Internal / Implementation details
- J-Quants クライアント:
  - レート制限: 120 req/min（_MIN_INTERVAL_SEC = 60 / 120）。
  - リトライ: 最大3回、指数バックオフ base=2.0、429 の場合は Retry-After を優先。
  - ID トークンはモジュールレベルでキャッシュ（ページネーション間で共有）。
- NewsCollector:
  - 記事IDは URL 正規化後 SHA-256 の先頭32文字。
  - デフォルト RSS ソースは `DEFAULT_RSS_SOURCES` に定義（現状 Yahoo）。
  - チャンク処理サイズ: `_INSERT_CHUNK_SIZE = 1000`。
- DuckDB スキーマは冪等に作成されるため、初回・再初期化とも安全に実行可能。

### Notes / TODOs
- strategy / execution / monitoring モジュールの __init__ はプレースホルダ（空）として存在。戦略や発注ロジック、監視機能は別途実装予定。
- pipeline.run_prices_etl 等の一部処理は抜粋版を元にしており、ETL の品質チェックやログ出力の統合など追加実装箇所がある想定。
- 各モジュールはテスト用に一部内部関数（例: news_collector._urlopen、jquants_client のトークン注入）をモック可能な設計になっている。

---

今後のリリースでは、strategy・execution 層の具体的なアルゴリズム実装、モニタリング/アラート統合、品質チェックモジュールの詳細実装、および CI テストやドキュメント拡充などを予定しています。必要であれば CHANGELOG の英語版やリリースノート（各機能ごとの詳細説明）も作成します。