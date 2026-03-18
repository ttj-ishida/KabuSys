CHANGELOG.md
=============

すべての注目すべき変更履歴をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

### Known issues
- run_prices_etl の戻り値が期待される (fetched, saved) のタプルになっておらず、実装上のミスにより第二要素が返っていない可能性があります（コード末尾に "return len(records)," のような形でトレイリングコンマが見られます）。次リリースで修正予定。

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)。
- 基本モジュールを実装：
  - kabusys.config
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、CWD に依存しない自動読み込みを実現。
    - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント判定等に対応）。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
    - 必須設定取得ヘルパー _require と Settings クラスを実装（J-Quants トークン、kabu API パスワード、Slack 設定、DB パス、環境/ログレベル判定等）。
  - kabusys.data.schema
    - DuckDB 用のスキーマ定義と init_schema/get_connection を実装。
    - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル DDL を用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - よく使うクエリのためのインデックス群を定義。
    - ディスク上の DB ファイルの親ディレクトリ自動作成に対応。":memory:" インメモリ DB をサポート。
  - kabusys.data.jquants_client
    - J-Quants API クライアントを実装。
    - レート制限制御（固定間隔スロットリング、デフォルト 120 req/min）を実装する RateLimiter を導入。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
    - 401 時の自動トークンリフレッシュを実装（1 回のみリフレッシュして再試行）。トークン取得は get_id_token 経由で行い、モジュールレベルのキャッシュを保持。
    - JSON デコード失敗時の明確なエラーメッセージ、429 の Retry-After ヘッダ考慮などの堅牢化。
    - データ取得関数を実装：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB へ冪等に保存する save_daily_quotes, save_financial_statements, save_market_calendar を実装（ON CONFLICT DO UPDATE）。
    - 値変換ユーティリティ _to_float / _to_int を実装（不正値や小数を含む整数表現の扱いを明確化）。
  - kabusys.data.news_collector
    - RSS フィードからのニュース収集モジュールを実装。
    - セキュリティ対策:
      - defusedxml を使用して XML Bomb 等を防御。
      - SSRF 対策としてリダイレクト時にスキーム/ホスト検査を行う専用リダイレクトハンドラを実装。初回 URL と最終 URL の両方を検証。
      - HTTP/HTTPS 以外のスキーム拒否。
      - ホストがプライベート/ループバック等の場合はアクセス拒否またはスキップするロジックを実装。
      - レスポンス受信サイズを MAX_RESPONSE_BYTES（デフォルト 10MB）で制限しメモリ DoS を緩和。gzip 解凍後のサイズもチェック。
    - 記事 ID は URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去等）してから SHA-256 の先頭32文字を使用し冪等性を確保。
    - 記事テキストの前処理（URL 除去、空白正規化）と pubDate の堅牢なパース（UTC 基準、フォールバック時は現在時刻を使用）。
    - fetch_rss 実装：RSS の柔軟なパース（channel/item の存在確認、content:encoded の優先使用）とエラーハンドリング。
    - DuckDB への保存機能を実装：save_raw_news（バルク挿入、チャンク化、トランザクション、INSERT ... RETURNING を使用して新規挿入IDを返す）、save_news_symbols / _save_news_symbols_bulk（ニュースと銘柄の紐付けを効率的に挿入）。
    - 銘柄コード抽出ロジックを実装（日本株の4桁コード候補を正規表現で抽出し、known_codes でフィルタリング）。
    - run_news_collection：複数ソースを処理、ソース単位でのエラーハンドリング、新規保存件数を集計して返す。
  - kabusys.data.pipeline
    - ETL パイプライン用の枠組みを実装。
    - ETLResult データクラスを実装（対象日、各種取得/保存件数、品質問題リスト、エラーリスト、シリアライズ用 to_dict）。
    - 差分更新ユーティリティ（テーブル存在確認、最大日付取得）を実装。
    - 市場カレンダー補助関数 _adjust_to_trading_day を実装（非営業日の調整、最大 30 日遡り）。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
    - run_prices_etl を実装（差分取得ロジック、デフォルトバックフィル日数 = 3、J-Quants クライアントを用いた取得と保存の呼び出し）。
- その他
  - パッケージの __init__ でバージョン情報と主要サブパッケージを公開。

Changed
- 初版のため、Backward-incompatible な変更履歴はなし。

Fixed
- 初版リリース：該当なし（以降のリリースでバグ修正予定）。ただし既知の問題を Unreleased に記載。

Security
- news_collector に複数のセキュリティ対策を導入（defusedxml、SSRF リダイレクト検査、プライベートアドレス検出、レスポンスサイズ制限）。

Notes / Usage
- 環境読み込み:
  - 自動的にプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先され、.env.local は上書きを行います）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB:
  - スキーマ初期化は init_schema(db_path) を使用してください。既存 DB があればスキップされます。get_connection は既存 DB 接続取得に使用します。
- J-Quants:
  - J-Quants の refresh token は Settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）から取得されます。
  - API レート制限とリトライはクライアント側で制御されますが、実運用時は更なる監視を推奨します。
- NewsCollector:
  - デフォルトの RSS ソースは Yahoo Finance のビジネスカテゴリに設定されています。sources 引数で上書き可能です。
  - 銘柄抽出には known_codes を渡す必要があります（渡さない場合は紐付けをスキップします）。

Contributing
- バグ報告、改善提案、セキュリティ問題の報告は issue を作成してください。重大なセキュリティ問題は公開前に運営に直接連絡してください。

Acknowledgements
- 本リリースは内部設計文書（DataPlatform.md / DataSchema.md 等）に基づき実装されました。