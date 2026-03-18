Changelog
=========
すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-18
-------------------

初期リリース。日本株自動売買システム (KabuSys) の基本コンポーネントを実装しました。
主な追加点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサーの強化：export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
  - 環境変数上書き制御（.env と .env.local の優先度、既存 OS 環境変数を保護する protected 機構）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティを提供。値の検証（KABUSYS_ENV, LOG_LEVEL 等）を実装。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する API 呼び出しを実装（ページネーション対応）。
  - RateLimiter による固定間隔スロットリングで API レート制限（120 req/min）を遵守。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰対策あり）。
  - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。DuckDB への保存は ON CONFLICT での冪等（upsert）を採用し、fetched_at を UTC で記録。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し、入力値の汚れに強い処理を提供。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能を実装。
  - 記事 ID を URL 正規化（トラッキングパラメータ削除等）→ SHA-256（先頭32文字）で生成して冪等性を確保。
  - defusedxml を用いた XML パース（XML Bomb 対策）、および受信サイズ上限（10MB）でメモリ DoS を防止。
  - リダイレクト先のスキーム検査・ホストのプライベートアドレス判定による SSRF 対策（カスタム RedirectHandler, DNS 解決検査）。
  - gzip 圧縮応答の解凍と解凍後サイズチェック（Gzip bomb 対策）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - テキスト前処理（URL 除去、空白正規化）、銘柄コード抽出（4桁数字 & known_codes フィルタ）。
  - DB 保存はチャンク分割 & トランザクションで実行し、INSERT ... RETURNING により実際に挿入されたレコードのみをカウント。
  - news_symbols の単一/バルク保存ロジックを実装（重複除去、トランザクション処理、ON CONFLICT DO NOTHING）。
  - run_news_collection により複数 RSS ソースの統合収集ジョブを実装。ソース単位で個別にエラーハンドリング（1ソース失敗でも他は続行）。
- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層を含むデータモデル DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions から始まり、prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance まで含む。
  - 各種チェック制約（CHECK, NOT NULL）、主キー、外部キー、インデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成・テーブル作成を行い、初期化済み DuckDB 接続を返す。get_connection() で既存 DB へ接続可能。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新・バックフィル（デフォルト backfill_days=3）を意識した ETL 処理の骨格を実装。
  - ETLResult データクラスで実行結果／品質問題／エラーを集約。品質チェック用のインタフェース（quality モジュールを参照）を組み込む設計。
  - 市場カレンダー先読み（日数定数）や trading day への調整ロジックを提供。
  - raw_prices / raw_financials / market_calendar の最終取得日取得ヘルパーを実装。
  - run_prices_etl により差分取得→保存（jquants_client の save_* を利用）を行う流れを実装（差分算出、ログ出力含む）。テスト容易性のため id_token を外部注入可能。
- テスト容易性を考慮した設計
  - jquants_client の id_token 注入や news_collector の _urlopen をモック差し替え可能にし、ユニットテストを行いやすく設計。

Security
- defusedxml の採用、SSRF 検査（ホストのプライベート判定、リダイレクト先検査）、レスポンスサイズ上限、gzip 解凍後サイズチェックなど、外部入力に対する複数の防御策を追加。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

Notes / Limitations
- quality モジュールは参照されているが本リリース範囲での実装状況に依存します（品質チェックの実装は別途）。
- run_prices_etl 等の ETL 関数は骨格実装を含みますが、運用上の細かい例外処理・スケジューリングは今後の改善対象です。
- DuckDB の SQL 実行で直接文字列を組み立てる箇所があるため（プレースホルダを使った実行を優先）、SQL インジェクション等に十分注意してください。現状は内部利用を想定しており、外部からの任意文字列注入経路は制限しています。

今後の予定（例）
- quality モジュールの実装・統合（欠損・スパイク検出など）。
- ETL のジョブスケジューリング（バックグラウンドワーカー/キュー連携）。
- execution（kabuステーション発注）や strategy モジュールの実装拡充。
- 単体テスト・統合テストの整備と CI パイプラインの導入。

--- End of changelog ---