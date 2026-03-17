# CHANGELOG

全ての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、リポジトリ内の現在のコードベース（初回公開相当）の内容から推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-17

Added
- パッケージ初版を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 設定管理: `kabusys.config`
  - .env/.env.local からの自動読み込み機能を実装（プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定）。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - `.env` の読み取りで次をサポート:
    - `export KEY=val` 形式
    - シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱い
  - `Settings` クラスを提供（プロパティ経由で設定値を取得）:
    - 必須トークンの取得（未設定時は ValueError を送出）: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス設定（DuckDB/SQLite）のデフォルト (`data/kabusys.duckdb`, `data/monitoring.db`)
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）
    - 環境種別を判定するヘルパープロパティ: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント: `kabusys.data.jquants_client`
  - 基本機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
    - ページネーション対応で全レコードを取得
  - レート制御:
    - 固定間隔スロットリング `_RateLimiter`（デフォルト 120 req/min）を実装
  - 再試行・エラーハンドリング:
    - 指数バックオフ付きリトライ（最大 3 回）
    - リトライ対象ステータス: 408, 429, 5xx
    - 429 時は `Retry-After` ヘッダ優先で待機時間を決定
    - ネットワークエラー（URLError/OSError）にも対応
  - 認証トークン管理:
    - リフレッシュトークンから ID トークンを取得する `get_id_token`
    - モジュールレベルでの ID トークンキャッシュと自動リフレッシュ（401 受信時に1回のみ再取得してリトライ）
  - DuckDB 保存:
    - 冪等性を担保する保存関数（ON CONFLICT DO UPDATE）:
      - `save_daily_quotes` -> `raw_prices`
      - `save_financial_statements` -> `raw_financials`
      - `save_market_calendar` -> `market_calendar`
    - レコード整形時に fetched_at を UTC 形式で記録
  - データ変換ユーティリティ:
    - `_to_float` / `_to_int`（文字列→数値の安全な変換、空値や不正値は None）

- ニュース収集モジュール: `kabusys.data.news_collector`
  - RSS フィードからニュース記事を取得し raw_news に保存する機能を実装
  - セキュリティ・堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等への対策）
    - SSRF 対策:
      - HTTP リダイレクト時にスキームとホスト/IP を事前検証するカスタムハンドラ `_SSRFBlockRedirectHandler`
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであればブロック
      - URL スキームは http/https のみ許可
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去してクエリパラメータをソートする `_normalize_url`
    - 正規化 URL の SHA-256 ハッシュ（先頭32文字）を記事IDとして利用（冪等性確保）
  - テキスト前処理:
    - URL 除去、空白正規化を行う `preprocess_text`
  - RSS 取得とパース:
    - `fetch_rss` が RSS を取得して記事リスト（NewsArticle）を返す（不正フィードは警告を記録して空リスト）
    - content:encoded を優先して本文を抽出
    - pubDate を UTC に変換して格納（パース失敗時は現在時刻で代替）
  - DB 保存:
    - `save_raw_news` はチャンク分割＋単一トランザクションで `INSERT ... ON CONFLICT DO NOTHING RETURNING id` を使い、実際に挿入された記事IDのリストを返す
    - `save_news_symbols` / `_save_news_symbols_bulk` によりニュースと銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、挿入件数を正確に返す）
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字候補を抽出し、与えられた known_codes セットに含まれるものだけを返す `extract_stock_codes`
  - 統合ジョブ:
    - `run_news_collection` により複数ソースを順次処理（各ソースは独立してエラーハンドリング。1ソース失敗でも他は継続）
    - 新規挿入記事に対する銘柄紐付けをまとめて保存するロジックを実装

- DuckDB スキーマ定義 / 初期化: `kabusys.data.schema`
  - Data Platform 設計に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブルを定義
  - 主なテーブル:
    - Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature: `features`, `ai_scores`
    - Execution: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 制約・チェック:
    - 主キー、外部キー、CHECK 制約（例: side, order_type, status の許容値チェック、数値チェックなど）を定義
  - インデックス:
    - 頻出パターンに対する複数のインデックスを作成（例: code, date によるスキャンを想定）
  - 公開 API:
    - `init_schema(db_path)` : 親ディレクトリ自動作成を行いスキーマを初期化して接続を返す（冪等）
    - `get_connection(db_path)` : 既存 DB への接続を返す（初期化はしない）

- ETL パイプライン: `kabusys.data.pipeline`
  - ETL 処理設計を実装（差分更新、バックフィル、品質チェック連携等の方針を反映）
  - `ETLResult` データクラスを追加（ETL 実行結果と品質問題・エラーを集約。辞書化メソッド付き）
  - DB ヘルパー:
    - テーブル存在チェック (`_table_exists`)
    - 日付最大値取得 (`_get_max_date`) とラッパー関数: `get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`
  - カレンダー関連ユーティリティ:
    - 非営業日の場合に直近の営業日へ調整する `_adjust_to_trading_day`
  - 個別 ETL ジョブ:
    - `run_prices_etl` を実装（差分更新・バックフィルの考慮、J-Quants からの取得と保存を行う）。差分ロジックは最終取得日ベースで date_from を自動決定する。
  - 設計上の特徴:
    - backfill_days による後出し修正吸収
    - 品質チェック（`kabusys.data.quality`）との連携を想定（重大度を保持し ETL を継続する設計）

Security
- RSS 収集周りで SSRF 対策、XML パースの安全化、レスポンスサイズ制限（DoS 対策）を導入。
- 環境変数の自動読み込みで OS 環境変数を保護する仕組み（protected set）を実装。

Notes / その他
- 設計方針として「冪等性」を重視（DuckDB への INSERT は ON CONFLICT を使用して上書き/スキップを行う）。
- ネットワーク周りは再試行/レート制御/トークン自動リフレッシュを組み合わせて堅牢化。
- テスト性の確保:
  - `news_collector._urlopen` を置き換え可能にして HTTP 周りのモックを容易にしている。
  - jquants_client の id_token は外部注入可能でページネーション間のトークン共有を行う設計。
- 提供コードは主要機能が実装されているが、ETL パイプラインの完全な実装（すべての ETL ジョブや品質チェック呼び出しの統合）は引き続き拡張が想定される。

お問い合わせ・補足
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB 初期化は `kabusys.data.schema.init_schema()` を利用してください。

---

参照:
- この CHANGELOG はソースコードの実装とドキュメント文字列から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリースポリシーに基づく追記・修正を行ってください。