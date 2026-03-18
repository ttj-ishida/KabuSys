# Changelog

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠します。

## [Unreleased]
（未リリースの変更はここに記載）

## [0.1.0] - 2026-03-18
初期リリース。パッケージのコア機能（データ取得・保存、ファクター計算、ニュース収集、設定管理など）を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。バージョンを __version__ = "0.1.0" に設定し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。読み込み順は OS 環境 > .env.local > .env。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により CWD に依存しない自動ロードを実現。
  - .env パーサを実装：コメント行、export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの扱い等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。is_live / is_paper / is_dev といったユーティリティも追加。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
  - 再試行（指数バックオフ、最大 3 回）とステータス別の扱い（408/429/5xx のリトライ、429 の Retry-After 優先）。
  - 401 Unauthorized を検出した際はリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライするロジックを実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE により冪等性を確保。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値や欠損値へ安全に対処。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集・正規化・DB 保存の実装。
  - 安全対策：
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - SSRF 対策：取得前のホストチェック、リダイレクト時のスキーム／ホスト検証用ハンドラ、プライベート IP 判定。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - URL スキーム検証（http/https のみ許可）。
  - コンテンツ前処理（URL 除去・空白正規化）と URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去）を実装し、正規化 URL の SHA-256（先頭32文字）で記事 ID を生成して冪等性を保証。
  - fetch_rss：RSS を取得し NewsArticle 型のリストを返す（パース失敗はログ出力して空リスト返却）。
  - DB 保存関数（save_raw_news, save_news_symbols, 内部の _save_news_symbols_bulk）を実装。チャンク挿入、トランザクションまとめ、INSERT ... RETURNING による挿入件数の正確取得を行う。
  - 銘柄コード抽出ユーティリティ（extract_stock_codes）を実装（4桁数字にマッチし、known_codes でフィルタ）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema に基づく初期 DDL を追加（Raw Layer の raw_prices, raw_financials, raw_news などのテーブル定義を含む）。実装は CREATE TABLE IF NOT EXISTS ベースで初期化を想定。
  - （raw_executions の定義開始を含むが、ソースの一部は途中まで記載）

- 研究用モジュール（kabusys.research）
  - feature_exploration モジュール：
    - calc_forward_returns：基準日から指定ホライズンの将来リターンを DuckDB の prices_daily テーブルから一括取得。
    - calc_ic：ファクター値と将来リターンのスピアマンランク相関（IC）を計算（NaN/None と ties を考慮）。
    - rank：同順位は平均ランクとするランク付け関数（丸めにより浮動小数点の ties 判定漏れを低減）。
    - factor_summary：ファクター列ごとの基本統計量（count/mean/std/min/max/median）を算出。
  - factor_research モジュール：
    - calc_momentum：1M/3M/6M リターン、MA200 乖離率を計算（足りないデータは None）。
    - calc_volatility：20日 ATR、ATR 比率、20日平均売買代金、出来高比を計算（部分窓・欠損考慮）。
    - calc_value：raw_financials と当日の株価を結合して PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - 研究モジュールは DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番発注 API 等にはアクセスしない設計。

- パッケージ公開 API（kabusys.research.__init__）
  - 研究用の主要関数（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize（kabusys.data.stats から）を __all__ でエクスポート。

### 変更 (Changed)
- （該当なし：初回リリースのため過去変更は無し）

### 修正 (Fixed)
- （該当なし：初回リリース）

### セキュリティ (Security)
- news_collector にて SSRF、XML Bomb、Gzip Bomb、過大レスポンス対策を実装。
- J-Quants クライアントは認証トークンの自動リフレッシュとレート制御を備え、過剰な再試行やトークン漏れを抑制。

### 注意事項 / 備考
- DuckDB のテーブル名（prices_daily / raw_prices / raw_financials / raw_news 等）の存在を前提としています。スキーマ初期化（DDL 実行）を事前に行ってください。
- news_collector の extract_stock_codes は「4桁数字」を基準に抽出するため、記事文脈により誤検出や見逃しが発生する可能性があります。known_codes を適切に渡して運用してください。
- config の自動 .env ロードはプロジェクトルートの検出に依存します。テストなどで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

-----
（今後のリリースでは、strategy / execution / monitoring の具体実装、Feature Layer の永続化・更新ロジック、より高度なファクター正規化・バックテスト機能などを追加予定）