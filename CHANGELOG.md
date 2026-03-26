CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" の慣例に準拠します。

[0.1.0] - 2026-03-26
-------------------

初回リリース。日本株自動売買フレームワーク "KabuSys" の基礎機能群を実装しました。
主な追加点／仕様は以下の通りです。

### Added
- パッケージ骨格
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開（execution パッケージは定義済み、実装は順次拡張予定）。

- 設定・環境変数管理 (kabusys.config)
  - プロジェクトルート自動検出：.git または pyproject.toml を基準に探索。
  - .env / .env.local 自動読み込み（OS 環境変数を保護する protected ロジックを採用）。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントなどに対応した .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 必須変数未設定時に ValueError を投げる _require ヘルパー。
  - 設定クラス Settings を提供（J-Quants / kabu API / Slack / DB パス / env/log_level 等のプロパティを含む）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値セットに基づく検証と例外）。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定と重み計算（pure function）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補抽出。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率による配分。全銘柄スコアが 0 の場合は等分配にフォールバック（WARNING ログ）。
  - リスク制御（pure function）
    - apply_sector_cap: セクター集中制限。既存保有時価を用いてセクター比率が閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知レジームは 1.0）。
  - ポジションサイズ計算（pure function）
    - calc_position_sizes: allocation_method に応じた発注株数計算（"risk_based", "equal", "score" をサポート）。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金の aggregate cap、cost_buffer を用いた保守的コスト見積り、スケーリングと端数配分ロジックを実装。
    - 価格欠損時のスキップやログ出力。

- 戦略（strategy）
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・最低売買代金）適用、Z スコア正規化、±3 でクリップ、features テーブルへ日付単位の置換（冪等）で保存。
    - DuckDB を使ったデータ取得・トランザクション処理。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネント欠損は中立値（0.5）で補完し不当に降格されないよう設計。
    - final_score に基づく BUY シグナル生成（閾値デフォルト 0.60）。
    - AI ベースのレジーム集計により Bear レジーム時は BUY を抑制。
    - 保有銘柄に対するエグジット判定（ストップロス、スコア低下）を実装し SELL シグナルを生成。
    - signals テーブルへの日付単位置換（冪等）を実装。
    - weights 入力の検査・補完・正規化ロジックを実装（不正値はログでスキップ）。

- リサーチ機能（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算（部分窓対応）。
    - calc_value: raw_financials と当日価格を組み合わせて PER/ROE を算出（EPS が 0/欠損時は None）。
  - 探索・評価ユーティリティ (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（SQL で高速取得）。
    - calc_ic: ランク相関（Spearman ρ）計算。サンプル数が不足する場合は None。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクとする安定なランク関数。
  - zscore_normalize を re-export（kabusys.data.stats 依存）。

- バックテスト (kabusys.backtest)
  - メトリクス計算 (kabusys.backtest.metrics)
    - CAGR、Sharpe、最大ドローダウン、勝率、ペイオフ比、総トレード数を計算するユーティリティを実装。
  - ポートフォリオシミュレータ (kabusys.backtest.simulator)
    - メモリ内でのポートフォリオ状態管理、SELL を先に処理してから BUY を処理する実行順、スリッページ（BUY:+、SELL:-）・手数料率を取り入れた約定処理、TradeRecord/DailySnapshot のデータ構造を提供。
    - SELL は全量クローズ（現状、部分利確やトレーリングは非対応）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Limitations / TODO
- position_sizing:
  - lot_size は現時点で全銘柄共通での扱い。将来的に銘柄別 lot_map に拡張予定（TODO）。
  - price が欠損（0.0）の場合にエクスポージャーが過少評価されてブロックが外れる可能性がある旨を注記（将来的に前日終値や取得原価をフォールバックする検討）。
- signal_generator:
  - トレーリングストップや保有日数に基づく決済は未実装（positions テーブルに peak_price / entry_date が必要）。
  - Bear レジーム判定は ai_scores の regime_score サンプル数依存（閾値未満では Bear とみなさない）。
- feature_engineering / research:
  - 処理は DuckDB 上で完結し、ルックアヘッドバイアスを避ける設計。ただし入力テーブル（prices_daily / raw_financials / ai_scores / features / signals 等）の整合性が前提。
- execution / monitoring:
  - execution パッケージは初期骨格のみ。実際の発注連携やモニタリング周りは今後実装予定。
- API の互換性:
  - すべての公開関数はドキュメント文字列で引数・戻り値の挙動を明記。将来的な変更はBREAKING CHANGE セクションで明示予定。

Acknowledgements
- 本リリースは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）に基づき実装されています。

今後の予定
- execution 層の実装（kabu ステーション等の実取引 API と連携）
- モニタリング・アラート機能の追加（Slack 通知等）
- 銘柄ごとの lot_size マスタ導入、フォールバック価格ロジック、追加のエグジット戦略（トレーリング等）

--------------------------------
（注）この CHANGELOG はコードベースからの推測に基づいて作成しています。実際の変更履歴・コミットログと異なる場合があります。