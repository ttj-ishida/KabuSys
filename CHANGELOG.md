# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

最新のリリースは [0.1.0] です — 2026-03-17

## [Unreleased]
（今後の変更はこちらに記載します）

## [0.1.0] - 2026-03-17
初期リリース。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（バージョン 0.1.0）。パッケージトップに __version__ を定義し、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルートを .git または pyproject.toml から自動検出するため、CWD に依存しない自動ロードを実現。
  - .env/.env.local の読み込み順をサポート（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を実装。
  - .env パーサを実装し、export プレフィックス・クォート文字・エスケープ・インラインコメント等のケースに対応。
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供。J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等の設定キーをプロパティとして公開。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）と便宜メソッド（is_live, is_paper, is_dev）を追加。

- J-Quants データクライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。以下のデータ取得メソッドを提供：
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（マーケットカレンダー）
  - 認証ヘルパー get_id_token（リフレッシュトークンから id_token を取得）を実装。モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
  - HTTP リクエスト処理における堅牢なリトライ戦略を実装：
    - 最大リトライ 3 回、指数バックオフ、408/429/5xx 系の再試行対応
    - 401 受信時は id_token を自動リフレッシュして最大 1 回リトライ（無限ループ回避のため allow_refresh フラグを考慮）
    - レスポンス JSON デコードエラーハンドリング
  - API レート制限（120 req/min）を守るための固定間隔レートリミッタ（_RateLimiter）を導入。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等性を保つために ON CONFLICT DO UPDATE を使用。取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレースを容易に。
  - 値変換ユーティリティ（_to_float, _to_int）を実装し、空値や不正値を安全に扱う。int変換では "1.0" のような float 文字列に配慮し、小数部が非ゼロの場合は None を返すなど精密に設計。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し、raw_news / news_symbols 等に保存する一連の処理を実装。
  - 記事IDを URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保（トラッキングパラメータ除去、クエリのソート化等を含む正規化）。
  - defusedxml を用いた XML パーシングで XML-Bomb 等の攻撃対策を実施。
  - SSRF 防止のための複数の対策を導入：
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時にスキーム/ホスト検査を行うカスタム HTTPRedirectHandler（_SSRFBlockRedirectHandler）
    - ホスト名を DNS 解決して得た IP を検査し、プライベート/ループバック/リンクローカル/マルチキャストを拒否
    - 最終 URL の再検証（冗長防御）
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）の導入と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - RSS の要素取得ロジック（title, content:encoded 優先, description, pubDate のパース）とテキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB 向けの保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装：
    - チャンク化バルクINSERT（_INSERT_CHUNK_SIZE）により SQL 長・パラメータ数を制限
    - トランザクションでまとめて挿入、INSERT ... RETURNING を使用して実際に挿入された ID/件数を正確に返す
    - 重複除去・ON CONFLICT DO NOTHING により冪等性を維持
  - テキストから銘柄コード（4桁）を抽出する extract_stock_codes を実装（既知コードセットでフィルタ、重複除去）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づくスキーマを実装。Raw / Processed / Feature / Execution 層のテーブル群を定義：
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）および頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・インデックス作成を行う初期化APIを提供。get_connection(db_path) で既存DBへ接続するヘルパーも追加。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ベースの ETL を実装（差分検出、バックフィル、保存、品質チェック呼出し）。
  - ETL 実行結果を表す ETLResult データクラスを提供（取得数・保存数・品質問題・エラー等を保持）。品質問題は辞書化してログや監査に出力可能。
  - テーブル存在チェック・最大日付取得等のユーティリティを提供。
  - 市場カレンダーに基づき非営業日を最も近い営業日に調整する _adjust_to_trading_day を実装。
  - 個別 ETL ジョブ（run_prices_etl 等）の骨子を実装。差分ロジック（最終取得日 - backfill_days）と最小取得日（_MIN_DATA_DATE = 2017-01-01）を採用。
  - 品質チェックは fail-fast ではなく、問題を収集して呼び出し元で判断できる設計。

### Performance
- API 呼び出しのレートリミット制御（固定間隔スロットリング）とリトライ／バックオフにより、外部 API へのアクセスを安定化。
- RSS/ニュース保存はチャンク化（バルクINSERT）・単一トランザクションにまとめることで DB オーバーヘッドを低減。

### Security
- RSS パースに defusedxml を利用し XML に関する攻撃を低減。
- RSS フェッチ時の SSRF 対策（スキーム検証、プライベートIP検出、リダイレクト検査）を実装。
- .env 読み込み時のファイル読み取りエラーを警告に変換し、安全にフォールバック。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Breaking Changes
- なし（初期リリース）。

### Migration notes / Upgrade instructions
- 既存のプロジェクトに導入する場合:
  - init_schema() を用いて DuckDB スキーマを初期化してください（既存テーブルがあればスキップされます）。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。設定がない場合、Settings の該当プロパティ呼び出しで ValueError が発生します。
  - 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

貢献・報告
- バグ報告・機能提案はリポジトリの Issues にお願いします。