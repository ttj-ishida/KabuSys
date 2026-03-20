# Changelog

すべての変更は Keep a Changelog の方針に従い、意味のあるリリース単位でまとめています。  
バージョン番号は semantic versioning に準拠します。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しています。主にデータ取得・保存、研究用ファクター計算、特徴量合成、シグナル生成、設定管理、ニュース収集などを含みます。

### Added（追加）
- パッケージ基礎
  - パッケージ情報: kabusys.__version__ = "0.1.0"
  - パッケージ公開モジュール: data, strategy, execution, monitoring

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env 行パーサの実装（コメント対応、export プレフィックス、シングル/ダブルクォート、エスケープ処理）。
  - 環境変数の必須チェック utility (_require) と Settings クラスを提供。
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 可設定項目（デフォルト値あり）:
    - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (allowed: development, paper_trading, live; デフォルト: development)
    - LOG_LEVEL (allowed: DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)
  - テスト等で自動.envロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（ページネーション対応）。
  - レート制限管理（固定間隔スロットリング、120 req/min）。
  - リトライ（指数バックオフ、最大3回）と HTTP エラー処理（408/429/5xx）、429 の Retry-After 対応。
  - 401 発生時のトークン自動リフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
  - API: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB へ保存関数（冪等）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ: _to_float, _to_int（安全な変換ロジック）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集・正規化・冪等保存機能。
  - 記事ID生成は URL 正規化後の SHA-256 の先頭利用で冪等性を確保（トラッキングパラメータ削除、フラグメント除去、クエリソート）。
  - defusedxml による安全な XML パース、HTTP 受信サイズ上限（10MB）、SSRF 回避やトラッキングパラメータ除去などの安全対策。
  - デフォルト RSS ソースに Yahoo Finance ビジネス RSS を追加。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム: calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、データ不足時は None を返す。
  - ボラティリティ/流動性: calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）。
  - バリュー: calc_value（per, roe。raw_financials の最新レコードを使用）。
  - DuckDB の prices_daily / raw_financials テーブルを前提に SQL ベースで実装。

- 研究用解析ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算: calc_forward_returns（複数ホライズン対応、デフォルト [1,5,21]）。
  - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランク計算から求める）。
  - ランク関数: rank（同位は平均ランク、丸めで ties 検出を安定化）。
  - 統計サマリー: factor_summary（count, mean, std, min, max, median）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを統合して features テーブルへ保存する build_features 関数。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）。
  - 正規化: zscore_normalize を利用、対象列を ±3 でクリップ（_NORM_COLS）。
  - 冪等性: target_date ごとに DELETE→INSERT のトランザクションによる置換を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成する generate_signals。
  - デフォルト重みとしきい値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60。
  - AI news スコアはシグモイド変換、未登録は中立 0.5 で補完。
  - Bear レジーム判定: ai_scores の regime_score 平均が負値かつサンプル数 >= 3 の場合に BUY を抑制。
  - SELL 判定（エグジット）:
    - ストップロス: 終値/avg_price - 1 < -8%（優先）
    - スコア低下: final_score < threshold
    - （未実装だが設計書に記載）トレーリングストップや時間決済は今後対応予定。
  - 冪等性: signals テーブルへ日付単位で置換（トランザクション）。

- strategy パッケージ公開 API
  - build_features, generate_signals を __all__ にて公開。

### Changed（変更）
- （初回リリースのため該当なし）

### Fixed（修正）
- （初回リリースのため該当なし）

### Deprecated / Removed / Security
- （初回リリースのため該当なし）

---

## マイグレーション / 運用メモ（重要）
- 必要なデータベーステーブル（DuckDB / SQLite 等）:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, news_symbols などが想定されます。スキーマは実装に合わせて準備してください（各関数の INSERT/SELECT を参照）。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意・デフォルト有り: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化可能。
- トークン管理: J-Quants の ID トークンはモジュール内でキャッシュされ、自動リフレッシュ処理があります。get_id_token は明示的に呼べます。
- 冪等性: 多くの保存処理は ON CONFLICT DO UPDATE（または DELETE→INSERT のトランザクション）で実装されており、再実行に耐えます。
- 外部依存: research モジュールは可能な限り標準ライブラリと DuckDB のみで動作するよう設計されています（pandas 等の外部 lib に依存しない）。
- セキュリティ: news_collector は defusedxml を使用し、HTTP レスポンスサイズ制限や URL フィルタリングを実装しています。J-Quants クライアントはレート制限・リトライ・トークンリフレッシュを組み込み。

---

## 開発上の注意点 / 今後の予定（設計上の備考）
- feature_engineering と signal_generator はルックアヘッドバイアスを防ぐ設計で、target_date 時点のデータのみを使用します。
- 現状、positions テーブルに peak_price / entry_date 等が存在しないため、トレーリングストップや時間決済は未実装。これらを追加するとより高度なエグジットルールを導入可能です。
- news_collector の記事 ID は URL 正規化に依存するため、将来的に URL 正規化ロジックを変更する際は既存データとの互換性に注意が必要です。
- generate_signals の重みは外部から渡せますが、無効な値は警告を出して無視され、合計が 1.0 になるよう再スケールされます。

---

追記や質問があれば、どの機能について詳細な記述（想定される DB スキーマ、利用例、API 引数のサンプル、運用手順など）を作成するか指示してください。