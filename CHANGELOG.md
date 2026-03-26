Keep a Changelog に準拠した CHANGELOG.md（日本語）を下記に作成しました。コードベースの内容から推測して記載しています。

Changelog
=========

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
リリースは semver に従います。

[Unreleased]
-------------

なし

0.1.0 - 2026-03-26
------------------

Added
- 初回リリース。パッケージ kabusys v0.1.0 を追加。
- パッケージエントリポイント
  - src/kabusys/__init__.py に __version__ = "0.1.0" と主要サブパッケージの公開設定。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env の読み込み優先順: OS 環境変数 > .env.local > .env。
  - 読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装:
    - export KEY=val 形式対応、クォートおよびエスケープ対応、コメント処理（クォート内を尊重）。
  - 環境変数保護（protected keys）と override ロジック。
  - Settings クラスを提供。主要プロパティ:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env (KABUSYS_ENV の検証: development/paper_trading/live)
    - log_level (LOG_LEVEL の検証)
    - is_live / is_paper / is_dev ヘルパー
  - 必須変数未設定時は ValueError を送出する _require 関数。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に並べ上位 N 件を選定。タイブレークは signal_rank 昇順。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - position_sizing:
    - calc_position_sizes: 発注株数を計算。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率（risk_pct）・損切り率（stop_loss_pct）に基づく算出。
    - equal/score: 資金配分に基づく算出、max_position_pct / max_utilization の適用。
    - lot_size、cost_buffer（手数料・スリッページ見積）を考慮した丸め・スケーリング処理。
    - aggregate cap を超える場合のスケールダウンと残差配分（lot 単位）アルゴリズム実装。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの新規候補を除外（sell_codes を除外して計算）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告して 1.0 にフォールバック。
  - export: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier。

- 戦略（特徴量計算・シグナル生成） (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB を用いたトランザクション単位の置換（DELETE + INSERT）で features テーブルへ書き込み（冪等性確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損は中立値（0.5）で補完。
    - デフォルトのファクター重みを用意し、ユーザー重みをフォールバック・検証・再スケーリングするロジック。
    - Bear レジーム検知時は BUY シグナルを抑制（ai_scores の regime_score 集計に基づく）。
    - BUY は閾値（デフォルト 0.60）で判定、SELL はストップロスやスコア低下判定で生成。
    - positions / prices を参照した売却ロジック（価格欠損時は判定スキップ・features 未登録ポジションは score=0 として SELL）と signals テーブルへの日付単位置換を書き込み。
  - export: build_features, generate_signals。

- リサーチ（ファクター計算・解析） (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を DuckDB SQL で計算（窓関数利用）。
    - calc_volatility: ATR（atr_20）、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 管理含む）。
    - calc_value: raw_financials から最新の財務値を取得し PER, ROE を計算（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を計算する実装（ペア不足時は None）。
    - rank: 同順位は平均ランクで処理（round による丸めで ties を安定化）。
    - factor_summary: 指定列の基本統計量（count/mean/std/min/max/median）を算出。
  - export: calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats 経由）, calc_forward_returns, calc_ic, factor_summary, rank。

- バックテスト (kabusys.backtest)
  - simulator:
    - DailySnapshot / TradeRecord の dataclass 定義。
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理と擬似約定ロジック。
    - execute_orders: SELL を先に処理し全量クローズ、BUY は指定株数で約定。スリッページ（BUY:+, SELL:-）・手数料を適用。lot_size の処理をサポート。
    - 約定記録を trades に保存（commission, realized_pnl の扱いを定義）。
  - metrics:
    - BacktestMetrics dataclass と calc_metrics。
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades の計算実装（履歴・トレードリストから算出）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes
- 一部未実装・既知の設計制約・TODO:
  - risk_adjustment.apply_sector_cap:
    - price_map に 0.0 がある場合、エクスポージャーが過少推定される可能性がありフォールバック実装が必要（TODO コメントあり）。
  - position_sizing:
    - 銘柄別の単元（lot_size）を stocks マスタで持たせる拡張が想定されている（現在は単一 lot_size パラメータ）。
  - signal_generator._generate_sell_signals:
    - トレーリングストップや時間決済（保有期間ベース）の判定は未実装（positions テーブルに peak_price / entry_date が必要）。
  - calc_score_weights:
    - 全スコア合計が 0 の場合は等金額配分にフォールバックし警告を出力する挙動。
  - calc_regime_multiplier:
    - 未知レジームは警告して 1.0 でフォールバックする。
  - feature_engineering:
    - Z スコア正規化と ±3 のクリップを行うため外れ値の影響を抑制する設計。
  - env パーサ:
    - 複雑な .env のパターンに対する堅牢性はあるが、極端なケースで挙動差があり得る（実運用での確認推奨）。

Security
- 初回リリースのため既知のセキュリティ修正はなし。ただし環境変数にトークン・パスワード等を扱うため取り扱いに注意。

---

注: 上記はコードベースの実装内容から推測して作成した CHANGELOG です。設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及がコード内コメントに多数あるため、それらに基づく挙動を反映しています。追加のリリース日や補足情報（リリースノート、互換性ポリシーなど）を提供いただければ、CHANGELOG を更新します。