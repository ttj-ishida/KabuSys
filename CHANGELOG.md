CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- 初回リリースを追加。
- パッケージメタ情報:
  - kabusys.__version__ = "0.1.0"
  - パブリックAPI: data, strategy, execution, monitoring を __all__ に定義（各サブパッケージの起点）。

- 環境設定管理 (kabusys.config):
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - ルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env、.env.local は上書き（override）される。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env のパース機能:
    - コメント行/空行対応、export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行内コメント処理等を実装。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB（DuckDB/SQLite）/システム設定のプロパティを定義。
    - 必須環境変数未設定時には ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
    - パス系環境変数は Path.expanduser() を使用して展開。

- J-Quants クライアント (kabusys.data.jquants_client):
  - API クライアントを実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar など）。
  - レート制御: _RateLimiter による固定間隔スロットリング（デフォルト 120 req/min を尊重）。
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回リトライ。
    - 408/429/5xx 系はリトライ対象。429 の場合は Retry-After を優先。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。ページネーション間でトークンを共有するモジュールレベルのキャッシュを搭載。
  - JSON レスポンスのデコードエラー時の明示的エラーメッセージ。
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - 各 fetch 関数は取得件数をログ出力。
  - DuckDB 保存関数（冪等設計）:
    - save_daily_quotes, save_financial_statements, save_market_calendar は ON CONFLICT DO UPDATE を用い重複を排除・更新する。
    - PK 欠損行はスキップしてログ出力。
  - 型変換ユーティリティ: _to_float, _to_int（小数部のある float 文字列を int へ丸めない挙動を明示）。

- ニュース収集 (kabusys.data.news_collector):
  - RSS フィードからのニュース収集・前処理・保存パイプラインを実装。
  - セキュリティ対策:
    - defusedxml による XML 攻撃防御。
    - SSRF 防止: URL スキーム検証、ホストがプライベート/ループバック/リンクローカルかの判定、リダイレクト先の事前検査（_SSRFBlockRedirectHandler）、最終URLの再検証。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MiB）を導入しメモリDoSを防止。gzip 解凍後にもサイズチェック。
    - HTTP/HTTPS 以外のスキームを拒否。
  - URL 正規化 (utm_* 等のトラッキングパラメータ削除、フラグメント削除、クエリソート) と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - RSS パース: content:encoded を優先、pubDate のパースと UTC 変換（失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: チャンク INSERT + トランザクション + INSERT ... RETURNING により実際に挿入された記事IDのリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで一括保存、INSERT ... RETURNING で挿入数を正確に取得。
    - 銘柄抽出: 正規表現で 4 桁数字を抽出し、known_codes に含まれるもののみを返す。
  - run_news_collection: 複数ソースを独立したエラーハンドリングで巡回し DB に保存。known_codes 指定時は新規挿入記事に対して銘柄紐付けを行う。

- DuckDB スキーマ (kabusys.data.schema):
  - DataPlatform の設計に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等のテーブルと制約（PK / CHECK / FOREIGN KEY）を実装。
  - 頻出クエリ向けのインデックス群を作成。
  - init_schema(db_path) によりディレクトリ作成→全DDL実行→インデックス作成を行い DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline):
  - ETLResult データクラスを導入し ETL 実行結果（取得数/保存数/品質問題/エラー等）を集約・辞書化できるように実装。
  - テーブル存在確認、最大日付取得等のユーティリティを実装。
  - 市場カレンダーに基づく営業日調整ヘルパーを実装（最大30日遡る）。
  - 差分更新の考え方を採用:
    - run_prices_etl による差分取得（最終取得日 - backfill_days から再取得）と保存処理を実装。
    - backfill_days により後出し修正を吸収可能（デフォルト 3 日）。
  - 品質チェックモジュール（quality）は呼び出し側で結果を検査する設計（ETL は全件収集を優先し Fail-Fast しない）。

- テスト/拡張性:
  - _urlopen をモック可能に設計（テストでの差し替えを想定）。
  - jquants_client の id_token 注入によりテスト容易性を確保。

Security
- RSS / HTTP 周りの SSRF 対策、defusedxml の採用、最大レスポンスサイズ制限、トラッキングパラメータ除去等を実装し、外部入力やネットワーク攻撃を考慮。

Known issues / Notes
- run_prices_etl のソースを見ると最後の return 文が不完全に見えます（現状コードは "return len(records)," のようにカンマで終了しており tuple を返す意図があるか不明瞭）。期待される戻り値は (fetched_count, saved_count) であり、実装の仕上げが必要です。
- パッケージ内のいくつかのサブパッケージ（kabusys.execution, kabusys.strategy, kabusys.data.__init__ など）は __init__.py が空またはプレースホルダのままで、追加実装が必要です。
- Settings._require は未設定時に ValueError を送出するため、実行環境では必須環境変数の準備が必要。
- DB スキーマは比較的詳細に定義されているが、現時点での互換性やマイグレーション機能は未実装。

Deprecated
- （なし）

Removed
- （なし）

Fixed
- （初回リリースのため該当なし）

Contributors
- 初期実装（モジュール分割・主要機能）を含むコードベース。

補足
- 以降のリリースでは、run_prices_etl の戻り値修正、strategy/execution の実装追加、品質チェック（quality モジュール）との統合テスト、より詳細なドキュメント・例示的使用方法の追加を推奨します。