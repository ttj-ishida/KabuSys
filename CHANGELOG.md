# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、SemVer を採用します。

## [0.1.0] - 初回リリース (initial)
最初のリリース。日本株自動売買ライブラリ KabuSys のコア機能をまとめて実装。

### 追加
- パッケージ構成
  - パッケージ名: kabusys、version: 0.1.0
  - エクスポート: data, strategy, execution, monitoring（__init__）

- 環境設定モジュール（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）
  - .env / .env.local の優先度管理（OS 環境変数の保護、override のサポート）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - .env 行パーサーの強化:
    - export KEY=val 形式対応
    - 単一/二重クォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォート外での '#' はスペース/タブ直前をコメントと判定）
  - 環境変数の必須チェック _require()
  - Settings クラスによる設定取得プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトローカルURL）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates(buy_signals, max_positions): スコア降順 + タイブレーク（signal_rank）
    - calc_equal_weights(candidates): 等金額配分
    - calc_score_weights(candidates): スコア加重配分（スコア合計 0 の場合は等配分へフォールバック）
  - position_sizing:
    - calc_position_sizes(...): 銘柄ごとの発注株数決定（allocation_method: "risk_based" / "equal" / "score"）
      - risk_based: risk_pct / stop_loss_pct に基づく算出
      - equal/score: weight に基づく算出、max_position_pct/max_utilization の考慮
      - lot_size 単位で丸め、_max_per_stock による per-stock cap 判定
      - aggregate cap（available_cash 超過時）のスケーリングと余剰キャッシュによる補完ロジック
      - cost_buffer による手数料・スリッページ保守見積りを導入
  - risk_adjustment:
    - apply_sector_cap(...): セクター集中 (max_sector_pct) を超過するセクターの新規候補を除外（"unknown" セクターは除外対象外）
      - sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外可能
      - 既存保有の価格欠損時の注意点（TODO コメントで明示）
    - calc_regime_multiplier(regime): market regime に応じた資金投下乗数 ("bull":1.0, "neutral":0.7, "bear":0.3)、未知のレジームは 1.0 にフォールバック

- ストラテジー（kabusys.strategy）
  - feature_engineering.build_features(conn, target_date):
    - research モジュールから得た生ファクターをマージ、ユニバースフィルタ（株価・流動性）適用、Z スコア正規化（±3 クリップ）し features テーブルへ日付単位の置換（トランザクションで原子性確保）
    - ユニバース閾値: min price = 300 円、min turnover = 5e8 円
    - DuckDB を用いた SQL + Python 実装
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して final_score を算出（component: momentum/value/volatility/liquidity/news）
    - シグナル生成フロー（BUY/SELL）を実装:
      - Bear レジーム検知時は BUY 抑制（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）
      - BUY: final_score >= threshold の銘柄を候補に（順位付け）
      - SELL: _generate_sell_signals にてストップロス（-8%）およびスコア低下で判定
      - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与
      - signals テーブルへ日付単位の置換（トランザクションで原子性確保）
    - 重みの補完・検証:
      - _DEFAULT_WEIGHTS をベースに user weights を受け付け、既知キーのみ採用、非数値/負値等はスキップ
      - 合計が 1.0 になるようリスケール、合計 0 以下はデフォルトへフォールバック
    - 未実装だが仕様に言及しているエグジット:
      - トレーリングストップ（peak_price が必要）
      - 時間決済（保有 60 営業日超）

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200 乖離を算出（データ不足時は None）
    - calc_volatility(conn, target_date): ATR(20), atr_pct, avg_turnover, volume_ratio を算出（データ不足判定あり）
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER/ROE を算出（EPS が 0/欠損時は PER=None）
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンを一度の SQL クエリで取得
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン IC（ランク相関）計算（有効レコード 3 未満で None）
    - factor_summary(records, columns): 各列の count/mean/std/min/max/median を返す
    - rank(values): 同順位は平均ランクで処理（round(..., 12) による ties の安定化）
  - zscore_normalize を kabusys.data.stats から取り込み、研究用ワークフローに統合

- バックテスト（kabusys.backtest）
  - metrics:
    - BacktestMetrics dataclass と calc_metrics(history, trades) 実装
    - 指標: CAGR, Sharpe (無リスク=0), Max Drawdown, Win Rate, Payoff Ratio, total trades
    - 内部関数の実装（暦日ベースの CAGR, 年次化 Sharpe (252 日), drawdown, 等）
  - simulator:
    - PortfolioSimulator: メモリ内のポートフォリオ状態管理（cash, positions, cost_basis, history, trades）
    - execute_orders(signals, open_prices, slippage_rate, commission_rate, ...) 実装
      - SELL を先に全量クローズ、その後 BUY（部分利確非対応）
      - スリッページは BUY:+、SELL:- で適用、手数料は commission_rate で算出
      - TradeRecord / DailySnapshot のデータ構造を定義

- 研究環境と本番系の分離設計
  - 各モジュールは発注 API や実行層に依存しない純粋関数／DuckDB 接続を想定した設計

### 変更点（設計的決定・注意点）
- feature_engineering / signal_generator / research の各関数はルックアヘッドを避けるため target_date 時点までのデータのみを使用する設計
- apply_sector_cap は "unknown" セクターをセクター上限の適用対象外とする（設計上の選択）
- calc_regime_multiplier は Bear 相場でも generate_signals によりそもそも BUY が出ないため、追加のセーフガードとして弱めの乗数を用いる（0.3）
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別拡張を想定する TODO）

### 修正（バグ修正 / 既知の改善）
- （初回リリースのため履歴なし）ただしソース中に以下の既知問題・改善候補を明記:
  - apply_sector_cap: price_map に price が欠損（0.0）だとエクスポージャーが過小見積もりされ、ブロックが外れる問題（TODO）
  - _generate_sell_signals: positions / prices 欠損時の処理でログを出すが、トレーリングストップ等は未実装

### 含まれない（未実装機能 / 将来の拡張）
- 銘柄別 lot_size マスタ（現在は単一 lot_size 引数で対応）
- トレーリングストップ、時間決済などの追加エグジット条件（コード内に未実装コメントあり）
- 一部のメトリクスの追加（例: 最大保有日数集計など）は未実装

### 既知の注意点（ユーザ向け）
- .env パーサーは多くのケースに対応しているが、極端に複雑なシェル式や複数行クォート等は想定外
- DuckDB スキーマ（prices_daily / raw_financials / features / ai_scores / positions / signals 等）を事前に準備する必要がある
- signal_generator の Bear 判定は ai_scores の regime_score に依存するため、ai_scores の整備が重要
- position_sizing の aggregate cap スケーリングは浮動小数点の丸めや lot_size による切り捨てで挙動が複雑になる可能性があるため、本番運用前に十分なテスト推奨

---

このリリースは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）に基づいて実装されています。ファイル内に多くの TODO / 注意書きが残っているため、実運用や拡張の際は該当箇所の検討・テストを行ってください。