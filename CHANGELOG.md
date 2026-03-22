# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- （次回以降の変更をここに記載）

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買フレームワークの基盤機能を実装しています。主な追加点と設計上の要点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）とモジュールエクスポート（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準に探索）。
  - .env パース機能（export 形式、クォート、エスケープ、インラインコメント対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - Settings クラス：J-Quants / kabu API / Slack / DB パス / 環境（KABUSYS_ENV）/ ログレベル（LOG_LEVEL）等のプロパティを提供。必須環境変数は未設定時に ValueError を送出。
- 戦略（kabusys.strategy）
  - feature_engineering.build_features
    - Research で生成した raw ファクター（momentum / volatility / value）を読み取り、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
    - 日付単位で features テーブルへ置換（DELETE + INSERT、トランザクションで原子性を保証）。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - 標準重み（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）を持ち、ユーザ提供の weights を検証・統合・再スケール。
    - final_score に基づく BUY シグナル生成（閾値デフォルト 0.60）、Bear レジーム検知時は BUY を抑制。
    - 保有ポジションのエグジット判定（ストップロス -8% / スコア低下）により SELL シグナルを生成。
    - signals テーブルへ日付単位の置換で書き込み（トランザクションで原子性）。
- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクターを算出（MA200, ATR20, PER 等）。
  - feature_exploration: calc_forward_returns（複数ホライズンに対応した将来リターン取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランクで処理）。
  - research パッケージの __all__ エクスポートを整備。
- バックテスト（kabusys.backtest）
  - simulator: PortfolioSimulator、DailySnapshot、TradeRecord の実装。売買の擬似約定（スリッページ・手数料モデル）、マーク・トゥ・マーケット、トレード記録を提供。
  - metrics: calc_metrics を含む各種評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - engine: run_backtest の実装
    - 本番 DB からインメモリ DuckDB へデータをコピー（signals/positions を汚さない設計）。
    - 日次ループ：前日シグナル約定 → positions 書き戻し → マーク・トゥ・マーケット → generate_signals 実行 → ポジションサイジング → 約定 のフローを実行。
    - 補助関数: _build_backtest_conn（データの範囲フィルタ付きコピー）、_fetch_open_prices / _fetch_close_prices、_write_positions（冪等書き込み）、_read_day_signals などを提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込みで OS 環境変数を保護する仕組み（.env/.env.local の読み込み時に既存の OS 環境変数キーを protected として扱う）を導入。

### Implementation notes / 設計上のポイント
- ルックアヘッドバイアス回避:
  - ファクター計算・シグナル生成は target_date 時点のデータのみを参照する設計。
- 原子性と冪等性:
  - features / signals / positions への日付単位置換は DELETE/INSERT をトランザクションで行い、ロールバック時に警告を出す等の保護を実装。
- 欠損値と不正データの扱い:
  - ファクター欠損は中立値（0.5）で補完する方針（銘柄の過度な降格を防止）。
  - 非数値/NaN/Inf/負の重みなどを weights 設定時に検証・無視、合計が 1.0 でない場合は再スケール。
- パフォーマンス配慮:
  - DuckDB を利用し、SQL ウィンドウ関数や一括取得で計算を効率化。バックテスト用には必要範囲のみをコピーしてメモリ内で実行。

### Known limitations / 今後の課題
- signal_generator のエグジット条件でトレーリングストップや時間決済は未実装（要 positions に peak_price / entry_date の拡張）。
- feature_exploration は標準ライブラリのみで実装しており、大規模なデータ処理や可視化のためには追加ツール（pandas 等）の導入が検討される場合あり。
- execution / monitoring 周りのモジュールはパッケージ構成に存在するが、本リリースでは発注 API への直接呼び出しを行わない設計（execution 層の実装は別途）。

---

（注）本 CHANGELOG はソースコード注釈・docstring と実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリースプロセスや変更履歴の公式記録と照合してください。