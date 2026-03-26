# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-26

Added
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: KabuSys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パブリック API として data / strategy / execution / monitoring をエクスポート。

- 環境設定 / .env ロード機能（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local をロード。
  - ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル・ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - コメントの扱い（クォートなしでは '#' の直前が空白/タブの場合にコメントとして扱う）に対応。
  - ファイル読み込み失敗時は警告を発行して継続。
  - Settings クラスを提供し、必須環境変数取得（_require）や既定値をラップ:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV の既定値とバリデーション（LOG_LEVEL / KABUSYS_ENV の許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ポートフォリオ構築関連（src/kabusys/portfolio/）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート（score 降順、タイブレークに signal_rank）と上位 N 抽出。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比例配分。全スコアが 0.0 の場合は等金額にフォールバックし警告を出力。
  - risk_adjustment:
    - apply_sector_cap: 既存ポジションのセクター別時価総額からセクター集中上限（max_sector_pct）を判定し、新規候補を除外。unknown セクターは制限対象外。
      - sell_codes を受け取り当日売却予定銘柄をエクスポージャー計算から除外可能。
      - 価格欠損時の注意（TODO によるフォールバック検討の指摘）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 発注株数計算ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - risk_based: risk_pct と stop_loss_pct に基づくポジションサイズ算出。
      - equal/score: 重み（weights）に基づき portfolio_value, max_utilization を用いて算出。
      - per-stock 上限 (max_position_pct)、単元株（lot_size）での丸め、price ベースの _max_per_stock 判定。
      - aggregate cap: 全銘柄合計コストが available_cash を超える場合のスケーリング処理を実装。cost_buffer を考慮し保守的に見積もる。
      - スケールダウン後は小数端数を lot_size 単位で再配分（残差が大きい順）。安定性のため tie-break に code を使用。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date):
    - research モジュール(calc_momentum / calc_volatility / calc_value) から生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルに対する日付単位の置換（冪等）：トランザクション + バルク挿入で原子性を保証。
    - 欠損値や例外時のロールバック処理を備える。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.6, weights=None):
    - features と ai_scores を統合して最終スコア(final_score) を計算。
    - コンポーネントスコアの算出:
      - momentum: momentum_20 / momentum_60 / ma200_dev のシグモイド平均。
      - value: PER を変換 (per=20 -> 0.5、per→0 ->1、per→∞ ->0 に近づく)。
      - volatility: atr_pct の Z スコアを反転してシグモイド変換。
      - liquidity: volume_ratio をシグモイド変換。
      - news: ai_score をシグモイド変換（未登録時は中立補完）。
    - weights のマージと正規化（不正値はスキップ、合計が 1 でない場合は再スケーリング）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合）で BUY を抑制。
    - BUY シグナル: threshold 超過銘柄に対しランク付き BUY を生成。
    - SELL シグナル:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先で判定。
      - final_score が threshold 未満なら SELL（score_drop）。
      - 未実装: トレーリングストップ / 時間決済（将来的に positions テーブルの拡張が必要である旨の注記）。
    - signals テーブルへの日付単位置換（冪等処理）。
    - features が空の場合は BUY を生成せず SELL 判定のみ実施。

- リサーチ機能（src/kabusys/research/）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials のみ参照して各種ファクターを算出（一定期間のデータ不足時は None を返す仕様）。
    - 各関数は date, code をキーとする dict リストを返す。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターン取得。horizons の検証（正の整数、<=252）と一括クエリによる取得。
    - calc_ic: factor と将来リターンの Spearman ランク相関を計算（有効レコードが 3 件未満なら None）。
    - rank: 同順位に平均ランクを割り当てる実装（丸めによる ties 回避のため round(v,12) を利用）。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を算出。

- バックテスト（src/kabusys/backtest/）
  - metrics:
    - BacktestMetrics dataclass と calc_metrics() を提供（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、Total Trades）。
    - 個別計算関数の実装（年次化やエッジケース処理を考慮）。
  - simulator:
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理、擬似約定処理を実装。
      - DailySnapshot / TradeRecord dataclass を定義。
      - execute_orders: SELL を先に処理してから BUY を処理（SELL は保有全量をクローズする仕様）。スリッページ（BUY:+、SELL:-）・手数料率を適用。
      - 約定情報は TradeRecord に記録（realized_pnl は SELL 時のみ計算・格納）。
      - lot_size パラメータで単元扱いが可能（デフォルト互換性のため 1 を許可）。

Changed
- 初回リリースのため過去の変更履歴はなし。

Fixed
- 初回リリースのため過去の修正はなし。

Known limitations / Notes
- apply_sector_cap: price_map に 0.0 または欠損があるとエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価をフォールバックに使う検討が記載されています。
- signal_generator におけるトレーリングストップ・時間決済は未実装。positions テーブルの拡張（peak_price / entry_date）が要件。
- .env のコメント/クォート解釈は一般的なケースを想定しているが、edge case のパーシングで差異が出る可能性あり。
- 取引手数料・スリッページのモデルは簡易化（パラメータ化）されており、実取引での検証が必要。

Acknowledgements
- 本リリースでは外部ライブラリの使用を最小限に抑え、DuckDB をデータソースとして前提にした設計になっています。