# Changelog

すべての注目すべき変更をここに記載します。これは Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成したものであり、実際のリリースノートは開発履歴に合わせて調整してください。

## [0.1.0] - 2026-03-18

### 追加
- 全体
  - 初期実装リリース。パッケージ名は `kabusys`、バージョンは `0.1.0`。
  - パッケージ公開用のモジュール構成を追加（data, strategy, execution, monitoring を __all__ に設定）。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env と .env.local の読み込み順を実装。`.env.local` は既存 OS 環境変数を protected として上書き制御。
  - .env パーサーを実装（コメント行・export プレフィックス・シングル/ダブルクォートやバックスラッシュエスケープに対応）。
  - 必須環境変数取得ヘルパー `_require()`、および各種プロパティ（J-Quants トークン、kabu API パスワード、Slack トークン／チャンネル、DB パス等）を実装。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の許容値バリデーションを実装（development / paper_trading / live、DEBUG..CRITICAL）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得クライアントを実装。
  - レート制御: 固定間隔スロットリングによるレートリミッタ（デフォルト 120 req/min）。
  - 再試行ロジック: ネットワークエラーと 408/429/5xx に対する指数バックオフ（最大3回）の再試行を実装。429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized を受けた場合のトークン自動リフレッシュ（1回のみ）と再試行ロジックを実装。モジュールレベルの ID トークンキャッシュをサポート。
  - JSON レスポンスのデコードとエラー処理を実装。
  - データ取得関数を提供:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を用いて保存
    - save_financial_statements: raw_financials テーブルへ保存（PK 重複は更新）
    - save_market_calendar: market_calendar テーブルへ保存
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、空値や不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集し DuckDB に保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベートアドレス判定（IP / DNS 解決を検査）、リダイレクト時の事前検証ハンドラを導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を防止。gzip 解凍後もサイズ検査を実施。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）除去とクエリソートを行う URL 正規化。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭32文字を採用し冪等性を担保。
  - RSS 取得処理 fetch_rss を実装（content:encoded 優先、pubDate パース、前処理で URL 削除・空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いたチャンクINSERT（トランザクションでまとめて実行）で新規挿入IDを返却。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク単位で INSERT ... RETURNING で実装。重複除去・トランザクション処理あり。
  - 銘柄コード抽出:
    - extract_stock_codes: テキストから 4 桁数字を抽出し、既知コード集合でフィルタする実装。
  - 統合ジョブ run_news_collection を実装。各ソースごとに独立したエラーハンドリングを行い、新規保存数と銘柄紐付けを処理。

- スキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）と型を明記。
  - 頻出クエリ向けのインデックスを作成（code/date 等）。
  - init_schema(db_path) を提供し、必要な親ディレクトリ自動作成と DDL 実行による初期化を行う（冪等）。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に基づく基盤処理を実装。
  - ETLResult データクラスを提供し、取得数・保存数・品質問題・エラーを集約して返却。
  - 差分取得用ユーティリティ:
    - テーブル存在チェック、最大日付取得用ヘルパー（_table_exists, _get_max_date）。
    - market_calendar を用いた非営業日調整ヘルパー（_adjust_to_trading_day）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - 個別 ETL ジョブの骨格を実装（例: run_prices_etl）。差分更新ロジック、バックフィル日数（デフォルト 3 日）、最小データ開始日（2017-01-01）、J-Quants からの取得と保存の流れを実装。

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 非推奨
- （初期リリースのため該当なし）

### セキュリティ
- ニュース収集で defusedxml、SSRF 検査、レスポンスサイズ制限、gzip 解凍後の再検査など複数の防御策を導入。
- .env ロードでは OS 環境変数を protected として上書き制御し、意図しない環境上書きを回避。

---

注: 本 CHANGELOG はコードから推測して作成した概要です。実際のリリースノートには、変更に関する責任者・影響範囲・マイグレーション手順（必要な場合）などを追記してください。