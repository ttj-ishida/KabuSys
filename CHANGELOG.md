# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

<!-- ToC -->
- [0.1.0 - 2026-03-20](#010---2026-03-20)
  - [Added](#added)
  - [Security](#security)
  - [Behavior / 実装詳細](#behavior--実装詳細)
  - [Known limitations / 未実装・注意点](#known-limitations--未実装・注意点)
  - [Migration / 導入メモ](#migration--導入メモ)

---

## 0.1.0 - 2026-03-20

初回リリース。日本株自動売買システムのコアライブラリを実装しました。以下はコードベースから推測してまとめた変更点・機能一覧です。

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - export されたサブパッケージ: data, strategy, execution, monitoring（execution は現状プレースホルダ）。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装。読み込み順は OS 環境 > .env.local > .env。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 柔軟な .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ対応。
  - settings オブジェクトを提供し、必要な環境変数をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション/デフォルト: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
  - 未設定の必須値取得時に ValueError を送出する _require 実装。

- Data 層（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しユーティリティを実装（ページネーション対応）。
    - RateLimiter による固定間隔スロットリング（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx/ネットワークエラー をリトライ対象）。
    - 401 発生時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュ。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への冪等保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換・不正値は None）。
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード取得と raw_news への冪等保存の実装設計。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、スキーム/ホスト小文字化、フラグメント削除）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、記事ID は正規化 URL の SHA-256 ハッシュ先頭を利用。
    - defusedxml を使った XML の安全パース等、セキュリティ対策を考慮。

- Research / ファクター計算（src/kabusys/research/）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム: calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - ボラティリティ/流動性: calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー: calc_value（per, roe。raw_financials から最新の財務データ参照）
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースの窓計算を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランク法で実装）
    - factor_summary, rank ユーティリティ（統計量 / 平均ランク処理）
  - 研究ユーティリティの公開（src/kabusys/research/__init__.py）。

- Strategy 層（src/kabusys/strategy/）
  - 特徴量作成（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した生ファクターを結合して正規化（zscore_normalize を利用）、Z スコアを ±3 でクリップ、features テーブルへ日付単位で UPSERT（トランザクションで原子性確保）。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。合計が 1.0 でない場合再スケール。
    - default BUY threshold = 0.60。
    - final_score の算出、Bear レジーム判定（AI レジームスコア平均 < 0 を Bear と判定、サンプル閾値あり）、Bear 時は BUY を抑制。
    - SELL 条件（ストップロス -8% または final_score < threshold）を実装。positions テーブルと最新価格を参照。
    - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
  - strategy パブリック API をエクスポート（build_features / generate_signals）。

### Security
- news_collector:
  - defusedxml を使用して XML 関連の攻撃（XML Bomb 等）を緩和。
  - 受信サイズ上限（10 MB）を設け、メモリ DoS を抑止。
  - URL 正規化とトラッキングパラメータ削除により ID の安定化を実現。
  - HTTP スキーム以外の URL を排除する想定（実装目標）。
- jquants_client:
  - API リクエストでのトークン自動リフレッシュは allow_refresh フラグで制御し、無限再帰を防止。
  - レート制限・リトライで外部 API への過負荷や誤動作を軽減。

### Behavior / 実装詳細（重要な仕様）
- 環境変数自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を探索。
  - OS 環境変数は保護され、.env の上書きからは除外（.env.local は override=True で上書き可能だが OS 環境は保護）。
  - .env 行のパースはコメント／クォート／エスケープを考慮。
- J-Quants API:
  - Rate limit: 120 req/min を _RateLimiter で遵守（固定間隔スロットリング）。
  - 最大リトライ回数: 3、指数バックオフ（base=2 秒）。429 の場合は Retry-After 優先。
  - ページネーション対応: pagination_key を使ってページング。
  - 保存処理は冪等（ON CONFLICT DO UPDATE）で raw_* テーブルに保存。
- Strategy:
  - features の数値列は Z スコア正規化（外れ値は ±3 でクリップ）。
  - ユニバースフィルタ: close >= 300 円、20 日平均売買代金 >= 5e8 円。
  - final_score のコンポーネント欠損は中立 0.5 で補完。
  - BUY シグナルは threshold 超、Bear レジームの場合 BUY を抑制。
  - SELL はストップロス優先（-8% 以下で即 SELL）、続いてスコア低下。
  - SELL 優先ポリシー: SELL 判定された銘柄は BUY リストから除外し、BUY ランクを再付番。

### Known limitations / 未実装・注意点
- execution パッケージは空のプレースホルダ（発注層の実装は含まれない）。
- signal_generator の SELL 判定で未実装の条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数によるクローズ）
- calc_value は PER / ROE のみを実装。PBR・配当利回り等は未実装。
- news_collector は記事と銘柄紐付け（news_symbols）などの実装方針は記述されているが、完全な紐付けロジックはコード断片からは不明（実装の有無に注意）。
- 各種 SQL テーブルのスキーマ定義はソースに含まれていないため、DB 準備（tables の作成）は利用者が用意する必要あり。想定される主なテーブル:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, positions, raw_news
- settings._require は未設定時に ValueError を投げるため、実行前に必須環境変数を準備してください。

### Migration / 導入メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意・デフォルト:
  - KABUSYS_ENV ∈ {development, paper_trading, live}（デフォルト development）
  - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）
  - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH / SQLITE_PATH（デフォルトを使用可）
- .env 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB のテーブルを事前に作成してください（raw_prices/raw_financials/prices_daily/features/ai_scores/signals/positions 等）。各関数はこれらの存在を前提とします。
- J-Quants API 呼び出し時のレート制限（120 req/min）を超えないよう注意。fetch_* 系は内部でページング・リトライを行います。
- ニュース収集を行う際は defusedxml と受信サイズ制限の動作に留意してください。

---

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートとして利用する際は、運用上重要な差分（DB スキーマ、外部設定、追加の依存パッケージ、既知のバグ修正など）を開発チームの確認の上で追記してください。