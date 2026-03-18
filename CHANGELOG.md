# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日付はパッケージ版の初回公開（スナップショット）の日付として本日を使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。本バージョンでは日本株自動売買システムの骨格およびデータ取得・前処理・研究用ユーティリティを実装しています。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0 に設定。
  - __all__ に data / strategy / execution / monitoring を公開。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込み順序、.env.local が上書きする挙動を実装。
  - export KEY=val 形式やクォート／コメントの扱いを考慮したパーサを実装。
  - 必須変数未設定時に ValueError を投げる _require() を提供。
  - 環境 (development / paper_trading / live) や LOG_LEVEL 等の検証ロジックを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - API レート制御（120 req/min）のための固定間隔レートリミッタを導入。
  - リトライ（指数バックオフ）、429 の Retry-After の尊重、408/429/5xx の再試行ロジックを実装。
  - 401 の自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュを実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を追加。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
  - 安全な型変換ユーティリティ _to_float / _to_int を実装。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS からのニュース収集、前処理、DuckDB への保存ワークフローを実装。
  - RSS の取得（fetch_rss）で以下の安全対策を実施:
    - スキーム検証（http/https のみ）
    - SSRF 対策（リダイレクト先のスキーム/プライベートアドレス検査）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）チェック、gzip 解凍後の再検査（Gzip bomb 対策）
    - defusedxml による XML パースの安全化
  - URL 正規化（トラッキングパラメータ除去）、SHA-256 による記事 ID 生成を実装（先頭32文字）。
  - テキスト前処理（URL除去・空白正規化）。
  - raw_news へ冪等保存する save_raw_news（チャンク/トランザクション/INSERT ... RETURNING）を実装。
  - news_symbols への紐付け処理および一括保存ユーティリティ _save_news_symbols_bulk を実装。
  - 記事本文から銘柄コード（4桁）抽出する extract_stock_codes を実装。
  - run_news_collection により複数ソース一括収集と紐付けを実行可能。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution 層の構想）。
  - raw_prices / raw_financials / raw_news 等のDDL 定義を追加（初期化用モジュール）。
  - （raw_executions テーブル定義の一部が含まれている）

- 研究用ユーティリティ (src/kabusys/research/*.py)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から複数ホライズン先の将来リターンを DuckDB の prices_daily テーブルから計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ欠損や ties に配慮。
    - rank / factor_summary: ランク付け（平均ランクで同順位処理）と基本統計量サマリーを標準ライブラリのみで実装。
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を prices_daily から計算。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率を計算（true_range の NULL 伝播を考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新財務レコードの取り方に注意）。
  - research パッケージ __init__ で主要関数をエクスポート。

### 修正 (Changed)
- 初回リリースのため該当なし（初期実装）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector において SSRF の軽減、XML パースの安全化（defusedxml）、レスポンスサイズ制限、gzip 解凍後の再チェック等の対策を追加。

### 既知の注意点 / マイグレーションノート
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が Settings により必須とされています。未設定の場合アプリケーションは ValueError を送出します。
- 自動 .env ロード:
  - パッケージは起点ファイルからプロジェクトルートを検出し .env / .env.local を自動で読み込みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB 依存:
  - 多数の関数が duckdb.DuckDBPyConnection を受け取って動作します。実行前に適切な DB とテーブルを schema モジュールの DDL に従って初期化する必要があります。
- 外部ライブラリ:
  - defusedxml を利用しています。RSS 周りの安全処理のためにインストールが必要です。
- Look-ahead bias:
  - jquants_client は fetched_at を UTC で記録する設計になっており、将来の情報漏洩（Look-ahead bias）を最小限にする配慮をしています。
- パフォーマンス・安定性:
  - 一部関数は大規模データセットを想定したチャンク処理／ウィンドウ関数／単一クエリ設計を採用していますが、実運用では DuckDB の設定やハードウェアに依存するためチューニングが必要です。

もしリリースノートに追記したい具体的な変更や、日付の修正、あるいは別バージョン（Unreleased）向けの差分を反映したい場合は、その内容を教えてください。