CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" に従って記載しています。
慣例: 変更はカテゴリ別に整理（Added, Changed, Fixed, Security, ...）。

[Unreleased]
------------

- （なし）


[0.1.0] - 2026-03-18
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの骨格を追加。
  - パッケージエントリポイント (src/kabusys/__init__.py) を追加し、バージョン 0.1.0 を定義。
- 環境設定 / ロード機能 (src/kabusys/config.py) を追加。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env の行パーサが export プレフィックス、引用符付き値（バックスラッシュエスケープ考慮）、インラインコメントをサポート。
  - OS環境変数を保護するオプションや .env.local の上書き挙動をサポート。
  - Settings クラスを提供し、J-Quants や kabu API、Slack、データベースパス、環境（development/paper_trading/live）やログレベルの検証機能を実装。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py) を追加。
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得関数を実装（pagination 対応）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）と 401 受信時の自動トークンリフレッシュを実装。
  - ID トークンのモジュールレベルキャッシュを導入（ページネーション間で共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による冪等性を保証。
  - 数値変換ユーティリティ（_to_float, _to_int）による堅牢な型変換。
- ニュース収集モジュール (src/kabusys/data/news_collector.py) を追加。
  - RSS フィード取得（gzip 対応） → テキスト前処理 → raw_news へ冪等保存 → 銘柄紐付け の一連処理を実装。
  - 記事IDは正規化後 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - defusedxml を使った XML パース（XML Bomb 対策）、HTTP レスポンスサイズ上限（10MB）チェック、Gzip 解凍後の再チェックを実装。
  - SSRF 対策: 初回ホスト検証、カスタムリダイレクトハンドラでリダイレクト先のスキーム/プライベートアドレスを拒否。
  - トラッキングパラメータ（utm_*, fbclid 等）除去と URL 正規化を実装。
  - DuckDB へのバルク保存はチャンク分割・トランザクション・INSERT ... RETURNING を用いて挿入された新規レコードを正確に取得（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。
  - 銘柄コード抽出ユーティリティ（4桁数字の検出と known_codes によるフィルタ）を実装。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を登録。
- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py) を追加。
  - Raw / Processed / Feature / Execution 層に対応したテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）と性能改善のためのインデックスを定義。
  - init_schema(db_path) で親ディレクトリ自動作成とテーブル作成を行う（冪等）。
  - get_connection(db_path) を提供（既存 DB 接続用）。
- ETL パイプライン基礎 (src/kabusys/data/pipeline.py) を追加。
  - ETLResult データクラス（ETL 実行結果、品質問題リスト、エラーリストを保持）。
  - 差分更新ヘルパー（最終取得日の取得、営業日調整）を実装。
  - run_prices_etl 等の差分 ETL ジョブの骨組みを導入（差分算出、backfill_days の考慮、_MIN_DATA_DATE、カレンダー先読み定数など）。
  - テスト容易性のため id_token 注入等を設計に反映。
- パッケージモジュールプレースホルダを追加（execution, strategy, data.__init__ 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- SSRF 対策を多数導入（news_collector: スキーム検証、プライベート IP 判定、リダイレクト時検査）。
- XML パースに defusedxml を採用して XML ベースの攻撃を軽減。
- .env のロードはプロジェクトルート検出に基づき動作し、KABUSYS_DISABLE_AUTO_ENV_LOAD によりテストで無効化可能（意図しない環境漏洩リスク低減）。

Notes / Implementation Details
- J-Quants クライアントはページネーション処理、トークン自動更新、レート制御、再試行を組み合わせた堅牢な設計。API 呼び出し失敗時は最大リトライ後に RuntimeError を送出。
- DuckDB 保存処理は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）、raw_news では INSERT ... RETURNING により新規挿入のみを検出。
- .env パーサはさまざまな実世界フォーマット（export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント）への互換性を持たせている。
- news_collector の URL 正規化はトラッキングパラメータ削除とクエリソートを行い、同一記事の重複登録を抑制。
- pipeline の差分ロジックはバックフィル（デフォルト 3 日）を行い、API の後出し修正に耐性を持たせる。

Breaking Changes
- なし（初回リリース）。

配布・利用上の注意
- settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定だと ValueError を送出するようになっています。初期設定を .env に用意してください（.env.example を参照）。
- DuckDB をファイルに保存する場合、init_schema() が親ディレクトリを作成します。":memory:" を渡すとインメモリ DB を使用できます。

--- 
（この CHANGELOG は、ソースコードに記載された実装・設計コメントから推測して作成した概要です。実際のリリースノートとして公開する前に、変更点や日付、要約文をプロジェクトのポリシーに合わせて調整してください。）