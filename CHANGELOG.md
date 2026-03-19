# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。  

安定したバージョンリリースの直近日付はソースから推測した初回公開日（この CHANGELOG 作成日）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下は本リリースで追加された主要機能と設計上の注意点です。

### Added
- パッケージ構成
  - kabusys パッケージの提供（サブパッケージ: data, research, strategy, execution）。
  - execution パッケージはプレースホルダ（未実装の実行層）として追加。

- 設定管理（kabusys.config）
  - Settings クラスによる環境変数ラッパーを実装。
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml が基準）。
  - .env のパース実装（コメント、export フォーマット、クォート・エスケープ対応）。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数の必須チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルト値の提供:
    - KABUS_API_BASE_URL: "http://localhost:18080/kabusapi"（環境変数未設定時）
    - DUCKDB_PATH: "data/kabusys.duckdb"
    - SQLITE_PATH: "data/monitoring.db"
  - 環境（KABUSYS_ENV）のバリデーション（development / paper_trading / live）。
  - ログレベル（LOG_LEVEL）バリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レートリミッタ（固定間隔スロットリング、120 req/min を想定）。
  - 再試行（指数バックオフ、最大 3 回）と特定ステータスでのリトライロジック（408, 429, 5xx）。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - fetch_* 系関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes → raw_prices テーブルへの冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials テーブルへの冪等保存
    - save_market_calendar → market_calendar テーブルへの冪等保存
  - 入力変換ユーティリティ: _to_float, _to_int（安全な変換処理）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と記事正規化、raw_news への保存処理の設計と一部実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - HTTP/HTTPS スキームのみ受け付ける設計（SSRF 緩和を想定）。
  - 記事 ID の生成方針（URL 正規化後の SHA-256 ハッシュの先頭 32 文字を利用する方針を記載）。
  - バルク INSERT チャンク処理の設計（_INSERT_CHUNK_SIZE）。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム（calc_momentum）: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）
  - ボラティリティ・流動性（calc_volatility）: atr_20, atr_pct（ATR / close）, avg_turnover, volume_ratio
  - バリュー（calc_value）: per（株価 / EPS）, roe（raw_financials から最新財務を取得）
  - DuckDB を用いた SQL ベースの効率的な計算実装（窓関数利用）
  - データ不足時の None 処理を明確化

- 研究用解析ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力バリデーション）
  - IC（Information Coefficient）計算（calc_ic、Spearman のランク相関）
  - ランク変換ユーティリティ（rank、同順位は平均ランクで処理）
  - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールから生ファクター取得（momentum/volatility/value）
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位の置換（DELETE + INSERT、トランザクションで原子性保証）
    - 冪等性（同一 target_date を再実行しても差し戻し可能）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）計算
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - デフォルト重み（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）
    - ユーザ指定 weights の検証・補完・再スケーリング処理（未知キー・負値・非数は無視）
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、かつサンプル数閾値以上）
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄に BUY、Bear 時は BUY 抑制
    - エグジット（SELL）判定:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が threshold 未満
      - positions テーブルの価格欠損時や features 未登録時の扱いを明確化（ログ出力）
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）
    - ログ出力（INFO/DEBUG）による処理可視化

- ロギング
  - 各モジュールに logger を配置し、重要な分岐・警告を出力するよう実装。

### Security
- RSS の XML パースに defusedxml を使用して XML 攻撃を緩和。
- ニュース収集において受信バイト数上限を設定し、メモリ DoS を軽減。
- ニュース中の URL 正規化でトラッキングパラメータを除去し、記事 ID を生成して冪等性を担保。
- news_collector におけるスキームチェックや IP 判定等の設計（SSRF 緩和方針）を反映。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Known limitations / Notes
- execution 層（実際の注文発行ロジック）は実装済みではなく、strategy 層は発注 API に直接依存しない設計。
- signal_generator 内で言及されている未実装のエグジット条件:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有日数に基づくエグジット）
- news_collector の全 RSS パース/収集ループは方針と一部ユーティリティを実装済みだが、外部接続周りの実装詳細（ネットワーク取得等）は環境依存。
- DuckDB テーブルスキーマ（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals 等）は本実装が期待する形で存在する必要があります。初期化スクリプトやマイグレーションは別途用意してください。
- 一部入力データの検証（例: 財務データの period_type 等）は簡易実装に留めています。

### Migration / Configuration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 用リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用、必須）
- 任意/デフォルト:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL（デフォルト: INFO）
- テスト/CI で自動環境読み込みを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

参考: パッケージバージョンは kabusys.__version__ = "0.1.0" に合わせています。

（本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして公開する場合は、リリース時の変更差分・日付・著者情報等を正確な運用フローに合わせて更新してください。）