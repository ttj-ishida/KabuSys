# Changelog

すべての日付は YYYY-MM-DD 形式。  
このファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-22
初回リリース。日本株向けの自動売買（研究・バックテスト・戦略実行）ライブラリの基盤機能を追加。

### Added
- パッケージのバージョン定義
  - kabusys.__version__ = "0.1.0"

- 環境設定 / 読み込み
  - kabusys.config: .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みの探索はパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を再帰的に特定。
  - .env のパース機能を実装：
    - export KEY=val 形式対応
    - シングル/ダブルクォート文字列対応（バックスラッシュエスケープ処理）
    - インラインコメントの扱い（クォート外かつ '#' の前が空白/タブの場合はコメントと扱う）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスに環境変数マッピングを追加（必須値は未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development|paper_trading|live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - ヘルパー: is_live / is_paper / is_dev

- 戦略関連（特徴量構築・シグナル生成）
  - kabusys.strategy.feature_engineering.build_features:
    - research で計算した生ファクター（momentum / volatility / value）を取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（冪等、トランザクション + バルク挿入で原子性を確保）。
    - ユニバース閾値: 最低株価 300 円、20 日平均売買代金 5 億円、Z スコアクリップ ±3。
  - kabusys.strategy.signal_generator.generate_signals:
    - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算して final_score を算出。
    - デフォルト重みを実装（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。ユーザ指定 weights を検証して正規化（合計が 1 に再スケール）。
    - Sigmoid 変換、欠損コンポーネントの中立補完（0.5）によるスコア計算。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数 >= 3 の場合）により BUY シグナルを抑制。
    - SELL シグナル生成（ストップロス -8%、final_score が閾値未満）。
    - signals テーブルへ日付単位で置換（冪等）。
    - デフォルト BUY 閾値: 0.60

- 研究用ファクター計算 / 特徴量解析
  - kabusys.research.factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高変化率（volume_ratio）を計算。true_range の NULL 伝播を制御してカウントを正確に扱う。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得して PER/ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、欠損や条件不足時は None を返す。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。有効レコードが 3 未満の場合は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と各ファクター列の統計サマリー（count/mean/std/min/max/median）。
    - ランク計算は浮動小数の丸め（round(..., 12)）を行い ties の検出を安定化。

- バックテストフレームワーク
  - kabusys.backtest.simulator:
    - PortfolioSimulator: メモリ内でポートフォリオ状態管理、BUY/SELL 約定ロジック、スリッページ・手数料モデル、約定記録（TradeRecord）と日次スナップショット（DailySnapshot）を実装。
    - execute_orders: SELL を先に処理、BUY は資金に応じて株数を切り下げる。部分利確/部分損切りは未対応（SELL は全量クローズ）。
    - mark_to_market: 終値で評価、終値欠損時は 0 評価して警告ログ出力。
  - kabusys.backtest.metrics:
    - calc_metrics: history / trades から CAGR, Sharpe Ratio（無リスク金利=0, 年次化: sqrt(252)）、Max Drawdown、勝率、Payoff Ratio、トレード数を計算。
  - kabusys.backtest.engine.run_backtest:
    - 本番 DuckDB から必要テーブルを期間フィルタしてインメモリ DuckDB にコピーしバックテストを実行（signals/positions を汚染しない）。
    - コピー対象: prices_daily, features, ai_scores, market_regime（期間フィルタ）、market_calendar（全件コピー）。
    - 日次ループ: 前日シグナルの当日始値約定 → positions の書き戻し → 終値で時価評価記録 → generate_signals 呼び出し → 発注リスト組立て（サイジング, max_position_pct を尊重）。
    - 各種補助関数: _fetch_open_prices/_fetch_close_prices/_write_positions/_read_day_signals を実装。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20

- パッケージエクスポート
  - kabusys.strategy: build_features, generate_signals を公開
  - kabusys.research: 主要な解析・ファクター関数を __all__ に登録
  - kabusys.backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

既知の制限・未実装の機能（今後の改善候補）
- signal_generator のエグジット条件にコメントで示された「トレーリングストップ（直近最高値から -10%）」や「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date 等の情報が必要。
- PortfolioSimulator の BUY ロジックは部分買付を行わず、割り当て金額を基に整数株数を floor で算出。小口株・信用等には未対応。
- calc_forward_returns は営業日を厳密に数えるのではなく、prices_daily の連続レコード数（LEAD/LAG）に依存する。市場カレンダーの特殊ケースは今後の検証が必要。
- .env パーサーは多くの一般的ケースに対応するが、非常に複雑なシェル構文すべてをサポートするものではない。

貢献・バグ報告
- バグや改善提案は issue を立ててください。README / ドキュメントに実行例やスキーマ定義（data/schema）を今後追加予定です。