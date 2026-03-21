# CHANGELOG

すべての notable な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
初期バージョンは 0.1.0 です。

## [Unreleased]

## [0.1.0] - 2026-03-21

### Added
- 初期リリース: KabuSys — 日本株自動売買システムのコアライブラリを実装。
- パッケージメタ:
  - パッケージ記述子とエクスポート: `kabusys.__version__ = "0.1.0"`, `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- 環境設定:
  - `kabusys.config.Settings` を追加。環境変数から設定を取得するプロパティを提供（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`）。
  - 自動 .env ロード機構を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を起点に探索）。優先順位: OS 環境変数 > .env.local > .env。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは `export KEY=val` 形式、引用符付き値（バックスラッシュエスケープ対応）、インラインコメントの扱い（クォートの有無による挙動差）に対応。環境変数上書き時の保護キーセットを考慮。
  - デフォルト値: `KABUSYS_ENV=development`、`LOG_LEVEL=INFO`、データベースパスのデフォルト (`DUCKDB_PATH="data/kabusys.duckdb"`, `SQLITE_PATH="data/monitoring.db"`) を実装。`KABUSYS_ENV` と `LOG_LEVEL` は妥当性検証を行う。
- データ収集 (data):
  - J-Quants API クライアント (`kabusys.data.jquants_client`) を実装。
    - 固定間隔レートリミッタ（120 req/min）とモジュールレベルのトークンキャッシュ。
    - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の `Retry-After` を尊重。
    - 401 受信時はリフレッシュトークンを使って id_token を自動更新して 1 回リトライする仕組み。
    - ページネーション対応の fetch 関数: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
    - DuckDB へ冪等に保存する save 関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（ON CONFLICT DO UPDATE を使用）。
    - 入力パースユーティリティ: `_to_float`, `_to_int`（型安全な変換ルールを定義）。
  - ニュース収集モジュール (`kabusys.data.news_collector`) を実装（RSS ベース）。
    - RSS 取得・パース、URL 正規化（トラッキングパラメータ削除、フラグメント除去、キーソート）、記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）。
    - defusedxml を利用して XML 攻撃対策、受信最大バイト数制限（10MB）や SSRF 防止を考慮した実装。
    - バルク挿入のチャンク分割、ON CONFLICT DO NOTHING による冪等保存と挿入数の正確な返却。
- 研究モジュール (research):
  - ファクター計算 (`kabusys.research.factor_research`) を実装。
    - Momentum: `calc_momentum`（mom_1m / mom_3m / mom_6m / ma200_dev、200 日移動平均の存在チェック）。
    - Volatility/Liquidity: `calc_volatility`（ATR20、atr_pct、avg_turnover、volume_ratio、true_range の NULL 処理）。
    - Value: `calc_value`（raw_financials から最新財務を取得して PER / ROE を計算）。
  - 探索・評価ユーティリティ (`kabusys.research.feature_exploration`) を実装。
    - 将来リターン計算: `calc_forward_returns`（複数ホライズン対応、クエリ効率化のためカレンダー日バッファ）。
    - IC (Spearman rank correlation) 計算: `calc_ic`（rank/同順位の平均ランク対応、最小サンプルチェック）。
    - 基本統計量集計: `factor_summary`（count/mean/std/min/max/median）。
    - ランキング補助: `rank`（丸めを入れて ties を正しく扱う実装）。
  - 研究側の関数群を `kabusys.research.__all__` に公開。
- 戦略モジュール (strategy):
  - 特徴量生成 (`kabusys.strategy.feature_engineering.build_features`) を実装。
    - 研究モジュールの生ファクターを統合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（外部ユーティリティ `kabusys.data.stats.zscore_normalize` を使用）、±3 でクリップ、日付単位で UPSERT（DELETE then INSERT within transaction）して冪等性を保証。
    - prices_daily の最新価格取得は target_date 以前の最新レコードを参照（ルックアヘッド回避）。
  - シグナル生成 (`kabusys.strategy.signal_generator.generate_signals`) を実装。
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で `final_score` を算出（デフォルト重みを定義）。
    - 重みのバリデーション・補完・再スケーリングを実装（不正な値はログ警告して無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数 >= 最小値で判定）により BUY シグナル抑制。
    - BUY 判定（デフォルト閾値 0.60）と SELL（ストップロス -8% / スコア低下）を生成。SELL は BUY より優先し、INSERT は日付単位で置換トランザクションとして行う。
    - 一部未実装のエグジット条件（トレーリングストップ / 時間決済）はコメントとして明示。
- DB トランザクション安全性:
  - 主要な書き込み処理（features, signals, raw tables 等）はトランザクションとバルク操作で原子性を確保し、例外発生時には ROLLBACK を試行してログ警告。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- RSS パーシングに defusedxml を利用し XML 攻撃に対処。
- ニュース URL 正規化と受信サイズの制限により SSRF / メモリ DoS のリスクを低減。

### Documentation / Notes
- .env パーサーの挙動や環境変数名の例は docstring と設定クラスに記載。必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB / raw テーブル設計（テーブル名: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals など）を前提とした実装。
- Python バージョン: 型注釈で `X | Y` を使用しているため Python 3.10+ を想定。
- 外部依存: duckdb, defusedxml（インストールが必要）。

### Breaking Changes
- 初回リリースのため破壊的変更はなし。

---

今後のリリースでは以下を検討:
- execution 層（発注 API 統合）と monitoring の実装。
- トレーリングストップ / 時間決済など追加のエグジット条件の実装。
- AI スコア取得パイプライン・news→ai_scores 連携機能の追加。
- 単体テストと統合テストの整備（外部 API はモック化してテスト可能にする）。