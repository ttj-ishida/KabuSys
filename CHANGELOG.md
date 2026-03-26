# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
各バージョンについて「Added / Changed / Fixed / Deprecated / Removed / Security」のカテゴリで要約しています。

## [Unreleased]

- （現在のリポジトリ状態はバージョン 0.1.0 として初版が実装済みのため、未リリースの差分はありません。）

## [0.1.0] - 2026-03-26

### Added
- パッケージ基本情報
  - パッケージ名: KabuSys。バージョン 0.1.0 を src/kabusys/__init__.py に定義。
  - モジュール群を __all__ で公開: data, strategy, execution, monitoring。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: __file__ から親ディレクトリを探索し `.git` または `pyproject.toml` を基準にルートを特定（配布後でも CWD に依存しない実装）。
  - .env のパーサを実装（クォート、エスケープ、インラインコメント、export プレフィックスに対応）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - Settings クラス実装: 必須環境変数取得（_require）、既定値、型変換、検証（KABUSYS_ENV, LOG_LEVEL 等）、Path 型の DB パス取得（duckdb/sqlite）。
  - 環境値検証: env 値の有効範囲チェック、ログレベルの検査とエラー報告。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順かつ tie-breaker に signal_rank を使用してトップ N を選択。
    - calc_equal_weights: 等金額配分（1/N）を返す。
    - calc_score_weights: スコア加重配分を実装。全スコアが 0 の場合は等金額配分へフォールバックし警告ログを出力。
  - risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、既存ポジション比率が上限（デフォルト 30%）を超えるセクターの新規候補を除外する。sell 対象はエクスポージャー計算から除外可能。"unknown" セクターは制限対象外とする。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 でフォールバック。
  - position_sizing
    - calc_position_sizes: 重み・候補・現金・既存ポジション・価格情報に基づき発注株数を計算。
      - allocation_method に "risk_based" と "equal"/"score" をサポート。
      - risk_based: 許容リスク率・stop_loss を用いた計算。
      - per-position 上限（max_position_pct）・aggregate cap（available_cash）・lot_size による丸め処理を実装。
      - cost_buffer により手数料・スリッページを保守的に見積もり、合計投資額が available_cash を超える場合はスケーリングと lot_size 単位での再配分を実行。
      - 将来の拡張ポイント（銘柄別 lot_size 等）は TODO コメントで明示。

- ストラテジー（src/kabusys/strategy/*）
  - feature_engineering
    - build_features: research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化、±3 でクリップした上で features テーブルへ日付単位の置換（冪等）で保存。DuckDB トランザクションで原子性を確保。
    - ユニバース基準の定数（最低価格 300 円、20 日平均売買代金 5 億円等）を定義。
  - signal_generator
    - generate_signals: features と ai_scores を統合して各銘柄の final_score を計算し BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存。
    - ファクター重みのマージ・検証・再スケーリング処理（無効値はスキップ）。
    - AI スコア（news）を利用、未登録は中立扱い。
    - Bear レジーム検知により BUY を抑制するロジックを実装（AI の regime_score を使用、サンプル閾値あり）。
    - エグジット判定（stop_loss と score 下落）を実装。価格欠損時の判定スキップや features 欠損時の扱い（score=0 として SELL）などの安全弁を実装。
    - DB 操作はトランザクションで実行し、失敗時にロールバックを試行。

- リサーチ・解析ユーティリティ（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range 計算で欠損制御を行う。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を計算（EPS=0 の場合は None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズンに対する将来リターンを一括 SQL で取得（デフォルト horizons=[1,5,21]）。入力検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効データ 3 件未満では None を返す。
    - rank: 同順位は平均ランクを割り当てる実装（round による丸めで ties 判定の安定化）。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージは便利関数を __all__ で公開。

- バックテスト（src/kabusys/backtest/*）
  - metrics
    - BacktestMetrics dataclass を定義（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）。
    - calc_metrics: DailySnapshot と TradeRecord のリストから各メトリクスを算出。
    - 個別計算関数を実装（CAGR、Sharpe、MaxDrawdown、勝率、Payoff Ratio）。境界条件（データ不足、ゼロ割等）に対する安全処理あり。
  - simulator
    - DailySnapshot / TradeRecord dataclass を実装。
    - PortfolioSimulator: メモリ内のポートフォリオ状態管理と疑似約定ロジックを実装。
      - execute_orders: SELL を先に処理してから BUY を処理（資金確保のため）。SELL は保有全量クローズ（部分決済は非対応）。
      - スリッページ（BUY は +、SELL は -）、手数料率を考慮した約定価格・手数料・実現損益の計算を行う。
      - lot_size のパラメータで丸め動作を制御（日本株では通常 100）。

- 公開 API とエクスポート
  - strategy, portfolio, research パッケージの主要関数を __init__.py で明示的にエクスポートし、利用者が簡単に import できるように整理。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Deprecated
- （初回リリースのため無し）

### Removed
- （初回リリースのため無し）

### Security
- （初回リリースのため無し）

---

注意事項 / 未実装・既知の制限
- position_sizing.calc_position_sizes:
  - price が欠損した場合、_max_per_stock による制約が過小評価される可能性があり、将来は前日終値や取得原価でフォールバックする検討が示されています（TODO）。
  - lot_size の銘柄別対応は未実装（将来拡張予定）。
- strategy.signal_generator:
  - トレーリングストップや時間決済（保有日数基準）は未実装。positions テーブルに peak_price / entry_date を追加すれば実装可能。
- simulator:
  - SELL は全量クローズのみ。部分利確/部分損切りは非対応。
- config:
  - .env の読み込みで OS 環境変数は保護され、.env.local による上書きは許可されているが、挙動は環境に依存するためテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用推奨。

以上が v0.1.0（初回リリース）に含まれる主な実装内容です。将来的なリリースでは、単元株マスタ対応、より柔軟な約定ロジック、追加のエグジット戦略、外部 API 連携の強化などが想定されています。