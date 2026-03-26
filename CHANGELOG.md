# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初期リリースをコードベースから推測して記載しています。

## [Unreleased]


## [0.1.0] - 2026-03-26

Added
- 初期リリース（パッケージバージョン: 0.1.0）
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージ __all__）

- 環境設定 / 設定管理（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数を読み込む自動ロード機能を実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local (override=True) > .env (override=False)
    - OS 環境変数は protected として .env による上書きを防止
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサーは以下に対応
    - export KEY=val 形式
    - シングル/ダブルクォート、バックスラッシュエスケープ
    - クォートなしのインラインコメント処理（# の前が空白/タブならコメントと判定）
  - Settings クラスの提供（settings インスタンス）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時に ValueError を送出）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルト値を持つ
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の検証
    - is_live / is_paper / is_dev のヘルパー

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルを score 降順、同点時は signal_rank 昇順で上位 N を選択
    - calc_equal_weights: 等金額配分（各銘柄 1/N）
    - calc_score_weights: スコア加重配分（総スコアが 0 の場合は等金額にフォールバック、WARNING ログ出力）
  - risk_adjustment
    - apply_sector_cap: 既存保有を基にセクター別エクスポージャー計算、指定比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）
      - sell_codes を受け取り当日売却予定銘柄をエクスポージャー計算から除外可能
      - price マップが欠損した場合の挙動（注記: 将来的にフォールバック価格を検討）
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバック（WARNING）
  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method は "risk_based" / "equal" / "score" をサポート
      - risk_based: 許容リスク率 (risk_pct)、stop_loss_pct に基づいて株数算出
      - equal/score: weights（{code: weight}）に基づき portfolio_value * weight * max_utilization を配分
      - per-stock の上限（max_position_pct）や lot_size（丸め）、_max_per_stock による制限を適用
      - aggregate cap: 全銘柄投資合計が available_cash を超える場合にスケールダウン。cost_buffer を考慮して約定コストを保守的に見積もる
      - スケーリング後の端数は lot_size 単位で fractional 残差が大きい順に追加配分（再現性確保のため安定ソート）
      - lot_size は現状グローバル定数的に扱う（将来的に銘柄別拡張予定）

- 戦略（kabusys.strategy）
  - feature_engineering.build_features
    - research モジュールから生ファクター（momentum / volatility / value）を取得し結合
    - ユニバースフィルタ（最低株価・平均売買代金）適用
    - 指定カラムを z-score 正規化し ±3 でクリップ
    - DuckDB へ日付単位の置換（DELETE + INSERT）で冪等に保存
  - signal_generator.generate_signals
    - features と ai_scores を統合して final_score を計算（momentum/value/volatility/liquidity/news の重みをサポート）
    - weights の入力検証とデフォルトフォールバック、合計が 1.0 でない場合の再スケール
    - _sigmoid/_avg 等のユーティリティを使用
    - AI スコアの欠損は中立 (0.5) で補完
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）では BUY シグナルを抑制
    - BUY は threshold（デフォルト 0.6）以上で生成、SELL はポジションに対してストップロス（-8%）やスコア低下で生成
    - SELL を優先して BUY から除外、rank を再付与
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（ウィンドウ不足時は None）
    - calc_volatility: ATR(20) / atr_pct, avg_turnover, volume_ratio の計算（TR の NULL 取り扱いに注意）
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算
    - DuckDB に依存し prices_daily / raw_financials のみ参照
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: Spearman（ランク）による IC 計算（有効サンプル <3 の場合 None）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数丸めで ties 検出安定化）
  - research パッケージは zscore_normalize を再エクスポート

- バックテスト（kabusys.backtest）
  - simulator
    - DailySnapshot / TradeRecord の dataclass
    - PortfolioSimulator: メモリ内でのポートフォリオ管理と擬似約定
      - execute_orders: SELL を先に処理、BUY を後で処理
      - スリッページ (slippage_rate) と 手数料 (commission_rate) のモデルを受け入れ
      - SELL は保有全量クローズ（部分利確・部分損切りは未対応）
      - TradeRecord に realized_pnl を保持（SELL 時のみ設定）
  - metrics
    - calc_metrics: history（DailySnapshot）と trades（TradeRecord）から BacktestMetrics を計算
      - 計算指標: cagr, sharpe_ratio (無リスク=0), max_drawdown, win_rate, payoff_ratio, total_trades
      - 各指標の詳細実装（年次化、252営業日等）

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリース）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / Limitations / TODO（コード内コメントに基づく）
- apply_sector_cap: price が 0.0 の場合、エクスポージャーが過少估計される可能性があるため将来的に前日終値や取得原価でのフォールバックを検討
- position_sizing:
  - 現状 lot_size はグローバル・共通扱い。将来的に銘柄別 lot_map の導入を想定
  - 部分約定や銘柄別単元未対応のため、日本株の実運用では lot_size の指定に注意
- signal_generator のエグジット条件:
  - トレーリングストップや時間決済（保有日数）については未実装（positions テーブルに peak_price / entry_date 等が必要）
- simulator.execute_orders:
  - SELL は常に保有全量をクローズ。部分クローズ非対応
- DB 操作は DuckDB を想定（トランザクションで日付単位の置換を実行）。運用時はテーブルスキーマと前提を確認すること
- ロギング: 多くの関数が状態異常時に logger.warning/debug/info を出力する。実行時のログ設定に注意

開発者向けメモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 自動 .env 読み込みをテストや CI で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB 接続を渡して各種関数（build_features/generate_signals/calc_*）を利用する想定

（以上）