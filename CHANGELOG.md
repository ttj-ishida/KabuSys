# Changelog

すべての注目すべき変更を一元的に記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新版: 0.1.0 (初回公開)

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ = 0.1.0 を定義し、公開 API として data / strategy / execution / monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装。
  - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD に依存しない自動読み込みを実現。
  - .env のパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 読み込み順: OS 環境 > .env.local > .env。テストなどで自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - settings オブジェクトを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須設定取得ユーティリティ）。
  - KABUSYS_ENV（development / paper_trading / live）の検証、LOG_LEVEL の検証、および is_live/is_paper/is_dev ヘルパー。

- データ収集 / 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
  - レート制限（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
  - 再試行（指数バックオフ）および HTTP ステータスに応じたリトライ処理（408/429/5xx）。429 の場合は Retry-After を優先。
  - 401 Unauthorized 受信時に自動でリフレッシュトークンから id_token を取得して 1 回リトライする仕組み。
  - ページネーション対応のデータ取得ユーティリティ:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ保存する冪等性のある保存関数:
    - save_daily_quotes（raw_prices へ、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials へ、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar へ、ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ（_to_float / _to_int）を提供し、安全に型変換を行う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集パイプラインを実装（DEFAULT_RSS_SOURCES を含む）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクト先のスキーム/ホスト検証、プライベート IP 判定、リダイレクトハンドラによる事前検査。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES、10MB）と Gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、_make_article_id により記事IDを SHA-256 の先頭32文字で生成）。
  - テキスト前処理（URL 除去、空白正規化）。
  - RSS 取得と記事抽出（content:encoded 優先、pubDate のパース、fallback ロジック）。
  - DuckDB への冪等保存:
    - save_raw_news（チャンク挿入、INSERT ... RETURNING id を使い新規挿入 ID を返す、トランザクション管理）
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄コードの紐付けをチャンク挿入、ON CONFLICT DO NOTHING、RETURNING 利用）
  - 銘柄抽出機能（extract_stock_codes）: 正規表現で 4 桁銘柄コードを抽出し、既知銘柄セットでフィルタリング。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日からの将来リターン（複数ホライズン）を DuckDB の prices_daily を参照して計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（ties・ランク平均処理あり）。
    - rank: 同順位を平均ランクにするランク変換ユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率 ma200_dev を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: raw_financials と当日の株価を組み合わせて PER / ROE を算出。直近報告の財務情報取得ロジックを含む。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照し、実取引 API へのアクセスは行わない設計。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL を実装（Raw / Processed / Feature / Execution 層に関する設計）。
  - raw_prices, raw_financials, raw_news, raw_executions（定義の一部）などのテーブル定義を含む。

- 研究 API エクスポート
  - kabusys.research パッケージで zscore_normalize（data.stats 由来）や各種ファクター関数を __all__ にて公開。

### 修正 (Changed)
- （初回リリースにあたっての内部設計上の選択を注記）
  - DuckDB へは冪等性を意識した INSERT / ON CONFLICT を多用し、外部データの再取得や重複挿入に耐える設計。
  - API リトライ・レート制御はサーバ側のレート制限を踏まえて固定スロットリングを採用。

### セキュリティ (Security)
- news_collector:
  - defusedxml による安全な XML パース。
  - SSRF 対策（リダイレクト前後の検査、プライベート IP 拒否）。
  - レスポンスサイズ制限・Gzip 解凍後検査によりメモリ DoS・Gzip bomb を防止。
- jquants_client:
  - 認証トークン管理で refresh フローを組み込み、不正な連鎖リフレッシュを防止。

### 既知の制約 / 注意点 (Notes)
- .env 自動ロードはプロジェクトルート検出に成功した場合のみ行われ、見つからない場合はスキップされる。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
- news_collector の URL 検査で DNS 解決に失敗した場合は安全側（非プライベート）とみなしてアクセスを許可する実装になっている（運用上のポリシーに応じて変更推奨）。
- calc_forward_returns / factor 計算は営業日数（連続レコード数）ベースのホライズンを想定しており、カレンダー日と混同しないこと。
- 一部ファイル（schema 内 raw_executions など）は DDL 定義の途中で切れているため、実際のスキーマを確定する際は完全な DDL を確認すること。

---

今後の予定:
- processed / feature 層の変換パイプライン実装（raw → processed → features）。
- strategy / execution 層の発注ロジック・kabuステーション連携実装。
- 単体テスト・統合テストの追加（外部 API のモック化を含む）。

もし CHANGELOG に追加したい詳細（リリース日付の変更、追加の機能や既知バグの追記など）があれば教えてください。