# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-22

### Added
- 基本パッケージ骨格を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ公開インターフェイスに data, strategy, execution, monitoring を含める (src/kabusys/__init__.py)。

- 環境設定モジュールを追加 (src/kabusys/config.py)
  - .env および環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行解析で以下をサポート:
    - コメント行（#）・空行のスキップ
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープの解釈
    - インラインコメントの扱い（クォートなしは直前が空白/タブの場合のみコメントと判断）
  - 必須環境変数取得用の _require() を提供。
  - 設定オブジェクト Settings を公開し、主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- 研究用ファクター計算モジュールを追加 (src/kabusys/research/)
  - calc_momentum, calc_volatility, calc_value を提供（prices_daily / raw_financials を参照し、(date, code) 辞書リストを返す）。
  - zscore_normalize を data.stats から利用可能にしてエクスポート。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定日からの将来リターン（任意ホライズン）を一括取得（単一 SQL 実行で実装）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク付け（丸め誤差対策に round(..., 12) を使用）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - 研究モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB を利用する設計。

- 特徴量エンジニアリングモジュールを追加 (src/kabusys/strategy/feature_engineering.py)
  - research 側で計算した生ファクターを取り込み、正規化・合成して features テーブルへ保存する build_features(conn, target_date) を実装。
  - ユニバースフィルタ:
    - 最低株価: 300 円
    - 最低 20 日平均売買代金: 5 億円
  - Z スコア正規化対象カラムを指定し、±3 でクリップして外れ値の影響を抑制。
  - features テーブルへの日付単位での置換（DELETE + INSERT）をトランザクションで実行し原子性を担保。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみ利用。

- シグナル生成モジュールを追加 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア final_score を計算し、BUY/SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
  - デフォルトの重み・閾値などを実装:
    - デフォルト重み: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10
    - BUY 閾値: 0.60
    - ストップロス閾値: -8%（SELL の最優先条件）
    - Bear 判定用最小サンプル数: 3（不足時は Bear でないと判断）
  - スコア算出のポイント:
    - Z スコアをシグモイド変換して 0〜1 に変換
    - component が None の場合中立 0.5 で補完（欠損による不当な扱いを防止）
    - AI スコアはシグモイド変換、未登録は中立
  - Bear レジーム時は BUY シグナルを抑制
  - SELL 条件:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score < threshold
    - price 欠損や features に未登録の保有銘柄については警告を出し、一定の扱い（score=0.0）で処理
  - weights の入力検証（未知キー・非数値・NaN/Inf・負値は無視、合計が 1.0 でない場合はスケーリング）
  - signals テーブルへの日付単位での置換（トランザクションで原子性を担保）
  - BUY と SELL の優先ポリシー（SELL 対象は BUY から除外し、BUY のランクを再付与）

- バックテストフレームワークを追加 (src/kabusys/backtest/)
  - PortfolioSimulator（src/kabusys/backtest/simulator.py）を実装:
    - スリッページ（BUY +、SELL -）・手数料モデルをサポート
    - SELL を先に処理し、SELL は保有全量をクローズ（部分利確は未実装）
    - 約定で TradeRecord を記録、mark_to_market で DailySnapshot を記録
    - price 欠損時の評価は 0 として警告を出力
  - バックテストエンジン（src/kabusys/backtest/engine.py）を実装:
    - 本番 DB から必要データをインメモリ DuckDB にコピーして安全にバックテストを実行（signals/positions を汚さない）
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → 終値評価 → generate_signals（SELL 判定用に positions を参照）→ ポジションサイジング → 次日の注文作成
    - DB コピーは日付範囲でフィルタしたテーブルを対象（market_calendar は全件コピー）
  - run_backtest() の公開 API（start_date, end_date, initial_cash, slippage_rate, commission_rate, max_position_pct）
  - バックテスト用の補助関数 (価格取得・positions 書き戻し・signals 読取など)

- バックテスト評価指標モジュールを追加 (src/kabusys/backtest/metrics.py)
  - BacktestMetrics データクラス（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）
  - calc_metrics(history, trades) を実装（内部で CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio を計算）
  - 各指標の実装詳細:
    - CAGR: 暦日ベース
    - Sharpe: 年次化、無リスク金利=0、営業日252日換算
    - Max Drawdown: 1 - 現在 / ピーク
    - Win Rate / Payoff Ratio: closed sell trades を基に算出

- モジュールエクスポートの整理
  - strategy.__init__ で build_features / generate_signals を公開
  - research.__init__ で各種関数を公開
  - backtest.__init__ で run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Design decisions
- SQL は DuckDB 上でウィンドウ関数や LEAD/LAG を活用し、性能とシンプルさの両立を目指す実装になっています。
- ほとんどの関数は DB 接続/データのみを受け取り、外部 API や発注レイヤ（execution）に依存しない純粋な計算ロジックとして設計されています。
- 欠損データやサンプル不足時は None を返す・処理をスキップする方針で、偽陽性・誤判定を抑制しています。
- トランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入を用いて、features / signals / positions などの日付単位の置換操作で原子性を保証しています。
- .env の自動読み込みは配布後の挙動を考慮して、ファイル探索を __file__ ベースで行い CWD に依存しない実装です。

### Required environment variables
- このリリースで必須/想定される環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - KABUSYS_ENV（省略時は development）
  - LOG_LEVEL（省略時は INFO）

---

今後のリリース案（参考）
- feature: PBR / dividend yield の追加（value ファクターの拡張）
- improvement: 部分利確・トレーリングストップ・時間決済の実装（_generate_sell_signals で未実装と注記済）
- testing: .env パーサー・DB 操作・バックテストのユニットテスト整備
- performance: DuckDB クエリの最適化および大口銘柄スケーリング対応

-- End of Changelog --