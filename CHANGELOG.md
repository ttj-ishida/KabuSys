# Changelog

すべての重大な変更はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠しています。  
※ リリース日はソースコードの状態（このスナップショット）に基づいています。

バージョン番号はパッケージ定義（kabusys.__version__）に準じます。

## [Unreleased]
- 現在のスナップショットに対する未リリースの変更はありません。

## [0.1.0] - 2026-03-26
最初の公開リリース。日本株自動売買システムのコアライブラリを含む初版を追加。

### Added
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) により、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - パッケージバージョン __version__ = "0.1.0" を設定。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの探索は __file__ を基点に .git または pyproject.toml を検索して行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - 高機能な .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、以下の設定プロパティを取得：
    - J-Quants / kabu API / Slack トークン・チャネル、DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）、ログレベル、便宜的な is_live/is_paper/is_dev フラグ。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須項目取得時の例外発生（_require）。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す（タイブレークに signal_rank を使用）。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - リスク調整（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補の同セクター銘柄を除外する（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし WARNING を出力。
  - ポジションサイジング（position_sizing）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
      - risk_based: 許容リスク率・ストップロスから株数を算出。
      - equal/score: 重み・最大利用率・最大ポジション比率を考慮して株数を算出。
      - 単元（lot_size）丸めと aggregate cap によるスケーリング（cost_buffer を用いた保守的見積もり）。余剰キャッシュを用いた端数分配ロジックを実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（株価・流動性）、Z スコア正規化（指定列）、±3 クリップを適用して features テーブルへ日付単位の置換（冪等）で書き込む。
  - ユニバース条件: 最低株価 300 円、20 日平均売買代金 >= 5 億円。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位の置換で書き込む。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算。欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みと閾値（weights デフォルト: momentum 0.40 等、threshold=0.60）を実装。ユーザ提供 weights の検証・正規化を行う。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル数不足時は Bear とはみなさない）。
    - エグジットロジック（SELL）: ストップロス（-8%）および final_score の閾値割れを実装。未実装のトレーリングストップ / 時間決済に関する注意コメントを追加。
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与。

- Research（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - momentum: 1M/3M/6M リターン、MA200 乖離（十分な履歴がない場合は None）。
    - volatility: 20 日 ATR・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率。
    - value: PER（EPS が 0/欠損時は None）、ROE（最新財務レコードを使用）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman のランク相関（IC）を計算（有効レコードが 3 未満の場合は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクを与えるランク関数（丸め処理で ties 検出漏れを防止）。
  - zscore_normalize は kabusys.data.stats から再公開。

- バックテスト（kabusys.backtest）
  - metrics: calc_metrics を実装し、CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / total_trades を計算するユーティリティを提供。
  - simulator: PortfolioSimulator を実装。
    - メモリ上でのポートフォリオ状態管理、注文実行（SELL を先に全量クローズ、BUY を後で処理）。
    - スリッページ（BUY は +、SELL は -）と手数料率を適用した約定価格算出。
    - TradeRecord / DailySnapshot の dataclass を提供。
    - 注意: SELL は現時点で「保有全量をクローズ」する動作（部分利確/部分損切りは未対応）。

### Changed
- 新規リリースのため特別な既存機能の変更はありません（初版）。

### Fixed
- 特定のバグ修正はこの初版に含まれていません。

### Notes / Known limitations / TODOs
- .env 読み込み
  - .env ファイル内の価格フォールバックなどは未実装。apply_sector_cap は price_map に 0.0（欠損）を渡すとエクスポージャーが過少見積もられる可能性がある旨を注記。
- signal_generator / sell ロジック
  - トレーリングストップや時間決済（保有日数に基づく決済）は未実装（positions テーブルに peak_price / entry_date 等の拡張が必要）。
- position_sizing
  - lot_size は現状全銘柄共通パラメタ。将来的に銘柄別の単元サイズを利用できるよう拡張予定（stocks マスタに lot_size を持つ）。
- simulator
  - 部分約定や複雑な約定ルール（部分利確）には未対応。日本株実運用に合わせるには lot_size 引数等の適切な指定が必要。
- レジーム乗数
  - calc_regime_multiplier のマッピングは簡易ルール（bull/neutral/bear）で、未知レジームは 1.0 でフォールバックする。

### Technical / operational notes
- 多くのモジュールは DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提としているため、実行環境に DuckDB と該当テーブルの準備が必要。
- ロギングは各モジュールで logger を使用しており、重要なフォールバックや警告を出力する実装が入っています。

---

今後のリリースでは以下を計画しています（例）
- 部分利確・トレーリングストップのエグジットロジック追加
- 銘柄別 lot_size、取引コストモデルの拡張
- execution 層（kabuAPI 連携）・monitoring（Slack 通知等）の実装・統合
- 単体テスト・カバレッジ向上と CI/CD の整備

（以上）