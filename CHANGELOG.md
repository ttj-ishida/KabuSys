# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

なお、本 CHANGELOG は与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## Unreleased
（なし）

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買システムのコアモジュール群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、公開モジュール一覧を定義。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .git または pyproject.toml を起点にプロジェクトルートを探索する実装（パッケージ配布後も CWD に依存しない）。
    - .env パーサ実装: export プレフィックス、クォート（シェル風のエスケープ処理）、コメント処理等に対応。
    - Settings クラスを提供し、必須設定取得（_require）、値検証（KABUSYS_ENV, LOG_LEVEL）やパス型プロパティ（duckdb/sqlite path）を実装。
    - J-Quants / kabuステーション / Slack / DB パス等の主要設定項目をプロパティとして公開。

- ポートフォリオ構築（ポートフォリオ選定・配分・リスク制御）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選出。タイブレークは signal_rank を利用。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（合計スコアが 0 の場合は等金額にフォールバックし警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するフィルタ。既存ポジションの時価からセクター比率を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投入資金乗数（bull=1.0, neutral=0.7, bear=0.3）＋未知レジームのフォールバックとログ警告。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 銘柄毎の発注株数算出。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による手数料/スリッページの保守的見積り、残差の優先配分ロジック等を実装。

- 戦略（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ、DuckDB に features テーブルとして日付単位の置換（冪等）で保存。
    - DuckDB を用いた価格取得やトランザクション処理（BEGIN/COMMIT/ROLLBACK）を実装。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合成により final_score を算出。
    - AI スコア補完、シグモイド変換、欠損コンポーネントは中立 0.5 で補完するポリシーを実装。
    - Bear レジーム検知（ai_scores の regime_score を集計）により BUY シグナル抑制。
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄を BUY、SELL はエグジット条件（ストップロス・スコア低下）に基づき生成。
    - signals テーブルへ日付単位で置換（冪等）して書き込み。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、ATR/close、平均売買代金、出来高比率）、Value（PER/ROE）等の定量ファクター算出を実装。DuckDB の SQL とウィンドウ関数を活用し、データ不足時は None を返す方針。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）への将来リターンをまとめて取得。
    - calc_ic: スピアマンのランク相関（IC）計算を実装。サンプル不足（<3）の場合は None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（round で丸めて ties を検出）。

- バックテスト関連
  - src/kabusys/backtest/metrics.py
    - BacktestMetrics データクラス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - calc_metrics: DailySnapshot と TradeRecord から各評価指標を計算するユーティリティを実装。
    - 内部関数: CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio の実装。
  - src/kabusys/backtest/simulator.py
    - DailySnapshot / TradeRecord データクラス。
    - PortfolioSimulator: メモリ内ポートフォリオ状態管理と擬似約定ロジックを実装。
    - execute_orders: SELL を先に処理してから BUY（資金確保のため）。スリッページ・手数料モデルを考慮した約定記録を保存する設計。
    - 約定時のスリッページ率（BUY は +、SELL は -）・commission_rate を扱う。

- モジュール公開
  - src/kabusys/portfolio/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py により主要 API を __all__ で公開。

### Notes / Known limitations
- apply_sector_cap 内の価格欠損時の挙動について注記（price が 0.0 の場合はエクスポージャーが過小見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO が残っています）。
- signal_generator のエグジット判定では、現状トレーリングストップや時間決済（保有日数ベース）は未実装。これらは positions テーブルに peak_price / entry_date 等が必要で拡張が想定されている旨の注記あり。
- position_sizing の lot_size は全銘柄共通で扱う設計。将来的に銘柄毎の単元情報を受け取る設計への拡張が示唆されています（TODO）。
- feature_engineering は zscore_normalize（kabusys.data.stats に実装）に依存。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB のみで実装する方針。
- トランザクション処理（BEGIN/COMMIT/ROLLBACK）を使用しているため、DuckDB 側の接続/トランザクション環境に依存する点に注意。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

この CHANGELOG はコード内のコメントや実装から推測して作成しています。運用に際しては実際のリリース日付や変更内容をプロジェクトのリリースポリシーに従って更新してください。