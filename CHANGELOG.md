# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  
リリース日付はコードベースから推測して記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- （今後の変更・追加予定をここに記載）

## [0.1.0] - 2026-03-17

初回リリース（推定）。日本株自動売買プラットフォームのコア基盤を実装。主な追加点・設計方針は以下の通り。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージの初期化（version = 0.1.0）。__all__ に data, strategy, execution, monitoring を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート判定は .git または pyproject.toml を起点に行い、CWD に依存しない実装。
  - .env パーサー: export 形式、クォート文字列、インラインコメントなどに対応。
  - Settings クラスを提供し、必須設定は _require() にて未設定時に ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - DUCKDB/SQLite ファイルパスのデフォルト、KABUSYS_ENV / LOG_LEVEL のバリデーション、is_live/is_paper/is_dev ユーティリティを提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライ戦略（指数バックオフ、最大3回）。HTTP 408/429/5xx 系はリトライ対象。
    - 401 Unauthorized 受信時はトークンを自動リフレッシュして1回だけリトライする仕組みを導入（無限再帰回避のため allow_refresh フラグ）。
    - モジュールレベルの ID トークンキャッシュを共有してページネーション中の再取得を抑制。
  - データ取得 API:
    - fetch_daily_quotes（株価日足, ページネーション対応）
    - fetch_financial_statements（財務データ, ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at を UTC で記録して Look-ahead Bias を防止
  - 型変換ユーティリティ: _to_float, _to_int（不正入力や小数切捨て防止の挙動を明示）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を安全に収集して DuckDB に保存する機能を実装。
    - defusedxml を用いた XML パースで XML Bomb 等から保護。
    - SSRF 対策:
      - リダイレクト検査ハンドラ (_SSRFBlockRedirectHandler) によるスキーム検査とホストのプライベートアドレス判定。
      - 初回と最終 URL のホスト検証。http/https スキームのみ許可。
      - ホスト名を DNS 解決して A/AAAA レコードを検査し、プライベート/ループバック/リンクローカルを拒否。
      - URL スキーム検証 (http/https のみ)。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 記事 ID はトラッキングパラメータ削除後の正規化 URL を SHA-256 でハッシュ（先頭32文字）して冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
    - fetch_rss により NewsArticle 型のリストを返す。
  - DuckDB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事 ID のみ返却（トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コード紐付けを一括保存。重複除去・チャンク挿入・RETURNING で正確な挿入数を取得。
  - 銘柄コード抽出:
    - extract_stock_codes: 正規表現で4桁銘柄コード候補を取得し、known_codes セットにあるもののみ返す（重複除去）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 向けのスキーマ定義を網羅的に追加（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（CHECK / PRIMARY KEY / FOREIGN KEY）を設定し、データ品質を担保。
  - 頻出クエリ用インデックスを定義（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成して DDL とインデックスを実行（冪等）。get_connection を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計原則と差分更新ロジックを実装（設計文書に基づく）。
    - 差分更新（最終取得日からの backfill による再取得）、API からの差分取得、保存、品質チェックのフロー。
  - ETLResult dataclass を実装し、品質問題やエラー概要を格納・辞書化するユーティリティを提供。
  - 市場カレンダー補正ヘルパー (_adjust_to_trading_day) を実装（最大30日遡りで直近の営業日に調整）。
  - 最終取得日取得ユーティリティ: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - run_prices_etl を実装（差分算出、fetch_daily_quotes 呼出し、save_daily_quotes による保存）。backfill_days, _MIN_DATA_DATE, _CALENDAR_LOOKAHEAD_DAYS 等の定数を定義。

- パッケージ構造
  - data サブパッケージに jquants_client, news_collector, schema, pipeline を配置。
  - strategy, execution, monitoring のためのパッケージスケルトンを追加（今後の実装予定を示唆）。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- RSS/HTTP 層での複数のセキュリティ対策を導入:
  - defusedxml による XML パース
  - SSRF 対策（スキーム検証・リダイレクト検査・プライベートIP検出）
  - レスポンスサイズ制限（メモリ DoS / Gzip bomb 対策）
  - URL 正規化でトラッキングパラメータを除去（識別子ハッシュ化前に実施）

### 既知の問題 / 注意点 (Known issues / Notes)

- run_prices_etl の戻り値がソース表示上途中で切れている（提示されたコードは最後が "return len(records)," で終わっており、(fetched, saved) のタプルが確実に返っていないように見えます）。実使用前に戻り値の帰着（saved 値の返却）を確認・修正してください（コードの切り取りに起因する可能性あり）。
- strategy / execution / monitoring パッケージはスケルトンまたは空の __init__ のみで、実際の取引戦略・発注ロジック・モニタリングは未実装。
- news_collector のホスト名 DNS 解決で OSError/ValueError が発生した場合は「安全側」で通過させる実装のため、極稀にプライベートアドレス判定が甘くなる可能性があります（設計上のトレードオフ：解決失敗時は非プライベートとみなす）。
- jquants_client のレート制御は単一プロセス内での固定間隔実装。マルチプロセス／分散環境で使用する場合は外部レートリミッタ等の検討が必要。

---

参照: 各モジュールの docstring に実装方針・設計原則・制約事項が記載されています。リリースノートはコードから推測して作成しています。必要があればリリース日やその他の詳細情報を更新します。