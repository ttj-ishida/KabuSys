CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初回リリースを追加。
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0, __all__ 宣言）。
  - 空のサブパッケージプレースホルダを追加: kabusys.execution, kabusys.strategy, kabusys.monitoring（将来の拡張用）。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val, 引用符あり/なし、インラインコメント等を考慮した堅牢な .env パーサーを実装。
  - Settings クラスを実装し、必須環境変数の取得、既定値、バリデーション（KABUSYS_ENV, LOG_LEVEL 等）を提供。
- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出し基盤を実装（_request）：JSON デコード、タイムアウト、パラメータ付与、POST ボディ対応。
  - レート制御（_RateLimiter）により 120 req/min の制限を遵守する固定間隔スロットリングを実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx のリトライ）を実装。
  - 401 を受け取ったときにリフレッシュトークンで自動的に id_token を更新して 1 回リトライする処理を実装（無限再帰防止）。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - データ取得 API 実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE／DO NOTHING）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - ユーティリティ関数: 型安全な _to_float/_to_int（空値・不正値を None に変換）を実装。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能を実装（fetch_rss）:
    - defusedxml を使った安全な XML パース、gzip 対応、Content-Length/受信サイズ制限（最大 10 MB）によるメモリ攻撃対策。
    - SSRF 対策：URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/プライベートアドレス検査（カスタム RedirectHandler）、ホストのプライベート判定。
    - レスポンスの正規化（URL 正規化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - content:encoded と description の優先度処理、pubDate の RFC2822 パース（UTC 正規化、パース失敗時は代替時刻）。
  - DuckDB 保存ルーチンを実装:
    - save_raw_news: チャンク INSERT + INSERT ... RETURNING id を用いて新規挿入 ID を正確に返す。トランザクションを使用して安全にコミット/ロールバック。
    - save_news_symbols: 単記事分の銘柄紐付け（INSERT ... RETURNING で挿入数を返す）。
    - _save_news_symbols_bulk: 複数記事の銘柄紐付けをチャンク化して一括挿入（重複除去、トランザクション）。
  - 銘柄コード抽出機能（extract_stock_codes）を実装：4桁の数字候補を抽出して known_codes に基づきフィルタ、重複除去。
  - 高レベル統合ジョブ run_news_collection を実装：複数 RSS ソースから収集し DB 保存、既知銘柄との紐付けを一括で実行。各ソースは個別にエラーハンドリング。
- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 頻出クエリに備えたインデックス群を定義。
  - init_schema(db_path) を実装：親ディレクトリ自動作成、全 DDL／インデックスを冪等に実行して DuckDB 接続を返す。
  - get_connection(db_path) を実装：既存 DB への接続を返す（スキーマ初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に基づく基礎実装を追加:
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーリスト等を含む）。
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）を実装。
    - 市場カレンダー補正ヘルパー (_adjust_to_trading_day) を実装（非営業日の補正）。
    - 差分更新のためのヘルパー関数: get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
    - run_prices_etl の雛形を実装（差分計算、backfill デフォルト 3 日、J-Quants 取得→保存のワークフロー）。設計上、後続の品質チェックフック等へ接続可能。

Security
- RSS パーサーに defusedxml を採用し XML ベース攻撃を軽減。
- SSRF 緩和策を複数導入（スキーム制限、DNS 解決によるプライベートアドレス判定、リダイレクトハンドラの事前検査）。
- レスポンス長や gzip 解凍後サイズのチェックにより Gzip-Bomb / メモリ DoS を軽減。

Notes / Design decisions
- 多くの DB 操作は DuckDB の INSERT ... ON CONFLICT 句や INSERT ... RETURNING を利用して冪等性と正確な挿入情報を確保。
- API 呼び出しは rate limit と retry を明示的に実装し、トークン切れ時の自動リフレッシュをサポート（ただし無限再帰を防止）。
- 環境変数の自動読み込みはプロジェクトルートから行うため、配布後もカレントワーキングディレクトリに依存しない設計。
- ニュース記事 ID はトラッキングパラメータ除去後にハッシュ化して生成、同一コンテンツの重複挿入を防ぐ。

Breaking Changes
- 初版のため該当なし。

Acknowledgements / TODO
- strategy, execution, monitoring サブパッケージは今後の実装予定。
- ETL の品質チェック（quality モジュール連携）や run_prices_etl の完全なワークフロー統合は継続実装予定。
- ドキュメント（DataPlatform.md, DataSchema.md 参照）に合わせたテストと例示スクリプトを追加予定。