CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
タグ付けは semver を想定します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-26
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージエントリポイント
    - kabusys.__version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を公開予定の名前空間として設定。
  - 環境設定・ロード機能 (kabusys.config)
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサ実装: export 形式、クォート内エスケープ、インラインコメントなどを考慮した堅牢なパース処理。
    - 必須環境変数チェックを提供（_require）。未設定時は ValueError を送出。
    - 主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN (必須)
      - KABU_API_PASSWORD (必須)
      - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
      - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須)
      - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
      - SQLITE_PATH (デフォルト: data/monitoring.db)
      - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - ユーティリティプロパティ: is_live / is_paper / is_dev
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder
      - select_candidates(buy_signals, max_positions=10): スコア降順（同点は signal_rank でタイブレーク）で上位候補を選択。
      - calc_equal_weights(candidates): 等金額配分を返す。
      - calc_score_weights(candidates): スコア比率で重み付け。全スコア 0 の場合は等配分にフォールバック（WARNING）。
    - risk_adjustment
      - apply_sector_cap(...): 既存保有のセクター露出が max_sector_pct を超える場合、そのセクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier(regime): market regime に応じた投下資金乗数（bull=1.0 / neutral=0.7 / bear=0.3）。未知レジームは 1.0 でフォールバック（WARN）。
    - position_sizing
      - calc_position_sizes(...): allocation_method ("risk_based", "equal", "score") に応じた発注株数決定。
        - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct からベース株数を算出。
        - equal/score: 重みと max_utilization を考慮して株数を算出。
        - 単元 lot_size に丸め、per-stock 上限（max_position_pct）を適用。
        - aggregate cap: available_cash を超える場合にスケールダウンし、残差を lot 単位で再配分。
        - cost_buffer により手数料/スリッページを保守的に見積もり。
  - ストラテジー (kabusys.strategy)
    - feature_engineering.build_features(conn, target_date)
      - research モジュールの calc_momentum / calc_volatility / calc_value を統合。
      - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）。
      - 指標の Z スコア正規化（対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）、±3 でクリップ。
      - features テーブルへ日付単位で置換（トランザクション保護、冪等）。
    - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
      - features と ai_scores を統合して各銘柄の final_score を算出（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
      - ai_scores による市場レジーム判定（Bear 判定は regime_score の平均が負かつサンプル数 >= 3）。
      - Bear レジームでは BUY シグナルを抑制（SELL 判定は継続）。
      - BUY: threshold を超えた銘柄に対して buy シグナルを発行。SELL: positions / price を基にストップロス・スコア低下で判定。
      - signals テーブルへ日付単位で置換（トランザクション保護、冪等）。
  - リサーチ (kabusys.research)
    - factor_research
      - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials を用いた各種定量ファクター計算（1M/3M/6M リターン、MA200 乖離、ATR20、20日平均売買代金、PER/ROE 等）。
    - feature_exploration
      - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターン計算（複数ホライズン一括取得）。
      - calc_ic(factors, forwards, factor_col, return_col): Spearman ランク相関（IC）計算（有効データ < 3 件は None）。
      - factor_summary(records, columns): 基本統計量（count/mean/std/min/max/median）を返す。
      - rank(values): 同順位は平均ランクで処理するランク関数。
    - research パッケージは zscore_normalize を data.stats から利用。
  - バックテスト (kabusys.backtest)
    - simulator.PortfolioSimulator
      - メモリ内でのポートフォリオ管理、execute_orders による擬似約定（SELL を先に処理、全量クローズ、スリッページ/手数料モデル適用）。
      - TradeRecord / DailySnapshot データ構造を提供。
    - metrics.calc_metrics(history, trades)
      - CAGR, Sharpe Ratio (無リスク=0), Max Drawdown, Win Rate, Payoff Ratio, total_trades の計算を提供。
  - 各モジュールでログ出力・警告を充実させ、運用時の診断を容易に。

Changed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Known limitations / Notes / TODOs
- 一部設計上明示された制約・未実装機能:
  - sector exposure の価格欠損時のフォールバック（現状 price_map が 0.0 の場合、過少評価される可能性あり。将来的に前日終値や取得原価でのフォールバックを検討）。
  - position_sizing: 現状 lot_size は全銘柄共通。将来的に銘柄別 lot_map を受け取る設計へ拡張予定（TODO コメントあり）。
  - sell ロジック: トレーリングストップや時間決済（例: 保有 60 営業日超）などはいまのところ未実装（positions テーブルに peak_price / entry_date が必要）。
  - PortfolioSimulator の SELL は保有全量をクローズ（部分利確・部分損切りはサポート外）。
  - feature_engineering / signal_generator / research は DuckDB の特定テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存するため、スキーマの準備が必要。
  - generate_signals: AI スコアが未登録の銘柄は中立扱い（news=0.5）に補完。ai_scores のサンプル不足時には Bear 判定を抑制する安全弁あり。
  - config モジュールは OS 環境変数の保護を行う（.env の読み込み時に既存 OS 環境変数を保護する挙動）。
- 運用上の注意:
  - 必須環境変数が未設定だと起動時に ValueError が発生する（安全な fail-fast）。
  - デフォルト閾値や定数（例: BUY 閾値 0.60、min price 300 円、min turnover 5e8、regime multipliers 等）は StrategyModel.md / PortfolioConstruction.md に基づく推奨値として実装されているが、運用環境に応じて調整が推奨される。

参考: 主要デフォルト/定数
- BUY threshold: 0.60
- factor zscore clip: ±3.0
- universe filter: min price = 300 円、min turnover = 5e8 円（20日平均）
- default factor weights: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
- regime multipliers: bull=1.0, neutral=0.7, bear=0.3
- position sizing defaults: risk_pct=0.005, stop_loss_pct=0.08, max_position_pct=0.10, max_utilization=0.70, lot_size=100（想定）

--- 
補足:
- 本 CHANGELOG はソース中の docstring・コメント・実装ロジックに基づき作成しています。実際のリリースノートやバージョン履歴と差異がある場合は、運用での変更点を反映して適宜更新してください。