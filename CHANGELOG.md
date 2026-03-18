# CHANGELOG

すべての注目すべき変更を記録します。本プロジェクトは Keep a Changelog の形式に準拠します。
リリースや変更内容は後続のバージョン管理と合わせて更新してください。

※本ファイルはリポジトリ内のソースコードから機能を推測して作成しています。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とエクスポート設定（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]

- 設定管理
  - 環境変数・.env 自動ロード機能を実装（src/kabusys/config.py）
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動読み込み
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）
    - .env の行パーサ実装（export プレフィックス、引用符エスケープ、コメント処理対応）
    - Settings クラスを公開:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値取得
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev ヘルパー

- J-Quants クライアント（データ取得・保存）
  - API クライアント実装（src/kabusys/data/jquants_client.py）
    - ベース URL と API 呼び出しラッパー実装
    - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの id_token キャッシュ
    - ページネーション対応（pagination_key）
    - データ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 数値変換ユーティリティ: _to_float, _to_int（不正値を安全に None に変換）

- ニュース収集（RSS）
  - RSS 収集・整形・DB 保存モジュール（src/kabusys/data/news_collector.py）
    - デフォルト RSS ソースを提供（例: Yahoo Finance ビジネス）
    - セキュリティ対策:
      - defusedxml を用いた XML パースで XML Bom 等を防止
      - SSRF 対策（リダイレクト先スキーム/ホスト検証）を行うカスタムリダイレクトハンドラ
      - URL スキーム検証（http/https のみ許可）、プライベートアドレス拒否
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および Gzip 解凍後の再チェック（Gzip-bomb 対策）
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等を削除）
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成（冪等性保証）
    - テキスト前処理（URL 除去、空白正規化）
    - RSS 取得関数 fetch_rss（XML パース失敗は警告を出して空リストを返す）
    - DuckDB への保存:
      - save_raw_news（チャンク INSERT、INSERT ... RETURNING で新規挿入 ID を返す、トランザクションでまとめる）
      - save_news_symbols / _save_news_symbols_bulk（記事と銘柄の紐付けを一括保存）
    - 銘柄コード抽出ロジック（4桁数字パターン + known_codes フィルタ）

- DuckDB スキーマ定義と初期化
  - スキーマ定義モジュール（src/kabusys/data/schema.py）
    - Raw / Processed / Feature / Execution 層テーブルの DDL を定義
    - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等を定義
    - 主要クエリ向けのインデックス定義を追加
    - init_schema(db_path) で DB ファイル親ディレクトリの自動作成とテーブル初期化を行い、DuckDB 接続を返す
    - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）

- ETL パイプラインの基礎
  - ETL パイプラインモジュール（src/kabusys/data/pipeline.py）
    - ETLResult データクラスで ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を集約
    - 差分更新ヘルパー実装:
      - get_last_price_date / get_last_financial_date / get_last_calendar_date
      - _get_max_date, _table_exists 等内部ユーティリティ
      - _adjust_to_trading_day（非営業日の調整）
    - run_prices_etl の実装（差分取得、backfill_days による再取得、_MIN_DATA_DATE の利用）
    - 定数:
      - _MIN_DATA_DATE = 2017-01-01（初回ロード基準）
      - _CALENDAR_LOOKAHEAD_DAYS = 90
      - _DEFAULT_BACKFILL_DAYS = 3

### 変更 (Changed)
- （初回リリースのため無し）

### 修正 (Fixed)
- （初回リリースのため無し）

### 削除 (Removed)
- （初回リリースのため無し）

### セキュリティ (Security)
- RSS パーシング周りに複数の防御を実装：
  - defusedxml による XML パース
  - リダイレクト先スキーム/ホスト検証で SSRF を軽減
  - レスポンスサイズ上限と Gzip 解凍後チェックで DoS/Bomb 攻撃に対処

### 既知の注意点 / 今後の改善候補
- run_prices_etl の戻り値ハンドリングや pipeline の一部（品質チェック quality モジュールの実行箇所等）は今後の拡張が想定されます（品質チェックはモジュール化されており、ETL の中で呼び出す設計）。
- duckdb を利用した SQL 実行時は SQL 文がコード内で組み立てられている箇所があるため、引数の取り扱いや SQL インジェクションの考慮が必要な場面が将来的に検討対象となり得ます（現状は内部利用と想定）。
- NewsCollector の既知銘柄リスト（known_codes）はユーザ側で供給する設計となっており、更新方法については運用手順整備が必要です。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、実運用に合わせて補足・修正を行ってください。