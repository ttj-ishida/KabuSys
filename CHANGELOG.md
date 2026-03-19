CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- （無し）

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージのトップレベル (src/kabusys/__init__.py) に __version__ と __all__ を定義。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
  - .env のパースロジックを独自実装（コメント・クォート・export 構文対応、エスケープ処理等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等で利用可能）。
  - 必須設定取得時の検証メソッド（_require）と Settings クラスを提供。
  - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト有）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL（値検証）。
  - is_live / is_paper / is_dev のユーティリティプロパティを提供。
- データ取得・保存: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API への HTTP クライアントを実装（ページネーション対応）。
  - レートリミッタ（固定間隔スロットリング、120 req/min）実装。
  - リトライ（指数バックオフ、最大3回）・429/408/5xx の再試行処理。
  - 401 受信時はリフレッシュトークンで自動トークン更新を行い1回リトライする実装。
  - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT による upsert）。
  - 入出力の型変換ユーティリティ (_to_float / _to_int) を実装。
  - 取得時刻 (fetched_at) を UTC ISO8601 で記録し、look-ahead bias のトレースを可能に。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news へ冪等保存するロジック。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
  - XML パースに defusedxml を利用し XML Bomb 等の対策を実施。
  - 受信バイト上限（10MB）や SSRF 対策（http/https のみ）などセキュリティ・耐障害面の配慮を記述。
  - デフォルト RSS ソースとして Yahoo Finance Business を定義。
- リサーチ用モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離率）
    - Volatility（20日 ATR、ATR / close、20日平均売買代金、出来高比率）
    - Value（PER、ROE の取得。raw_financials と prices_daily を結合）
    - DuckDB SQL を中心に実装し、結果を (date, code) 辞書リストで返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応・入力検証）
    - IC（Spearman の ρ）計算 calc_ic（結合・欠損除外・最小サンプル検査）
    - 基本統計量出力 factor_summary（count/mean/std/min/max/median）
    - ランク計算ユーティリティ rank（同順位は平均ランク、丸め処理で ties 検出）
  - research パッケージの __all__ に主要関数を公開。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで算出した raw factor を統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
  - 正規化（zscore_normalize を利用）→ ±3 でクリップ → features テーブルへ日付単位の置換（トランザクション化、冪等）を実装。
  - 実装によりルックアヘッドバイアスを防止（target_date 時点のみ利用）。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
  - 各コンポーネントの変換ロジック（シグモイド、PER の逆数スケーリング、ボラティリティ反転等）を実装。
  - 重み付け合算による final_score 計算（デフォルト重みを定義、ユーザ指定 weights の検証と正規化対応）。
  - Bear レジーム検出（ai_scores の regime_score 平均が負 → BUY 抑制。サンプル数閾値あり）。
  - BUY シグナル判定（threshold デフォルト 0.60、ランク付け）と SELL（エグジット）判定を実装。
  - SELL 判定ではストップロス（終値/avg_price -1 < -8%）を最優先、score低下での売り判定も実装。
  - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入、冪等）を実行。
- strategy パッケージの __all__ に build_features / generate_signals を公開。
- 実装方針・運用上の配慮をコード内ドキュメントとして多数追加
  - look-ahead bias 回避、冪等性、トランザクション性、ログ出力方針、性能上の工夫（スキャン範囲限定・バルク挿入チャンク等）。

Changed
- （初回リリースのため該当無し）

Fixed
- （初回リリースのため該当無し）

Security
- ニュースパーサで defusedxml を採用、HTTP スキームの制限、受信バイト数制限など複数の入力検証／安全対策を導入。

Known issues / Notes
- _generate_sell_signals 内でトレーリングストップや保有期間に基づく時間決済など、一部エグジット条件は未実装（コメントで TODO 記載）。positions テーブルに peak_price / entry_date 等が必要。
- data.stats の zscore_normalize 実装ファイルはこの差分に含まれていないが、strategy モジュールから利用する前提で記述がある点に注意。
- 実運用前に以下を確認推奨:
  - 環境変数（JQUANTS_REFRESH_TOKEN 等）の設定
  - DuckDB / テーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar 等）の用意
  - J-Quants API 利用時のレート制御方針（環境による追加調整が必要な場合あり）
- 単体テスト・統合テストは別途必要（自動ロード機能は KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。

Acknowledgements
- 初期設計では「StrategyModel.md」「DataPlatform.md」等の設計ドキュメントセクションを参照した実装方針を多数反映。ドキュメントがある場合は併せて参照してください。