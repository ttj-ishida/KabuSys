# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回バージョンとして 0.1.0 をリリースします。

## [0.1.0] - 2026-03-26

### 追加 (Added)
- パッケージ初期構成
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
  - 公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を親ディレクトリから探索してプロジェクトルートを特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動ロードを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、クォート、エスケープシーケンスに対応）。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN・KABU_API_PASSWORD・SLACK_BOT_TOKEN 等）や既定値（KABU_API_BASE_URL、データベースパス等）をプロパティとして取得可能。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値以外は ValueError）。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄候補選定: select_candidates（スコア降順、signal_rank によるタイブレーク）。
  - 重み計算:
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア加重配分、全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - リスク調整:
    - apply_sector_cap：既存保有のセクター別エクスポージャーに基づき、新規候補を除外するセクター上限チェック（"unknown" セクターは除外しない）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数の計算（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告ログを出して 1.0 にフォールバック。
  - ポジションサイズ算出:
    - calc_position_sizes：allocation_method（risk_based / equal / score）に基づいて銘柄ごとの発注株数を計算。
    - リスクベース（risk_pct / stop_loss_pct）や per-position 上限（max_position_pct）、aggregate cap（available_cash）を考慮。
    - lot_size（単元）で丸め処理、cost_buffer による保守的コスト見積り、スケールダウン時の再配分ロジックを実装。
    - 単元や銘柄毎の lot_size 拡張については将来の TODO（現状は共通 lot_size を想定）。

- 研究・特徴量 (src/kabusys/research/*, src/kabusys/strategy/feature_engineering.py)
  - ファクター計算（research/factor_research.py）:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true range の NULL 伝播を適切に制御）。
    - calc_value: raw_financials から最新の財務データを参照し PER / ROE を計算（EPS が 0 または欠損のときは None）。
  - 特徴量探索・統計 (research/feature_exploration.py):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装（1クエリで取得）。
    - calc_ic: スピアマンのランク相関（IC）計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクとするランク計算（丸め誤差対策あり）。
  - 特徴量保存 / 正規化 (strategy/feature_engineering.py):
    - build_features: research モジュールで計算した raw factors をマージ、価格・流動性ベースのユニバースフィルタ、Z スコア正規化（指定列）、±3 でクリップし、features テーブルへ日付単位の置換（冪等処理）で保存。
    - ユニバース条件: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals:
    - features / ai_scores / positions を参照して final_score を算出（コンポーネント: momentum/value/volatility/liquidity/news）。
    - デフォルト重みを定義し、ユーザー指定 weights は検証・補完・再スケールして採用。
    - AI の regime_score 集計による Bear レジーム判定（サンプル不足時は Bear とは見なさない）。Bear レジーム時は BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄を BUY として生成。SELL シグナルは stop_loss（-8%）および final_score の閾値割れで生成。
    - SELL 優先ポリシー: SELL 対象を BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位で置換して保存（トランザクション + バルク挿入）。
    - 欠損データや価格欠損に対するログ出力・安全策あり（例: features にない保有銘柄は score=0 として SELL 判定、価格がない保有銘柄は SELL 判定をスキップ）。

- バックテスト (src/kabusys/backtest/*)
  - 指標計算 (backtest/metrics.py):
    - BacktestMetrics データクラス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - calc_metrics: DailySnapshot と TradeRecord から各種指標を計算。
    - 個別実装: CAGR（暦日ベース）、Sharpe（年次化、無リスク金利=0、252 日年率化）、Max Drawdown、勝率、ペイオフレシオ等。
  - ポートフォリオシミュレータ (backtest/simulator.py):
    - DailySnapshot / TradeRecord データクラス。
    - PortfolioSimulator: メモリ内でキャッシュ・ポジション・コスト基準を管理し、シグナルに基づく約定処理をシミュレート。
    - execute_orders: 当日始値での擬似約定。SELL を先に処理（保有全量をクローズ）、その後 BUY を処理。スリッページ・手数料モデルを適用。部分約定は lot_size に基づく丸めで対応。

- ロギング・エラーハンドリング
  - 各モジュールで詳細な debug/info/warning ログを出力。
  - DB 操作時のトランザクション管理（COMMIT / ROLLBACK）を採用して原子性を確保。

### 既知の制限・未実装 (Known issues / Not implemented)
- position_sizing:
  - lot_size は現状グローバル共通で取り扱い（将来的に銘柄別 lot_map への対応を想定）。
  - price_map の欠損（0.0）によりセクターエクスポージャーが過少見積りされる問題があり、将来的にフォールバック価格（前日終値・取得原価等）を検討。

- signal_generator / 戦略ロジック:
  - トレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - Bear レジーム相当の抑制は実装済みだが、market_regime による完全な動作は外部 ai_scores の品質に依存。
  - AI ニューススコアは ai_scores の未登録時に中立（0.5）で補完。

- simulator:
  - SELL は保有全量をクローズする実装。部分利確・部分損切りは未対応。
  - execute_orders の一部実装が前提（lot_size 等の扱いに注意）。

- その他:
  - 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバックなど）が残る。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

---

備考:
- ドキュメント内の参照（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md, UniverseDefinition.md 等）は設計資料を示しており、実装はこれらのセクションに準拠しています。実運用前に .env 設定、DB スキーマ（prices_daily, features, ai_scores, positions, signals 等）および lot_size や手数料モデルの精査を推奨します。