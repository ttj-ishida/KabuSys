# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-22

### Added
- 初期リリース。パッケージ名: `kabusys`（__version__ = 0.1.0）。
- 環境設定・自動読み込み機能（kabusys.config）
  - `.env` / `.env.local` の自動ロード（プロジェクトルートは `.git` または `pyproject.toml` を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env の柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱い）。
  - OS 環境変数を保護する override/protected ロジック。
  - 必須環境変数取得時の明確なエラーメッセージ (_require)。
  - 設定値検証: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - 各種設定プロパティ（J-Quants / kabuAPI / Slack トークン・チャネル、DuckDB / SQLite のパス等）。

- 戦略モジュール（kabusys.strategy）
  - feature_engineering.build_features
    - research モジュールから生ファクターを取得（momentum / volatility / value）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - 指定カラムに対する Z スコア正規化（zscore_normalize を利用）と ±3 クリップ。
    - 日付単位での冪等な features テーブル置換（トランザクション + バルク挿入、エラー時にロールバック）。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - シグモイド変換・欠損補完（欠損コンポーネントは中立 0.5）による final_score 計算。
    - 重みのマージ・検証・再スケーリング機構（デフォルト重みは StrategyModel に基づく）。
    - Bear レジーム判定（ai_scores の regime_score を平均し負なら Bear、最小サンプル数は 3）。
    - BUY シグナル閾値デフォルト 0.60、Bear 時は BUY 抑制。
    - エグジット判定（SELL）実装：ストップロス（-8%）とスコア低下（threshold 未満）。features に存在しない保有銘柄は score=0 として扱うロジック。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。

- リサーチモジュール（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value
    - DuckDB のウィンドウ関数を用いたファクター計算（mom 1/3/6M、MA200乖離、ATR20、avg_turnover、volume_ratio、PER/ROE など）。
    - データ不足時に None を返す堅牢な実装。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary
    - 将来リターンの一括取得（複数ホライズン対応、範囲バッファ付き）。
    - Spearman ランク相関（IC）計算、ランク付け（同順位は平均ランク）、統計サマリー。
    - 外部ライブラリに依存しない純 Python 実装。

- バックテストフレームワーク（kabusys.backtest）
  - engine.run_backtest
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーしてバックテスト実行（features 等は start_date - 300d からのコピー）。
    - 日次ループ: 前日シグナルを始値で約定 → positions を DB に書き戻し → 終値で時価評価 → generate_signals → 発注リスト作成 といった一連の流れを実装。
  - simulator.PortfolioSimulator
    - 擬似約定ロジック（SELL を先、BUY を後で処理）、スリッページ（率）と手数料モデルによる約定価格計算、平均取得単価管理、trade record 作成、mark_to_market による日次スナップショット記録。
    - 部分利確は非対応（SELL は保有全量をクローズ）。
  - metrics.calc_metrics（BacktestMetrics）
    - CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数などの評価指標を計算。

- ロギングとエラーハンドリング
  - 各所で警告ログやデバッグログを充実。トランザクション失敗時のロールバック失敗もログを残す。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

---

注意事項 / 既知の制約
- 一部仕様はドキュメント（StrategyModel.md / BacktestFramework.md 等）を前提に実装されており、該当スキーマ（prices_daily / raw_financials / features / ai_scores / positions / signals / market_calendar 等）が存在することが前提です。
- 未実装の戦術的機能:
  - トレーリングストップ（直近最高値からのトレール）、時間決済（保有日数ベース）は未実装（ソース内コメントで将来的実装予定）。
  - 部分利確・部分損切りは非対応（SELL は現状全量クローズ）。
  - バリュー指標の一部（PBR、配当利回り）は未実装。
- generate_signals は ai_scores が不足している場合でも動作するが、Bear 判定には最小サンプル数が必要（デフォルト 3）。不足時は Bear と判定しない。
- .env 自動ロードはプロジェクトルート探索に失敗した場合はスキップされるため、配布環境では明示的に環境変数を設定することを推奨します。

もし項目の追加や日付・バージョン表記変更、より詳細なリリースノート（例: 各関数の入力/出力例、互換性情報など）をご希望でしたら指示してください。