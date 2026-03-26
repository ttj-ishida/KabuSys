# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠して記載します。  
フォーマット: "Unreleased" → 今後の変更、その下に各リリース（バージョンと日付）を列挙しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-26
初回公開リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点・挙動は以下の通りです。

### Added
- パッケージ基礎
  - パッケージバージョンを設定 (kabusys.__version__ = "0.1.0")。
  - モジュール公開 API を __all__ で定義（data, strategy, execution, monitoring など）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。`.env.local` は既存の OS 環境変数を保護しつつ上書き可能。
  - 読み込み時の保護セット（protected）により OS 環境変数を上書きしない挙動。
  - .env パーサーは export の前置、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - 任意・デフォルト: KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - システム環境値検証: KABUSYS_ENV は development/paper_trading/live のいずれか、LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかでバリデーションを実施
    - ヘルパー: is_live/is_paper/is_dev プロパティ

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す。タイブレークは signal_rank の昇順。
    - calc_equal_weights: 等比率配分（1/N）を計算。
    - calc_score_weights: スコア比率で正規化して重みを算出。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - risk_adjustment
    - apply_sector_cap: 既存保有セクター比率が閾値（デフォルト 30%）を超える場合、同セクターの新規候補を除外（unknown セクターは除外対象外）。当日売却予定銘柄はエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に応じた投下資金乗数（1.0,0.7,0.3）を返す。未知レジームは 1.0 にフォールバックし WARNING を出力。
  - position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて銘柄ごとの発注株数を算出。
      - risk_based: 許容リスク率 (risk_pct) と損切り率 (stop_loss_pct) に基づく株数上限を計算。
      - equal/score: 各銘柄の weight に基づき per-position 上限、aggregate cap（利用可能現金）を考慮して計算。
      - 単元（lot_size）で丸め、max_position_pct による per-stock 上限を適用。
      - cost_buffer により手数料/スリッページを保守的に見積もり、aggregate cap を超える場合はスケールダウン。スケールダウン後は lot 単位で残差を大きい順に追加配分するロジックを持つ（再現性のため安定ソート）。
      - lot_size の拡張（銘柄別 lot_map）や価格フォールバック等は将来の拡張点として TODO を明示。

- 戦略（特徴量・シグナル） (kabusys.strategy)
  - feature_engineering
    - build_features: research 側のファクター（momentum / volatility / value）を取得し、ユニバースフィルタ（株価・平均売買代金閾値）を適用、数値ファクターを Z スコア正規化して ±3 でクリップし、features テーブルへ日付単位で置換（トランザクションで原子性保証）。DuckDB を利用。
    - ユニバースの閾値は _MIN_PRICE=300 円、_MIN_TURNOVER=5e8（20日平均売買代金）。
  - signal_generator
    - generate_signals: features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成して signals テーブルへ置換保存。
    - コンポーネント: momentum/value/volatility/liquidity/news にデフォルト重みを用意（合計 1.0 にリスケール）。ユーザー重みは妥当性チェック（未定義キー、非数値、負値等は無視）される。
    - スコア計算は Z スコア → シグモイドへの変換、欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score 平均が負でかつサンプル数 >= 3 のとき Bear とみなし、BUY シグナルを抑制する。
    - SELL シグナル: ストップロス（終値/平均取得 < -8%）および final_score が閾値未満。SELL は BUY より優先され、SELL 対象は BUY 候補から除外される。
    - features が空の場合は BUY は生成せず、SELL 判定のみ実施。
    - DB トランザクション中に例外が起きた場合は ROLLBACK を試行し、失敗時は WARNING をログ出力。

- リサーチ (kabusys.research)
  - factor_research
    - calc_momentum/calc_volatility/calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリューファクターを計算。戻り値は (date, code) をキーとする dict のリスト。
    - 各ファクター計算は窓長・必要行数チェックを行い、データ不足時は None を返す挙動。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の妥当性検査あり（1〜252）。
    - calc_ic: Spearman（ランク）相関を計算。サンプル数 < 3 の場合は None。
    - factor_summary: 指定カラム群の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを採る実装。比較前に round(v,12) で丸めて ties 検出の丸め誤差を吸収。

- バックテスト (kabusys.backtest)
  - simulator
    - PortfolioSimulator: メモリ内でポートフォリオ状態・履歴を管理。初期現金で初期化。
    - execute_orders: SELL を先に全量クローズ、その後 BUY を処理する。約定は当日始値を使いスリッページ/手数料を適用。部分利確・部分損切りは非対応（SELL は保有全量クローズ）。
    - TradeRecord / DailySnapshot のデータ構造を提供。
  - metrics
    - calc_metrics: DailySnapshot と TradeRecord から各種評価指標を算出（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - 各指標の内部実装を提供し、データ不足時の安全なフォールバック（例: 標本数不足で 0.0）を実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数読み込みは OS 環境変数の保護（protected set）を考慮して実装しており、意図しない上書きを避ける設計を採用。

---

注意事項（既知の制約・今後の拡張点）
- position_sizing の lot_size は現状グローバルな単一値のみ対応。将来的に銘柄別 lot_map を受け取る拡張を予定（TODO コメントあり）。
- apply_sector_cap は price_map の価格欠損時にエクスポージャーが過小推定されうる点をコメントで指摘しており、前日終値や取得原価でのフォールバックは未実装。
- signal_generator の一部エグジット条件（トレーリングストップ、保持日数による期日決済）は positions テーブルの拡張（peak_price / entry_date 等）を前提として未実装のまま。
- simulator の SELL は現状「保有全量クローズ」のみ対応。部分売却や約定の複雑な振る舞いは未対応。
- 多くの処理は DuckDB の特定テーブル (prices_daily, features, ai_scores, raw_financials, positions など) の存在を前提としており、テーブル構造・データ充足がない場合は警告・例外が発生する可能性があります。

詳細な設計やアルゴリズムの根拠はソース内ドキュメント（関数 docstring、PortfolioConstruction.md / StrategyModel.md 参照）に従っています。必要であれば、各モジュールの API 仕様（引数/戻り値・例外）を別途ドキュメント化します。