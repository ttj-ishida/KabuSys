# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-22

Added
- 初期リリース。日本株自動売買ライブラリ "KabuSys" のコア機能を実装。
- パッケージ公開情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - 主要パッケージ名空間に `data`, `strategy`, `execution`, `monitoring` を公開（`__all__`）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を起点に行うため、CWD に依存しない。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`（主にテスト用途）。
  - .env パーサの堅牢化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしの行での `#` をインラインコメントとして扱うルールを実装（直前が空白/タブの場合のみコメントと判定）。
    - 無効行や読み込み失敗時は無害にスキップし、必要時に警告を発行。
  - OS 環境変数を保護するための protected キーセットをサポートし、`.env.local` 読み込み時の上書き制御を実装。
  - Settings クラスを提供し、主要設定項目をプロパティ経由で取得:
    - J-Quants / kabu API / Slack / DB パス（DuckDB / SQLite）など。
    - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性チェック（許容値を検査）。
    - 利便性プロパティ: `is_live`, `is_paper`, `is_dev`。

- 戦略（strategy パッケージ）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - 研究環境の生ファクターを正規化・合成して `features` テーブルへ保存する `build_features()` を実装。
    - 処理内容:
      - 研究モジュール（calc_momentum / calc_volatility / calc_value）から raw factor を取得。
      - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
      - 指定列の Z スコア正規化（外れ値は ±3 でクリップ）。
      - 日付単位で DELETE → INSERT のトランザクション処理により冪等性を保証（トランザクションで原子性を確保）。
    - 入出力は DuckDB 接続（`duckdb.DuckDBPyConnection`）と `date`。
  - シグナル生成（kabusys.strategy.signal_generator）
    - `generate_signals()` を実装し、`features` と `ai_scores` を統合して売買シグナル（BUY / SELL）を `signals` テーブルへ出力。
    - スコアリングロジック:
      - コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付きで `final_score` を算出。
      - デフォルト重みは (momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10)。ユーザー指定の重みは妥当性検査・正規化を行う。
      - Z スコアは sigmoid（0-1）に変換。欠損コンポーネントは中立値 0.5 で補完。
      - BUY 判定は `final_score >= threshold`（デフォルト閾値 0.60）。Bear レジーム（AI の regime_score 平均が負）を検知した場合は BUY を抑制。
    - エグジット（SELL）ロジック:
      - ストップロス: 現在終値 / avg_price - 1 <= -8% の場合は即時 SELL。
      - スコア低下: final_score が閾値未満の場合 SELL。
      - 保有銘柄で現在価格が取得できない場合は SELL 判定をスキップして誤クローズを防止。
    - SELL を優先して BUY から除外し、BUY のランク付けを再付与するポリシーを採用。
    - 日付単位で DELETE → INSERT のトランザクション処理により冪等性を保証。

- 研究モジュール（research パッケージ）
  - ファクター計算（kabusys.research.factor_research）
    - `calc_momentum`, `calc_volatility`, `calc_value` を実装。prices_daily / raw_financials テーブルのみ参照（外部 API 不使用）。
    - 実装詳細:
      - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（必要行数が足りない場合は None）。
      - Volatility: 20 日 ATR（true range の NULL 伝播に注意した実装）、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
      - Value: target_date 以前の最新財務データ（eps / roe）を取得し PER/ROE を計算。EPS が 0 または欠損の時は PER を None にする。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: `calc_forward_returns()`（複数ホライズン対応、ホライズンの妥当性検査あり）。
    - IC 計算: `calc_ic()`（Spearman の ρ をランクで計算、サンプル不足時は None）。
    - 統計サマリー: `factor_summary()`（count/mean/std/min/max/median を標準ライブラリのみで算出）。
    - ランク変換ユーティリティ: `rank()`（同順位は平均ランク、丸め処理で ties の検出を安定化）。
    - 設計方針として pandas 等の外部ライブラリに依存しない実装。

- バックテストフレームワーク（kabusys.backtest）
  - シミュレータ（kabusys.backtest.simulator）
    - メモリ内ポートフォリオシミュレータ `PortfolioSimulator` を実装。
    - オーダー約定ロジック:
      - SELL を先に処理、BUY は後から（資金確保のため）。
      - BUY は資金配分（alloc）に基づいて株数を切り捨てで約定。手数料・スリッページを考慮し、手数料込みで買える株数に再計算。
      - SELL は保有全量をクローズ（部分利確非対応）。約定後の realized_pnl を計算して記録。
      - 約定失敗や価格未取得時はログ出力してスキップ。
    - 日次時価評価 `mark_to_market()` で `DailySnapshot` を記録。終値が欠損する銘柄は 0 で評価して警告。
    - TradeRecord および DailySnapshot のデータモデルを提供。
  - メトリクス（kabusys.backtest.metrics）
    - `calc_metrics()` が `DailySnapshot` と `TradeRecord` から BacktestMetrics を算出。
    - 実装済み指標: CAGR, Sharpe Ratio（無リスク金利=0, 年次化252営業日換算）, Max Drawdown, Win Rate, Payoff Ratio, Total Trades。データ不足時は安全に 0.0 を返す実装。
  - エンジン（kabusys.backtest.engine）
    - `run_backtest()` を実装し、実運用 DuckDB から必要データを切り出してインメモリ DuckDB にコピーし、日次シミュレーションを実行。
    - コピー戦略:
      - signals / positions を汚染しないためにインメモリで実行。
      - `prices_daily`, `features`, `ai_scores`, `market_regime` は日付範囲でフィルタしてコピー。`market_calendar` は全件コピー。
      - コピーに失敗したテーブルは警告してスキップする堅牢性を提供。
    - 日次ループのフロー:
      1. 前日シグナルを当日始値で約定（simulator.execute_orders）。
      2. simulator の positions を `positions` テーブルへ書き戻し（`generate_signals` の SELL 判定が参照するため）。
      3. 終値で時価評価・スナップショット記録。
      4. `generate_signals` を呼び出し翌日シグナルを生成。
      5. signal を読み取り、発注リストを組成して次日に渡す。
    - `run_backtest()` の主要引数とデフォルト:
      - `initial_cash=10_000_000`
      - `slippage_rate=0.001`
      - `commission_rate=0.00055`
      - `max_position_pct=0.20`

- パブリック API のエクスポートを整理（各 __init__.py による公開）
  - strategy: `build_features`, `generate_signals`
  - research: `calc_momentum`, `calc_volatility`, `calc_value`, `zscore_normalize`, `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
  - backtest: `run_backtest`, `BacktestResult`, `DailySnapshot`, `TradeRecord`, `BacktestMetrics`

Other notable points / 設計上の注意
- 多くのモジュールは外部発注 API や本番口座に直接アクセスしない設計（安全性とテスト容易性）。
- DuckDB を主要なデータストア操作に使用（SQL と Python の組合せで高性能に集計）。
- 冪等性: データ書き込みは日付単位の DELETE → INSERT をトランザクションで実行して原子性を確保。
- 欠損データや非数（NaN/Inf）への堅牢な扱い（多くの場所で検査して None または中立値で補完）。
- 外部依存を最小化（研究用ユーティリティでは pandas 等を使わず標準ライブラリで実装）。

Known limitations / 今後の実装予定（ソースから推測）
- signal_generator の未実装機能:
  - positions テーブルに peak_price / entry_date が必要になるトレーリングストップや時間決済の実装（コメントで未実装と明示）。
- factor_research や value ファクターに PBR/配当利回りは未実装。
- simulator の BUY は部分利確に対応していない（買いは alloc ベースで新規建のみ、SELL は全量クローズ）。
- テストや運用上の追加的な検証・メトリクス、Slack 通知など実稼働機能は今後拡張想定。

以上が初期リリース (0.1.0) の主な変更点と実装内容の概要です。コードや仕様に関する追加の要約や、各モジュールごとの API ドキュメント（使用例、引数説明、戻り値例）を希望される場合は、対象モジュールを指定して依頼してください。