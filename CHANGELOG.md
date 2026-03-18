CHANGELOG
=========

すべての注目すべき変更履歴をここに記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。
リリース日付はコードベースの現状から推測して記載しています。

Unreleased
----------
- なし（次のリリースに向けて実装・改善を予定）
  - 戦略（strategy）および発注/実行（execution）モジュールの実装強化
  - 監視（monitoring）モジュールの具現化（現在はパッケージ名のみ定義）
  - ETL パイプラインの追加テスト・品質チェックルールの拡張

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ基本構成を追加
  - kabusys パッケージ（src/kabusys/__init__.py）を導入。バージョン 0.1.0 を設定。
  - サブパッケージの骨格を準備（data, strategy, execution, monitoring を公開）。

- 環境設定管理モジュール（src/kabusys/config.py）を追加
  - .env ファイルおよび環境変数の自動読み込み機構（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env/.env.local の読み込み順序、OS 環境変数の保護（protected set）。
  - export KEY=val 形式やクォート付き値、インラインコメント、コメントの扱いを考慮したパーサー実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティを提供。
  - 環境変数チェック（必須値の検査）とバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加
  - API 呼び出しの共通処理: 固定間隔レートリミッタ（120 req/min）、最大リトライ（指数バックオフ）、リトライ対象ステータス（408/429/5xx）。
  - 401 受信時の自動トークンリフレッシュ（1 回）とトークンキャッシュ共有。
  - JSON デコード失敗時の明示的エラー、タイムアウト設定、ページネーション対応を実装。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（いずれもページネーション対応）。
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 取得時刻 (fetched_at) を UTC で記録し、Look-ahead Bias 対策を考慮。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、安全な数値変換を提供。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）を追加
  - RSS フィードからの記事取得（fetch_rss）および前処理 / DB 保存の実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - セキュリティ対策: defusedxml による XML パース、SSRF 防止のためのリダイレクト検査ハンドラ、ホストのプライベートアドレス検出（DNS 解決と IP 判定）を導入。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化（追跡パラメータ削除、クエリソート、フラグメント削除）と記事ID生成（SHA-256 の先頭 32 文字）。
  - テキスト前処理（URL 除去、空白正規化）、銘柄コード抽出（4桁数字、known_codes によるフィルタリング）。
  - DB 保存はチャンク化して一括挿入、トランザクション管理、INSERT ... RETURNING により実際に挿入された件数を返す。
  - DEFAULT_RSS_SOURCES（例: Yahoo Finance ビジネスカテゴリ）を定義。
  - 統合ジョブ run_news_collection を実装（各ソースの個別エラーハンドリング、銘柄紐付けの一括登録）。

- DuckDB スキーマ定義 & 初期化（src/kabusys/data/schema.py）を追加
  - Raw / Processed / Feature / Execution 層に渡るテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 各テーブルに制約（PRIMARY KEY、CHECK、FOREIGN KEY 等）を設定し、データ品質を担保。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成を含む初期化処理を実装（冪等）。
  - get_connection(db_path) による既存 DB への接続 API を提供。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）を追加
  - 差分更新（差分取得）を行う ETL 設計。最小データ開始日やカレンダー先読み、バックフィル日数などを定義。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーの集約を提供。
  - テーブル存在チェック、最大日付取得ヘルパー、取引日補正ロジック（market_calendar に基づく調整）を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date のユーティリティを追加。
  - run_prices_etl 実装: 差分計算（last date を基に date_from を決定）、J-Quants からの取得と保存の呼び出し、ログ出力を行う（backfill_days により後出し修正を吸収）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- ニュース収集周りで複数の安全対策を導入
  - defusedxml による XML パース（XML 脆弱性対策）
  - SSRF 対策: リダイレクト先のスキーム/ホスト検査、プライベートIP判定、最終 URL の再検証
  - レスポンスサイズチェックと gzip 解凍後の追検査（メモリ DoS 対策）
  - URL スキーム検証により file:, mailto:, javascript: 等を排除

Performance
- J-Quants API クライアントで固定間隔レートリミットと指数バックオフを導入し、API レート制限と再試行の効率化を図る。
- DB 保存処理はバルク挿入・チャンク化・トランザクションまとめによりオーバーヘッドを削減。

Notes / Known state
- strategy/ と execution/ の __init__.py は存在しますが、具体的な戦略ロジック・発注実装は未実装でプレースホルダです。
- monitoring はパッケージ公開名として定義されていますが、実装は含まれていません。
- pipeline モジュールは ETL の骨格を備えていますが、品質チェックモジュール（quality）の具合や各 ETL ジョブの完全な例外処理やユニットテストの網羅は今後の作業対象です。
- 今後のリリースで以下を予定:
  - strategy / execution / monitoring の実装
  - テストケース・CI の整備（特にネットワークリクエストや DB 操作のモック）
  - 品質チェックルールの拡充と運用向けドキュメントの追加

Appendix
- この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴や運用上の変更点とは差異がある場合があります。必要があれば実際のコミット履歴・バージョニング方針に合わせて調整してください。