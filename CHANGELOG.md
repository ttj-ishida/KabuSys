CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、バージョニングは SemVer を想定します。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ初回リリース（kabusys 0.1.0）。
- 基本パッケージ構成を追加:
  - kabusys.__init__ にバージョンと公開サブパッケージのエクスポート定義を追加。
- 設定管理:
  - kabusys.config: .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを実装し、J-Quants・kabu API・Slack・データベースパス・環境モード・ログレベル等の取得とバリデーションを提供。
  - 必須環境変数未設定時は ValueError を送出する _require ユーティリティを追加。
- ポートフォリオ構築（純粋関数群、DB非依存）:
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが0の際は等配分へフォールバック（WARNING）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash に収まるようスケーリング）、cost_buffer による保守的コスト見積りをサポート。
    - risk_based: 許容リスク率・損切り率を用いた株数算出。
    - 将来拡張メモ: 銘柄別 lot_size マップ等を想定した TODO を含む。
- 戦略（feature / signal）:
  - kabusys.strategy.feature_engineering:
    - build_features: research 層からの生ファクターを統合し、ユニバースフィルタ（最低株価・最低売買代金）、Zスコア正規化、±3 クリップを経て features テーブルへ日付単位の置換（トランザクション＋バルク挿入）で保存。DuckDB を使用。
  - kabusys.strategy.signal_generator:
    - generate_signals: features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを算出、重み付き合算で final_score を計算。デフォルト重みと閾値（0.60）を提供し、ユーザー重みを安全にマージ・正規化。
    - Bear レジーム検出時は BUY シグナルを抑制（ai_scores の regime_score 集計に基づく）。
    - SELL シグナルはストップロス（-8%）とスコア低下で判定。保有銘柄の価格欠損時は SELL 判定をスキップする安全策あり。
    - signals テーブルへ日付単位置換（トランザクション・ROLLBACK ハンドリング）で書き込み。
    - 未実装コメント: トレーリングストップや時間決済については TODO（positions に peak_price/entry_date が必要）。
- リサーチユーティリティ:
  - kabusys.research.factor_research:
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials のみ参照）。MA200、ATR20、出来高/売買代金指標、PER/ROE などを計算。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得するクエリ実装（ホライズン検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算を実装（同順位は平均ランク対応）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで扱うランク関数を提供。
  - zscore_normalize を public API として再エクスポート。
- バックテスト:
  - kabusys.backtest.metrics:
    - BacktestMetrics データクラスと各種指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）算出ロジックを実装。
  - kabusys.backtest.simulator:
    - PortfolioSimulator: 擬似約定ロジック（SELL を先に、BUY を後に実行）、スリッページおよび手数料モデル考慮、DailySnapshot と TradeRecord の定義を実装。約定時の安全チェック（価格欠損等）や lot_size のサポートあり。
- DB 操作の原子性:
  - features / signals 等の書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）＋バルク挿入で日付単位の置換を行い、途中失敗時は ROLLBACK を試行して安全性を確保。ROLLBACK 失敗はログ警告。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known limitations
- position_sizing の lot_size は現状グローバル固定で銘柄別単元対応は未実装（将来拡張予定）。
- apply_sector_cap のエクスポージャ算出は price_map に依存しており、price が欠損（0.0）の場合は過少見積りとなる旨の TODO コメントあり。前日終値や取得原価を用いるフォールバックは未実装。
- generate_signals の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルの追加情報が必要。
- research / strategy / backtest いずれも DuckDB 接続や prices_daily 等のテーブルに依存。実行前に適切なスキーマとデータ準備が必要。
- .env パーサは多くのケースに対応するが、複雑なシェル展開等の完全互換は意図していない。

---

この CHANGELOG は提示されたコードベースの実装内容から推測して作成しています。実際のリリースノートは開発履歴・コミットログに基づいて調整してください。