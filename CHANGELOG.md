# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
リリースはセマンティックバージョニングを想定しています。

## [0.1.0] - 2026-03-22
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主要な機能は設定管理、ファクター計算・特徴量生成、シグナル生成、リサーチユーティリティ、およびバックテストフレームワークです。

### Added
- パッケージ初期化
  - kabusys.__version__ = "0.1.0" を追加。
  - 公開サブパッケージ一覧（data, strategy, execution, monitoring）を __all__ に定義。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（cwd に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を保護する protected 機構を実装。
  - .env パーサーを実装（コメント・export、クォート、エスケープ、インラインコメント等に対応）。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabuステーション / Slack / データベースパス / 環境（development/paper_trading/live） / ログレベル 等をサポート。
    - 必須環境変数未設定時に ValueError を送出する _require() を提供。
    - 値の検証（有効な env 値、ログレベルの検証）を実装。

- 戦略: 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で計算された raw ファクターを取得し、ユニバースフィルタ・正規化・クリップを行い features テーブルへ UPSERT する build_features(conn, target_date) を実装。
  - ユニバースフィルタ（最低株価、20日平均売買代金）を実装。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でのクリップ、トランザクションによる日付単位の置換（冪等）を実装。
  - トランザクション失敗時のロールバックと警告ログを実装。

- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals(conn, target_date, ...) を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算するユーティリティを実装（シグモイド変換、平均化、PER 変換など）。
  - 重みの補完・検証（不正なキー／値をスキップ、合計を 1.0 に再スケール）を実装。
  - Bear レジーム判定（AI の regime_score の平均が負 → BUY 抑制）を実装。サンプル数閾値あり。
  - エグジット判定（ストップロス、スコア低下）を実装。positions / prices に基づく SELL 生成。
  - 生成結果を signals テーブルへ日付単位で置換（トランザクション＋バルク挿入、冪等）する処理を実装。
  - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）を実装。
  - 欠損データに対する中立補完（None → 0.5）やログ出力を実装。

- Research（リサーチ用ユーティリティ） (kabusys.research)
  - ファクター計算モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - momentum: 1M/3M/6M リターン、200日移動平均乖離。
    - volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - value: PER / ROE（raw_financials の最新レコードと当日株価を組み合わせて算出）。
  - 特徴量探索モジュールを実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 将来リターンの一括取得（任意ホライズン、入力検証あり）。
    - IC（Spearman の ρ）計算（結合・欠損除外・最小サンプル数チェック）。
    - 基本統計量サマリー（count/mean/std/min/max/median）。
    - ランク処理は ties を平均ランクで処理し、丸め処理（round(...,12)）で浮動小数点誤差を扱う。
  - research パッケージの __all__ を整備。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ実装（PortfolioSimulator, DailySnapshot, TradeRecord）。
    - execute_orders: SELL を先に処理、BUY は割当額に基づく発注、手数料・スリッページを考慮。
    - BUY の株数不足・資金不足時の再計算処理。
    - SELL は保有全量をクローズ（部分利確/分割は未対応）。
    - mark_to_market: 終値で評価し DailySnapshot を記録（終値欠損時は 0 評価と警告ログ）。
  - バックテストメトリクスを実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - calc_metrics() により DailySnapshot と TradeRecord から BacktestMetrics を生成。
  - バックテストエンジンを実装（run_backtest）。
    - 本番 DB からインメモリ DuckDB へ必要テーブルを日付範囲でコピー（データ汚染回避）。
    - get_trading_days を用いた日次ループ。前日シグナル約定→positions 書き戻し→時価評価→generate_signals→ポジションサイジング→次日発注の一連処理を実装。
    - コピー時に失敗したテーブルは警告ログでスキップする堅牢性。
    - positions の書き戻し、signals の読み取り補助関数を実装。

- パッケージエクスポート
  - 各サブパッケージ（backtest, research, strategy 等）で主要関数／型を __all__ に追加し、上位から import しやすくした。

### Changed
- （初回リリースのため特記なし）

### Fixed
- （初回リリースのため特記なし）

### Notes / Limitations / TODO
- 一部のエグジット条件は未実装（トレーリングストップ、時間決済など）。_generate_sell_signals の docstring に記載。
- generate_signals と build_features は発注実行層（execution）や外部 API には依存しない設計になっている — 発注はバックテストシミュレータや実行層で別途実装する必要あり。
- raw データ（prices_daily, raw_financials, ai_scores, market_calendar 等）のスキーマは外部モジュール（kabusys.data.schema）に依存するため、データ準備が必要。
- 一部ユーティリティは入力データの品質（欠損・不正値）に依存しており、欠損時は None を返すか中立値で補完する挙動を取ります。
- パフォーマンス改善や大規模データ最適化は今後の課題（現在は DuckDB 上のウィンドウ関数・1クエリ取得を多用）。

---

今後の予定（例）
- execution 層の実装（kabuステーション・API との統合）
- モニタリング・通知（Slack 統合など）の追加強化
- 戦略パラメータのチューニング支援ツール、可視化ユーティリティの追加
- 単体テスト / CI の整備とドキュメントの充実

貢献・不具合報告歓迎です。README やドキュメントに沿ってデータ準備を行った上で動作確認してください。