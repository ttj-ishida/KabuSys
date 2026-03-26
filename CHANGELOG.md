CHANGELOG.md

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
- なし

[0.1.0] - 2026-03-26
-------------------
Added
- 初回リリース: KabuSys 日本株自動売買ライブラリ v0.1.0 を追加。
- パッケージエントリポイント:
  - kabusys.__version__ = "0.1.0"
  - パブリックモジュール: data, strategy, execution, monitoring（__all__ にて公開）
- 環境設定:
  - kabusys.config:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val 形式やクォート、コメントの扱いを考慮した .env パーサ実装。
    - .env 読み込みに際して OS 環境変数を保護する機能（protected set）。
    - 必須環境変数取得ヘルパー _require と Settings クラス。J-Quants / kabu API / Slack / DB パス / 環境フラグ（development/paper_trading/live）やログレベルの検証を提供。
- ポートフォリオ構築:
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順（同点は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等配分へフォールバック（WARNING ログ）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクターエクスポージャーに基づき、新規候補を除外するセクター上限適用（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知レジームはフォールバック 1.0、bear→0.3 等）。未知レジームでの警告ログあり。
    - セクター計算で価格欠損時の未対応箇所（将来的に前日終値や取得原価でのフォールバックを想定）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
    - risk_based: 許容リスク率、ストップロス率からベース株数算出。単元（lot_size）で丸め。
    - equal/score: 重みからポジション配分を算出し、per-position 上限（max_position_pct）と aggregate cap（available_cash）を考慮。
    - aggregate cap 超過時はスケーリングして、lot_size 単位の再配分を残差順に実施。cost_buffer で手数料/スリッページを保守的に見積もり。
    - 将来的な拡張点として銘柄別 lot_size の導入予定（TODO コメントあり）。
- 戦略（Strategy）:
  - kabusys.strategy.feature_engineering:
    - build_features: research 側の生ファクターを取得（calc_momentum / calc_volatility / calc_value）、ユニバースフィルタ（最低株価・最低平均売買代金）を適用し、指定カラムを Z スコア正規化、±3 でクリップして features テーブルへ UPSERT（DuckDB を使用）。処理は target_date 時点のデータのみを使用し冪等（削除→挿入）。
    - ユニバース閾値: _MIN_PRICE=300 円、_MIN_TURNOVER=5e8（5 億円）。
  - kabusys.strategy.signal_generator:
    - generate_signals: features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを重み付き合算して final_score を算出。
    - デフォルト重みは StrategyModel.md に準拠（momentum=0.40 等）。ユーザ指定 weights は検証・補完され合計が 1.0 でない場合は再スケール。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値以上）。Bear の場合は BUY シグナルを抑制。
    - BUY: threshold（デフォルト 0.60）を超える銘柄をランク付きで BUY シグナル化（SELL 対象を優先して除外）。
    - SELL: エグジット判定としてストップロス（終値 / avg_price - 1 < -8%）とスコア低下（final_score < threshold）を実装。未実装のエグジット（トレーリングストップ、時間決済）はコメントで明示。
    - signals テーブルへの日付単位の置換（トランザクションで原子性確保）。
    - features が空の場合は BUY を生成せず SELL 判定のみ実施（警告ログ）。
- リサーチ（Research）:
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算（データ不足は None）。
    - calc_volatility: ATR20（平均 true range）、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS=0 の場合は None）。PBR/配当利回りは未実装。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。サンプル数 3 未満で None。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで扱う実装（丸めで ties 対応）。
  - 研究用関数群は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照。外部ライブラリ（pandas 等）には依存しない設計。
- バックテスト（Backtest）:
  - kabusys.backtest.metrics:
    - バックテスト評価指標を計算するユーティリティ（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 実装上の注意: データ不足やゼロ分散等に対する安全措置あり（0.0 を返す）。
  - kabusys.backtest.simulator:
    - PortfolioSimulator: メモリ内でポートフォリオ状態管理と擬似約定を実施。DailySnapshot / TradeRecord dataclass を定義。
    - execute_orders: SELL を先に全量クローズ、その後 BUY（部分利確・部分損切り・分割約定の一部は未対応）。スリッページ・手数料モデルを考慮し TradeRecord を記録。lot_size による丸め対応。
- モジュールエクスポート:
  - strategy と research の主要 API をパッケージ __init__ で公開（例: build_features, generate_signals, calc_momentum 等）。

Known limitations / Notes
- apply_sector_cap: price_map に価格欠損（0.0）があるとエクスポージャーが過小評価され、ブロックされない可能性がある（将来のフォールバック価格導入を検討）。
- position_sizing: 現状単一 lot_size を全銘柄共通で扱う。将来的に銘柄別 lot_map を受け取る拡張を検討中（TODO）。
- signal_generator:
  - AI ニューススコアがない銘柄は中立（0.5）で補完。
  - SELL のトレーリングストップ / 時間決済は未実装（コメントにて明示）。
- feature_engineering は zscore_normalize を kabusys.data.stats から利用する前提。外部データソースは DuckDB 内のテーブル（prices_daily / raw_financials）に限定。
- 一部の関数は入力データの欠損・非数値を慎重に扱うが、実運用では入力データの前処理とデータ品質チェックを推奨。
- 標準出力やログレベルのデフォルトは Settings.log_level で制御。開発・テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で .env 自動読み込みを無効化可。

参考
- このリリースはコードベースの初期実装（v0.1.0）を反映しています。将来的なリリースでは以下のような改善を予定:
  - 銘柄別単元（lot_size）と取引コストの精緻化
  - apply_sector_cap の価格フォールバック実装
  - SELL ポリシー（トレーリングストップ、時間決済）と部分利確の対応
  - execution 層（kabu API 連携）と monitoring（Slack 通知等）の統合

（以上）