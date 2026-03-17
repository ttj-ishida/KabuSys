# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初期リリースを記録しています。

## [0.1.0] - 2026-03-17

### Added
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) とバージョン定義 (0.1.0) を追加。
  - モジュール化されたパッケージ構成: data, strategy, execution, monitoring。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱いなどをサポート。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require() を提供。
  - 各種設定プロパティ（J-Quants, kabuステーション, Slack, DB パス, 環境/ログレベル判定等）を追加。値のバリデーション（env, log_level）を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース実装とユーティリティ関数を追加。
  - レート制御: 固定間隔スロットリングによる RateLimiter（120 req/min）を実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、ネットワーク起因/サーバーエラーに対するリトライ。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン: リフレッシュトークンから ID トークンを取得する get_id_token 関数。401 受信時にトークンを自動リフレッシュして 1 回リトライする挙動を実装（無限再帰防止）。
  - データ取得: 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）をページネーション対応で実装。
  - DuckDB への冪等保存関数を実装: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - データ変換ユーティリティ: _to_float, _to_int（空値や不正値処理、float 文字列の安全な整数変換含む）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する一連処理を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証、プライベートアドレス判定、リダイレクト時の検証を行うカスタム RedirectHandler を実装。
    - レスポンス読み込み上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の上限検査を実装。
  - URL 正規化: トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリソートによる正規化を実装。
  - 記事ID 生成: 正規化 URL の SHA-256 ハッシュ先頭 32 文字を使用して冪等性を保証。
  - 前処理: URL 除去・空白正規化を行う preprocess_text。
  - DB 保存:
    - save_raw_news: チャンク挿入、トランザクションでまとめて INSERT ... RETURNING id により新規挿入 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、RETURNING を利用して実際の挿入数を正確に取得）。
  - 銘柄抽出: テキスト中の 4 桁数字を正規表現で抽出し、known_codes に含まれるものだけを返す extract_stock_codes。
  - run_news_collection: 複数ソースを順に処理し、個別ソースの失敗は他ソースに影響させずに収集を継続する高耐障害なジョブ処理を実装。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けのインデックスを追加。
  - init_schema(db_path) によりファイルの親ディレクトリ自動作成、DDL を冪等に実行して初期化する API を提供。get_connection() で既存 DB へ接続。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計に基づく差分更新ワークフローの基盤を実装。
  - ETLResult データクラス: 実行結果・品質問題・エラー一覧を集約・辞書化するユーティリティを提供。
  - DB ヘルパ: テーブル存在チェック、最大日付取得（_get_max_date）を実装。
  - 市場カレンダー補正: 非営業日の場合に直近営業日に調整する _adjust_to_trading_day を提供。
  - 差分取得ヘルパ: raw_prices/raw_financials/market_calendar の最終取得日を取得する get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
  - run_prices_etl の骨子を実装（差分計算、バックフィル日数、fetch + save の流れ）。  

### Security
- defusedxml の採用により XML パースに対する攻撃耐性を強化。
- RSS 取得時の SSRF 防止（スキーム検証、プライベートアドレス検出、リダイレクト時の検証）。
- .env 読み込み時に OS 環境変数を保護する protected パラメータを導入（.env.local の override 挙動制御）。

### Performance
- API 呼び出しのレートリミット（固定間隔スロットリング）と指数バックオフにより外部 API とのやり取りを安定化。
- raw_news / news_symbols のバルク INSERT をチャンク化してトランザクションでまとめ、DB オーバーヘッドを削減。
- DuckDB スキーマにインデックスを追加し、銘柄×日付のスキャンやステータス検索の効率を向上。

### Reliability / Data Quality
- J-Quants クライアントでのページネーション対応とフェッチ日時（fetched_at）記録により Look-ahead Bias を防止。
- save_* 関数は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を担保。
- ETL の差分/バックフィル戦略により API の後出し修正に対処。
- news_collector はサイズ上限・gzip 解凍上限などで大量レスポンス攻撃（DoS）を抑制。

### Notes
- 一部の ETL 関数（pipeline モジュール）には今後の拡張が想定される箇所があります（例: run_prices_etl の戻り値形式や追加の品質チェック統合など）。
- strategy, execution, monitoring パッケージはエントリポイントを用意していますが、具体的な戦略・発注ロジックはこれから実装される想定です。

### Breaking Changes
- 初回リリースのため該当なし。

--- 

このリリースは初期設計・実装フェーズであり、以降のリリースで戦略ロジック、発注実行部分、詳細な品質チェック、テストカバレッジ拡充、ドキュメント整備などを追加予定です。