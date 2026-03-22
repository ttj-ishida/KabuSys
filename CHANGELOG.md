# CHANGELOG

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、以下はコードベースから推測して作成した変更履歴です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-22
最初のリリース。日本株自動売買システムのコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
  - 公開 API として data / strategy / execution / monitoring をエクスポート。

- 環境設定管理
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装（src/kabusys/config.py）。
    - プロジェクトルート判定: .git または pyproject.toml を起点に検索する _find_project_root() を導入。
    - .env パース実装: コメント・export プレフィックス・シングル/ダブルクォートとエスケープに対応する _parse_env_line() を実装。
    - .env の読み込み順序: OS環境変数 > .env.local > .env。既存の OS 環境変数は保護（protected）され上書きされない。
    - 自動ロードの無効化オプション: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による抑制。
    - 必須設定の取得ヘルパー _require() と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 環境フラグなどのプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の検証（指定値以外は ValueError）。

- 戦略：特徴量エンジニアリング
  - build_features(conn, target_date) を実装（src/kabusys/strategy/feature_engineering.py）。
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 定義済み数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位で features テーブルへ UPSERT（トランザクションで DELETE → INSERT、冪等性を保証）。
    - ルックアヘッド防止のため target_date 時点のデータのみ参照。

- 戦略：シグナル生成
  - generate_signals(conn, target_date, threshold, weights) を実装（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合して複数コンポーネント（momentum / value / volatility / liquidity / news）のスコアを計算。
    - コンポーネントごとの変換関数（シグモイド、PER→value スコア、ボラティリティ反転など）を実装。
    - デフォルト重み _DEFAULT_WEIGHTS と閾値 _DEFAULT_THRESHOLD（0.60）を導入。外部から重みを与えた場合の検証・正規化（合計が 1.0 になるよう再スケール）を実施。
    - Bear レジーム検知（ai_scores の regime_score 平均 < 0、サンプル数閾値あり）により BUY シグナルを抑制するロジックを追加。
    - BUY シグナルは最終スコア >= threshold で生成（rank を付与）。SELL シグナルは保有ポジションをチェックしてストップロス（-8%）やスコア低下で生成。
    - SELL が優先されるよう BUY から除外し rank を再付与。
    - 日付単位で signals テーブルへ置換（トランザクションで DELETE → INSERT、冪等性）。

- Research（リサーチ）機能
  - factor_research モジュールを実装（src/kabusys/research/factor_research.py）。
    - calc_momentum(conn, target_date): 約1/3/6ヶ月リターン、200日移動平均乖離率を計算。
    - calc_volatility(conn, target_date): 20日 ATR / close（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 処理を慎重に実装。
    - calc_value(conn, target_date): raw_financials から最新の財務データを取得し PER / ROE を計算。EPS が無効な場合は None。
    - DuckDB SQL を用いた実装で prices_daily / raw_financials のみ参照。ルックアヘッド防止の設計。

  - feature_exploration（src/kabusys/research/feature_exploration.py）を実装。
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの妥当性チェックあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン相関（Information Coefficient）をランクで計算する実装。
    - factor_summary(records, columns): 各ファクター列の count/mean/std/min/max/median を計算。
    - rank(values): 同順位は平均ランクとする安定なランク付けユーティリティ（丸めで ties の検出漏れを防止）。
    - 研究向けに外部依存を持たない純粋な Python 実装。

  - research パッケージのエクスポートを追加（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- バックテストフレームワーク
  - simulator（src/kabusys/backtest/simulator.py）
    - DailySnapshot / TradeRecord データクラスを追加。
    - PortfolioSimulator クラスを実装。メモリ内での保有管理、約定シミュレーション、約定記録、時価評価を提供。
    - execute_orders で SELL を先に処理、BUY は資金と手数料を考慮して株数を計算（端数切り捨て）。SELL は保有全量クローズ（部分利確非対応）。
    - スリッページと手数料（commission_rate）を考慮し、取引記録（TradeRecord）を保持。
    - mark_to_market で終値評価、終値欠損時は警告を出し 0 評価。

  - metrics（src/kabusys/backtest/metrics.py）
    - BacktestMetrics データクラスを導入（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - calc_metrics(history, trades) により上記メトリクスを計算するユーティリティを実装。
    - 内部に CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio の実装を提供。実装は入力が不十分な場合に安全に 0.0 を返す設計。

  - engine（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...) を実装。
      - 本番 DuckDB から必要データを期間フィルタしてインメモリ DuckDB にコピー（_build_backtest_conn）。
      - 日次ループ: 前日のシグナルを当日始値で約定 → positions テーブルを書き戻し → 終値で時価評価を記録 → generate_signals を実行 → シグナルに基づき注文リスト作成・次日約定準備。
      - _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals の補助関数を追加。
      - バックテスト用に market_calendar を含めた安全なデータコピーを実施し、本番テーブルを汚染しない設計。

- パッケージのエクスポート
  - backtest パッケージの __init__ にて run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics を公開。

### Changed
- （初版につき該当なし）

### Fixed
- .env 読み込みでファイルオープンに失敗した際に warnings.warn を出すようにして読み込み失敗を静かに扱う。これにより環境がない場合でもプロセス継続が容易。

### Security
- （該当なし）

### Notes / デザイン上の重要な決定
- ルックアヘッドバイアス回避：全ての戦略・リサーチ関数は target_date 時点までのデータのみ参照するように設計。
- 冪等性：features / signals / positions など日付単位で DELETE → INSERT を行いトランザクションで保護している（原子操作）。
- 欠損データの取り扱い：コンポーネントスコアの欠損は中立値 0.5 で補完して不当な降格を防止。features に存在しない保有銘柄は final_score=0.0 扱いで SELL 判定の対象となる。
- 外部依存の最小化：研究用モジュールは pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。
- パラメータのデフォルト値：BUY閾値 0.60、ストップロス -8%、Zスコアクリップ ±3、ユニバースフィルタの閾値（300円、5億円）などはコード中の定数として明示。

もし追加でリリースノートの粒度を調整したい（モジュール別に詳細化、既知の制限や TODO を追記する等）があれば指示ください。