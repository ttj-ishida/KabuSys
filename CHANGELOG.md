# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
初期リリースの内容は、配布されたコードベースから推測して記載しています。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース。
- 基本パッケージ構成
  - kabusys モジュールの公開 API: data, strategy, execution, monitoring をエクスポート。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env/.env.local の読み込み順序および OS 環境変数保護（既存キーの保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env パースの堅牢化（コメント、export プレフィックス、クォートおよびエスケープ処理のサポート）。
  - Settings クラスで必要環境変数の取得ラッパーを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 設定値バリデーション（KABUSYS_ENV の許容値: development/paper_trading/live、LOG_LEVEL の許容値）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。主な機能:
    - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得関数（ページネーション対応）。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）、特定ステータス（408, 429, 5xx）でのリトライ処理。
    - 401 を受信した場合の ID トークン自動リフレッシュを 1 回実施してリトライ。
    - 取得時刻（fetched_at）を UTC で記録して look-ahead バイアスの追跡を容易化。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT による冪等保存（重複行は更新）。
    - 値変換ユーティリティ (_to_float, _to_int) を実装し不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集用基盤を追加。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除、小文字化など）。
  - defusedxml による安全な XML パース（XML Bomb などの対策）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、HTTP スキーム検証、SSRF 対策に配慮。
  - DB 側は raw_news / news_symbols への冪等保存を想定（INSERT バルクのチャンク化等で実装を想定）。

- 研究用モジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率。
    - calc_volatility: 20 日 ATR・相対 ATR、平均売買代金、出来高比などの流動性指標。
    - calc_value: PER / ROE の算出（raw_financials と prices_daily を組み合わせ）。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト: 1/5/21 営業日）での将来リターンを計算。
    - calc_ic: スピアマン rank 相関（IC）を計算。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティ。
  - 外部依存を最小化し、DuckDB を用いた SQL/純 Python 実装。

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research で計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（トランザクション + バルク挿入で冪等性を保証）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントはシグモイド・平均・補完（欠損は中立 0.5）などで処理。デフォルト重みはモデル定義に基づく。
    - 重みのバリデーション・リスケーリング、閾値（デフォルト 0.60）による BUY シグナル生成。
    - Bear レジーム判定（ai_scores の regime_score の平均が負でサンプル数閾値を満たす場合 BUY を抑制）。
    - エグジット（SELL）条件: ストップロス（終値が avg_price に対して -8% 以下）、final_score が閾値未満。
    - signals テーブルへ日付単位の置換（冪等性）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外し、ランクを再付与）。

- 内部ユーティリティ
  - レートリミッタ、HTTP リクエスト共通処理、トークンキャッシュなど。

### Changed
- （初版のため特に変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- news_collector において defusedxml を利用し XML パースの安全性を考慮。
- RSS/HTTP 取得で受信サイズを制限して DoS 対策。
- J-Quants クライアントは Authorization ヘッダを使用、トークン自動更新の処理を実装。

### Notes / Known limitations
- positions テーブルに peak_price / entry_date 等が未整備なため、signal_generator に記載されているトレーリングストップや時間決済（保有 60 営業日超過）は未実装。将来的な拡張で対応予定。
- news_collector のドキュメントには銘柄紐付け（news_symbols）に言及があるが、コードの一部は省略されており完全実装は要確認。
- 一部の機能は DuckDB の特定のテーブルスキーマ（raw_prices, raw_financials, prices_daily, market_calendar, features, ai_scores, positions, signals, raw_news など）を前提としているため、導入時はスキーマ整備が必要。
- J-Quants API とのやり取りはネットワーク/認証に依存するため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD やモックを利用することを推奨。

### Migration / Setup notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- オプション環境変数:
  - KABUSYS_ENV (development / paper_trading / live, デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)
- 必要な DB テーブル（検証・マイグレーションが必要）:
  - raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
  - raw_financials (code, report_date, period_type, eps, roe, fetched_at, ...)
  - market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
  - prices_daily, features, ai_scores, positions, signals, raw_news 等（コード内クエリ参照）

---

（将来的に変更があった場合は Unreleased セクションを使って追記し、リリース時にバージョン／日付を追加してください。）