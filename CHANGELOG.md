# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトの最初の公開リリースを記録します。

## [0.1.0] - 2026-03-18

初期リリース。

### 追加
- パッケージのエントリポイント
  - kabusys パッケージを初期化（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution。バージョンは 0.1.0。

- 環境設定管理
  - settings を提供する Settings クラスを実装（src/kabusys/config.py）。
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 読み込み時の上書き制御（override / protected）をサポートし、OS 環境変数保護に対応。
  - .env の行パース機能を強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行でのインラインコメント認識 (直前が空白/タブの場合)
  - 必須環境変数チェック（_require）と各種設定プロパティ（J-Quants、kabu API、Slack、DB パス、環境種別、ログレベル、is_live / is_paper / is_dev）。

- J-Quants API クライアント
  - jquants_client モジュールを実装（src/kabusys/data/jquants_client.py）。
  - 機能:
    - 株価日足（OHLCV）の取得（ページネーション対応）
    - 財務データ（四半期 BS/PL）の取得（ページネーション対応）
    - JPX マーケットカレンダー取得
    - リフレッシュトークンから ID トークン取得（get_id_token）
  - 設計上の特徴:
    - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象は ネットワーク系エラーや 408/429/5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰防止）。
    - 取得時刻（fetched_at）を UTC で付与し、Look-ahead Bias を防止できる設計。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除する save_* 関数を提供。
  - ユーティリティ:
    - 型変換ヘルパー _to_float / _to_int（不正値や小数部がある場合の int 変換ルールを明確化）。

- ニュース収集（RSS）
  - news_collector モジュールを実装（src/kabusys/data/news_collector.py）。
  - 機能:
    - RSS フィードから記事取得（fetch_rss）と前処理（preprocess_text）。
    - 記事ID は URL 正規化後の SHA-256 の先頭 32 文字で生成（utm_* 等のトラッキングパラメータ除去を実施）。
    - XML パースに defusedxml を使用し XML Bomb 等に対する安全対策を実施。
    - リダイレクト時の SSRF 対策（スキーム検証とプライベートアドレス拒否）を組み込んだカスタムリダイレクトハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）によりメモリ DoS を防止。gzip 解凍後もサイズ検査を実施。
    - URL スキーム検証（http/https のみ許可）。非対応スキームやプライベートホストは拒否。
    - pubDate の解析と UTC への整形（失敗時は警告ログと現在時刻で代替）。
    - raw_news テーブルへの保存はチャンク INSERT + トランザクション + INSERT ... RETURNING を利用し、新規挿入された記事 ID を正確に返す（save_raw_news）。
    - 記事と銘柄コードの紐付けを行う save_news_symbols / _save_news_symbols_bulk（重複排除、チャンク/トランザクションあり）。
    - 銘柄コード抽出関数 extract_stock_codes（4桁数字のみを候補にし、known_codes によるフィルタリング）。
    - 統合収集ジョブ run_news_collection（複数ソースを独立ハンドリングし、個別エラーで他ソースに影響させない）。
  - デフォルト RSS ソースを設定（DEFAULT_RSS_SOURCES に Yahoo Finance のビジネスカテゴリ RSS を追加）。

- DuckDB スキーマ定義と初期化
  - schema モジュールを実装（src/kabusys/data/schema.py）。
  - 3 層（Raw / Processed / Feature）＋Execution 層にまたがるテーブル定義を提供:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成を行い、DuckDB 接続を返す。get_connection() で既存 DB へ接続。

- ETL パイプライン
  - pipeline モジュールを実装（src/kabusys/data/pipeline.py）。
  - 機能:
    - 差分更新のためのヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day)。
    - ETL 実行結果を格納する ETLResult dataclass（品質チェックやエラー情報を保持、辞書化可能）。
    - run_prices_etl の差分更新ロジック（最終取得日から backfill_days を遡って再取得、最小データ開始日を考慮）。
  - 設計方針:
    - 差分更新をデフォルトとし、backfill により API の後出し修正を吸収する。
    - 品質チェックは fail-fast とはせず、検出情報を呼び出し元へ戻す設計（quality モジュール想定）。

- モジュール骨組み
  - execution/strategy パッケージ初期化ファイル（空の __init__.py）を配置し拡張に備える。

### 変更
- （初回リリースのため履歴無し）

### 修正
- （初回リリースのため履歴無し）

### 既知の注意点 / マイグレーション
- このリリースは初期実装のため、運用前に以下を確認してください:
  - .env の自動読込はデフォルトで有効。テストや特別な実行では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
  - DuckDB スキーマ初期化は init_schema() を呼ぶことで行われます。既存 DB には get_connection() を使用してください。
  - J-Quants API の利用には JQUANTS_REFRESH_TOKEN（環境変数）が必須です。
  - news_collector は外部ネットワークへアクセスするため、実行環境のネットワーク制約やプロキシ環境に注意してください。

### セキュリティ関連
- XML パースに defusedxml を使用。
- RSS 取得時およびリダイレクト時に SSRF 対策（スキーム検証、プライベートアドレス拒否）を実装。
- レスポンスサイズ上限（10MB）と gzip 解凍後の検査によりメモリ DoS を軽減。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入。

### 貢献者
- 初期実装: 開発チーム（ソースコード内の docstring / 実装に基づく推測）

（今後のリリースでは Unreleased セクションを追加し、機能追加・変更・修正を記録してください。）