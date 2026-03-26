# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、この CHANGELOG はコードベースから推測して自動生成しています（実装内容・ドキュメント文字列に基づく要約）。APIや挙動の正確な仕様はソースコードを参照してください。

## [Unreleased]

（今後の変更・修正をここに記載）

---

## [0.1.0] - 2026-03-26

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

### Added
- パッケージ初期化
  - kabusys のパッケージメタデータとして __version__ = "0.1.0" を定義。
  - 公開モジュール一覧として __all__ に data, strategy, execution, monitoring を設定。

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml による）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント処理など）。
  - 環境変数の保護（既存 OS 環境変数を protected として扱う上書き制御）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB パス / システム設定等の取得 API を提供。
  - 必須変数未設定時は ValueError を送出する _require 関数を提供。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。

- ポートフォリオ構築ロジック（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順、同点は signal_rank でタイブレークして上位 N を選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等分配へフォールバックし WARNING を出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター別集中リスク制限。既存保有のセクターエクスポージャーを計算し閾値超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を用いた保守的見積り、スケールダウン時の残差処理（fractional の優先配分）を実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research モジュールの生ファクター（momentum/volatility/value）を統合してユニバースフィルタ（最低株価・流動性）適用、Zスコア正規化、±3 クリップ、features テーブルへの日付単位の置換（冪等）を実装。
  - 正規化対象カラムやフィルタ閾値（_MIN_PRICE=300 円, _MIN_TURNOVER=5e8）を定義。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
  - ファクター重みのマージ／正規化、無効なユーザー重みの無視と警告出力。
  - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）と sigmoid / 平均での合成。
  - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
  - SELL 判定ロジック（ストップロス: -8%／スコア低下）を実装。features に存在しない保有銘柄は score=0 と見なして SELL 判定。
  - 未実装のエグジット条件（トレーリングストップ、時間決済）は注記あり。

- リサーチ機能（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装し、prices_daily / raw_financials から各種ファクター（mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe）を算出。
    - データ不足時の None ハンドリング。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括取得するクエリを実装。
    - calc_ic: スピアマンランク相関（IC）を実装。サンプル不足時は None を返す。
    - rank: 同順位は平均ランクとするランク化実装（丸めで ties 対応）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - 研究ユーティリティ zscore_normalize をデータモジュールからエクスポート（kabusys.data.stats を経由）。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator クラスを実装（メモリ内状態管理）。DailySnapshot / TradeRecord のデータクラスを定義。
    - execute_orders: SELL を先行処理してから BUY を処理するワークフロー、スリッページ・手数料率を適用した約定処理、SELL は保有全量クローズ（部分利確未対応）などを実装。
  - metrics:
    - calc_metrics と内部計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を実装。

- パッケージのエクスポート整備
  - kabusys.portfolio/__init__.py, kabusys.strategy/__init__.py, kabusys.research/__init__.py により主要 API を公開。

### Changed
- 初期リリースにつき「変更点」は該当なし。

### Fixed
- 初期リリースにつき「修正点」は該当なし。

### Known limitations / Notes (ドキュメントに明記)
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされる（配布環境での挙動を考慮）。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターのコードにはセクター上限が適用されない設計（明示的に除外）。
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格の導入を検討。
- strategy.signal_generator:
  - トレーリングストップや時間決済などの一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
  - AI ニューススコアが未登録の場合は中立値 0.5 で補完する設計。
- position_sizing:
  - lot_size は全銘柄共通の単位（現在は共通の lot_size 引数で対応）。将来的に銘柄別 lot_map の導入を想定する TODO コメントあり。
- バックテストの約定ロジック:
  - SELL は現状「全量クローズ」のみ。部分約定や分割売買は未対応。
- 一部関数は debug/info/warning のログ出力を行うが、詳細なログポリシーは運用で調整が必要。

### Security
- 初版リリースにおける既知のセキュリティ問題はなし。設定情報（トークン等）は Settings 経由で環境変数から取得するため、運用時は .env の取り扱いに注意すること。

---

今後のリリースでは以下を想定:
- トレーリングストップや時間決済などの追加エグジットロジック実装
- 銘柄別 lot_size / 手数料モデルの柔軟化
- .env 取り扱い・パスワード管理（OS シークレットストア等）拡張
- execution 層・monitoring 層の具体的な API 実装（現状はパッケージ構成のみ）