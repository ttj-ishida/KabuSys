Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマットの解説: https://keepachangelog.com/ja/1.0.0/

[Unreleased]

0.1.0 - 2026-03-26
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本モジュール群を実装。
- パッケージメタ:
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パッケージ公開用エクスポート: data, strategy, execution, monitoring を想定。
- 設定管理:
  - .env / .env.local ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索、環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（src/kabusys/config.py）。
  - .env パーサーは export 形式やクォート・エスケープ・行内コメントの取り扱いに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル等のプロパティを検証付きで取得可能。
- ポートフォリオ構築（純粋関数群、メモリ内計算）:
  - 候補選定: select_candidates（スコア降順、signal_rank によるタイブレーク） （src/kabusys/portfolio/portfolio_builder.py）
  - 重み算出: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分配へフォールバック） （src/kabusys/portfolio/portfolio_builder.py）
  - リスク調整: apply_sector_cap（セクター集中上限チェック、売却予定銘柄を除外可能）、calc_regime_multiplier（市場レジーム別の乗数: bull/neutral/bear） （src/kabusys/portfolio/risk_adjustment.py）
  - 口数決定（position sizing）: calc_position_sizes
    - allocation_method による分岐（risk_based / equal / score）。
    - 単元株（lot_size）丸め、銘柄別上限（max_position_pct）、投下資金の aggregate cap とスケーリング、cost_buffer による保守的コスト見積りを実装（src/kabusys/portfolio/position_sizing.py）。
- 戦略（特徴量生成・シグナル生成）:
  - feature_engineering.build_features:
    - research モジュールで算出したファクターを結合し、ユニバースフィルタ（最低株価・最低売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ、DuckDB の features テーブルへ日付単位で冪等に UPSERT（src/kabusys/strategy/feature_engineering.py）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して要素スコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みのマージ・正規化、Bear レジーム時の BUY 抑制、閾値超過で BUY、エグジット条件（ストップロス・スコア低下）で SELL を判定。
    - signals テーブルへ日付単位で冪等書き込み（src/kabusys/strategy/signal_generator.py）。
- リサーチ機能:
  - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照し、各種ファクターを SQL + Python で算出） （src/kabusys/research/factor_research.py）。
  - feature_exploration: 将来リターン計算 calc_forward_returns、IC（Spearman）計算 calc_ic、統計サマリー factor_summary、rank ヘルパー （src/kabusys/research/feature_exploration.py）。
  - research パッケージのエクスポート整備（src/kabusys/research/__init__.py）。
- バックテスト / シミュレーション:
  - PortfolioSimulator（擬似約定、ポートフォリオ状態管理）:
    - SELL を先に処理してから BUY（資金確保）、スリッページ・手数料モデル、TradeRecord/ DailySnapshot を記録（src/kabusys/backtest/simulator.py）。
  - バックテスト指標: calc_metrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）と内部計算関数群（src/kabusys/backtest/metrics.py）。
- ロギングを広く使用し、入力検証や欠損時の動作（スキップ/警告）を明示。

Changed
- 初版のため既存バージョンからの変更点はなし。

Fixed
- 初版のため既存不具合の修正履歴はなし。

Known issues / TODO
- セクターエクスポージャー計算で価格が欠損（0.0）の場合に過小評価となる可能性がある（将来的に前日終値や取得原価などのフォールバックを検討）。（src/kabusys/portfolio/risk_adjustment.py）
- position_sizing: 将来的に銘柄別 lot_size をサポートする設計への拡張がコメントで示されている。（src/kabusys/portfolio/position_sizing.py）
- signal_generator のエグジットでトレーリングストップや時間決済は未実装。positions テーブルに peak_price / entry_date が必要となる（実装 TODO）（src/kabusys/strategy/signal_generator.py）。
- execution モジュールの一部（src/kabusys/execution/）は未実装または省略されている可能性がある（コードベースに空の __init__ や未完の関数断片あり）。
- data.stats.zscore_normalize など外部モジュール（kabusys.data）が存在する前提。実行環境の DuckDB テーブルスキーマ（prices_daily, features, ai_scores, positions, raw_financials 等）の準備が必要。

Developer notes
- 自動 .env 読み込みはプロジェクトルート探索を用いるため、パッケージ配布後も CWD に依存せず動作することを意図している。
- 環境変数の必須チェックは Settings._require にて行われ、未設定時は ValueError を投げる。
- 戦略・ポートフォリオ計算は設計上、DB 参照を限定し（主に DuckDB）、発注 API や execution 層への依存を持たない純粋関数として設計されている。

Acknowledgements
- 本リリースは初期実装であり、実運用前に統合テスト・データ依存性の確認・エッジケース検証を推奨します。