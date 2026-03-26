CHANGELOG
=========
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

Unreleased
----------

- （現在差分なし）

0.1.0 — 2026-03-26
------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン __version__ = "0.1.0"、公開 API の __all__ を定義。

  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env / .env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml から探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
      - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォートとエスケープ処理、コメント扱いの挙動制御）。
      - OS 環境変数を保護する protected キーセットに基づく上書き制御（.env.local は .env を上書き）。
      - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / ログレベル / 環境（development/paper_trading/live）等の取得・バリデーションを実施。
      - 必須環境変数未設定時に ValueError を送出する _require ヘルパー。

  - ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・リスク調整）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順・タイブレークで並べ最大保有数で切り取り。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア比率で配分、全スコアが 0 の場合は等配分へフォールバック（警告ログ）。

    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限(max_sector_pct)チェック。既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。sell_candidates（当日売却予定）をエクスポージャー計算から除外可能。
      - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に応じた投下資金乗数（1.0/0.7/0.3）。未知レジームは 1.0 でフォールバック（警告ログ）。

    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method に基づき発注株数を算出（"risk_based", "equal", "score" を想定）。
      - risk_based: 許容リスク率と stop_loss_pct から目標株数を算出、単元(lot_size)で丸め。
      - equal/score: 重みと max_utilization を用いて各銘柄割り当てを算出、単元丸め、1 銘柄上限（max_position_pct）チェック。
      - aggregate cap: 合計投資額が available_cash を超える場合にスケールダウン。cost_buffer を加味して保守的に見積もり、スケール時の端数処理では lot_size 単位で残差の大きい銘柄から再配分するロジックを実装。

  - 戦略（特徴量構築・シグナル生成）
    - src/kabusys/strategy/feature_engineering.py
      - build_features: research モジュールから生ファクターを取得（calc_momentum / calc_volatility / calc_value）、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（zscore_normalize 使用）、±3 でクリップ、DuckDB の features テーブルへ日付単位でアップサート（BEGIN/COMMIT/ROLLBACK で原子性確保）。DuckDB 接続を引数に取り DB 以外に依存しない実装。

    - src/kabusys/strategy/signal_generator.py
      - generate_signals: features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントスコアを計算して final_score を算出（既定の重みを持つ、ユーザ指定の重みは検証・正規化）。Bear レジーム時の BUY 抑制、BUY/SELL のルール（スコア閾値、ストップロス等）を適用し signals テーブルへ日付単位で置換書き込み。SELL 優先ポリシー（SELL 対象は BUY から除外）を実装。AI ニューススコア未登録時は中立で補完。各種ログ出力・警告を実装。

  - Research（ファクター計算・解析ユーティリティ）
    - src/kabusys/research/factor_research.py
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算（必要なヒストリ範囲を考慮）。
      - calc_volatility: ATR(20)/atr_pct、平均売買代金、volume_ratio を計算。true_range の NULL 伝播を明示的に扱う。
      - calc_value: raw_financials から最新財務を取得し PER/ROE を計算（EPS=0 の処理）。
      - DuckDB を用いた SQL ベース実装で prices_daily / raw_financials のみ参照。

    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 任意ホライズン(デフォルト [1,5,21]) の将来リターンを一括取得。
      - calc_ic: Spearman ランク相関(IC)を計算（結合・欠損除外・最小サンプルチェック）。
      - factor_summary, rank: 基本統計量算出・ランク化ユーティリティ。

    - src/kabusys/research/__init__.py: 上記 API をパッケージ公開。

  - バックテスト（シミュレータ・メトリクス）
    - src/kabusys/backtest/simulator.py
      - DailySnapshot, TradeRecord データクラス。
      - PortfolioSimulator: メモリ内でのポートフォリオ管理と擬似約定処理を実装。execute_orders は SELL を先に処理し全量クローズ、BUY は単元/スリッページ/手数料/lot_size を考慮して約定（スリッページは BUY=+、SELL=-）。DB 参照無しで純粋な状態管理。

    - src/kabusys/backtest/metrics.py
      - BacktestMetrics データクラスと calc_metrics。CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades の算出ロジックを実装（日次スナップショットとトレードレコードのみを入力とする）。

  - モジュールのエクスポート整理
    - portfolio、strategy、research 等の __init__.py で主要関数を公開（パッケージ API を整理）。

Notes / Implementation details
- DuckDB を用いるコンポーネントは外部 DB 接続（DuckDBPyConnection）を引数に取り、DB スキーマとして prices_daily / features / ai_scores / raw_financials / positions / signals などを想定。
- 多くの関数は「純粋関数」または DB 接続を引数に取る形で設計されており、本番の発注 API や外部サービスへの直接アクセスは持たない（テスト容易性重視）。
- ロギングを各所に配置し、異常値・欠損・フォールバック時に警告/情報を出力。
- 現時点で未実装（TODO）事項や将来の拡張点：
  - position_sizing: 銘柄別 lot_size 対応（現在は単一 lot_size 引数で共通扱い）。
  - risk_adjustment の価格欠損時のフォールバック（前日終値・取得原価等）。
  - signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等が必要で未実装。
  - simulator の一部挙動（部分利確等）は未対応。

Security
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）