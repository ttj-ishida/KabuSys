CHANGELOG
=========

この変更履歴は Keep a Changelog のフォーマットに準拠しています。  
（コードベースの内容から推測して作成しています）

Unreleased
----------

- なし

0.1.0 - 初回リリース
--------------------

Added
- パッケージ構成
  - kabusys パッケージの初版（__version__ = "0.1.0"）。
  - data / strategy / execution / monitoring を公開 API としてエクスポート。

- 環境設定読み込み（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パーサ実装（export 形式・クォート・エスケープ・インラインコメントの扱いを考慮）。
  - OS 環境変数を保護する protected 機構（.env.local は .env を上書き可能だが OS 環境は保護）。
  - Settings クラスによる設定ラッパーを提供（必須トークン取得時は未設定で ValueError を送出）。
  - デフォルト値と検証:
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV（development/paper_trading/live の検証）と LOG_LEVEL の検証。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順で候補選定、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額にフォールバックし WARNING ログを出力。
  - risk_adjustment:
    - apply_sector_cap: セクター毎の既存エクスポージャーを計算し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象から除外）。
    - calc_regime_multiplier: market レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供。未知レジームはログを出し 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジックを実装。
    - risk_based: risk_pct / stop_loss_pct に基づく株数算出と 1 銘柄上限処理。
    - equal/score: weight に基づく配分、portfolio_value * weight * max_utilization を元に算出。
    - 単元（lot_size）丸め、_max_per_stock による per-stock cap。
    - aggregate cap: available_cash を超える場合にスケールダウン。cost_buffer を加味した保守的なコスト見積りと、端数（fraction）に基づく追加配分ロジックを実装。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクター（momentum/volatility/value）を取得してマージ。
    - ユニバースフィルタ（最低株価・平均売買代金）適用。
    - 指定カラムの Z スコア正規化と ±3 クリップ。
    - DuckDB への日付単位 UPSERT（トランザクション + バルク挿入、ロールバック処理を含む）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みを用意し、ユーザ指定 weights を検証してフォールバック・再スケーリング。
    - ai_scores によるレジーム判定（Bear 検出時は BUY シグナルを抑制）。
    - final_score に基づく BUY シグナル生成（閾値デフォルト 0.60）。
    - _generate_sell_signals によるエグジット判定（ストップロス、スコア低下）。価格欠損時の判定スキップや features 未存在時の警告ログ。
    - signals テーブルへ日付単位で置換（冪等性確保）。

- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials のみ参照）。
  - feature_exploration:
    - calc_forward_returns: LEAD を使った複数ホライズンの将来リターン計算。
    - calc_ic: スピアマンのランク相関（ties は平均ランクで扱う）。
    - factor_summary: 各カラムの count/mean/std/min/max/median 計算。
    - rank: 同順位の平均ランクを返す実装（丸めによる ties 検出対策を含む）。

- バックテスト（kabusys.backtest）
  - metrics.calc_metrics: DailySnapshot / TradeRecord から主要指標（CAGR, Sharpe, MaxDrawdown, Win rate, Payoff ratio, total trades）を計算。
  - simulator.PortfolioSimulator:
    - メモリ内ポートフォリオ管理（cash, positions, cost_basis, history, trades）。
    - execute_orders: SELL を先に処理してから BUY を処理、SELL は現状「全量クローズ」で部分利確は未対応。
    - スリッページ（BUY:+, SELL:-）と手数料モデルを適用した擬似約定。TradeRecord / DailySnapshot 型を定義。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Known limitations / TODO（コード内の注記より）
- .env 読み込み:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（CI/配布後を考慮）。
- apply_sector_cap:
  - 現状 price_map が 0.0 の場合は露出が過少見積りされブロックが外れる可能性あり。前日終値や取得原価でのフォールバック未実装。
- calc_regime_multiplier:
  - Bear レジーム下でも generate_signals は通常 BUY シグナルを生成しない仕様（multiplier は追加セーフガード）。
- position_sizing:
  - 銘柄ごとの lot_size を持つ設計へ拡張予定（現状は全銘柄共通 lot_size）。
- signal_generator:
  - トレーリングストップや時間決済（保有 60 営業日超）などのエグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- simulator:
  - SELL は現状保有全量をクローズ（部分利確・部分損切り非対応）。
- 一部のログや警告は将来の監視/アラート設計で活用予定。

-----

注: 本 CHANGELOG は提供されたコード内容からの推測に基づいて作成しています。リリース日や追加のリリースノート（バグ修正、パフォーマンス改善、API 変更など）は実際のプロジェクト運用に合わせて追記してください。