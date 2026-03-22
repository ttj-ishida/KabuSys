# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な機能、設計方針、既知の未実装点を以下にまとめます。

### 追加
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` に設定。
  - 公開モジュール群を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - OS 環境変数を保護する機構（override/protected）。
  - Settings クラスでアプリ設定をプロパティとして提供（必須変数は _require により検証）。
    - J-Quants / kabuステーション / Slack / DB パス 等の設定を提供。
    - KABUSYS_ENV の許容値検証（development, paper_trading, live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - Path 型での DuckDB / SQLite パスの取り扱い。

- 戦略：特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを取り込み、ユニバースフィルタ、Zスコア正規化、クリッピング、features テーブルへの日付単位 UPSERT を実装。
  - ユニバースフィルタ条件：
    - 最低株価: 300 円
    - 20日平均売買代金: 5 億円
  - 正規化対象カラムの指定、Zスコアを ±3 でクリップ。
  - ファクター取得は research モジュール（calc_momentum, calc_volatility, calc_value）を使用。
  - トランザクション / バルク挿入により日付単位の置換（冪等性）を確保。

- 戦略：シグナル生成（kabusys.strategy.signal_generator）
  - features テーブルと ai_scores を統合して銘柄ごとの final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ書き込む。
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news（AI スコア）
  - 重み付けのデフォルト（StrategyModel.md に準拠）を実装し、ユーザ渡し weights を検証・正規化して合計を 1.0 にスケール。
  - AI レジーム集計により Bear 相場を検知すると BUY を抑制（サンプル数閾値あり）。
  - SELL（エグジット）条件:
    - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
    - スコア低下: final_score が threshold 未満
  - SELL 対象銘柄は BUY リストから除外（SELL 優先）。
  - 日付単位の置換（トランザクション／バルク挿入）で冪等性を確保。
  - 公開 API:
    - generate_signals(conn, target_date, threshold=0.60, weights=None) -> 書き込みシグナル数を返す

- research モジュール群（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）
    - calc_volatility: 20日 ATR（atr_pct）、avg_turnover、volume_ratio（部分窓でも算出）
    - calc_value: raw_financials から最新財務を参照して PER/ROE を計算
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（horizons の検証あり）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード数閾値あり）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクで扱うランク関数（丸めにより ties 検出の安定化）
  - zscore_normalize は kabusys.data.stats から利用（実装は data 側に依存）

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator によりメモリ内でポートフォリオ状態・約定を管理。
    - execute_orders: SELL を先に処理、BUY は alloc に基づき当日始値で約定（スリッページ/手数料を適用）。
      - BUY は端数切り捨て（floor）で株数を計算、手数料込みで再計算して資金不足時はスキップ。
      - SELL は保有全量をクローズ（部分利確/部分損切り未対応）。
    - mark_to_market: 終値で評価し DailySnapshot を記録（終値欠損は 0 と評価して警告）。
    - TradeRecord / DailySnapshot のデータクラスを定義。
  - metrics:
    - calc_metrics で BacktestMetrics を作成（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）。
    - それぞれの内部計算関数を実装（年次化の扱い、0 回避などのガードあり）。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB からインメモリ DuckDB へ必要テーブル（日付範囲でフィルタ）をコピーしてバックテスト用接続を構築。
      - 日次ループでの処理フローを実装：
        1. 前日シグナルを当日始値で約定
        2. positions テーブルにシミュレータ保有状態を書き戻し（generate_signals の SELL 判定に必要）
        3. 終値で時価評価・スナップショット記録
        4. generate_signals() で当日シグナル生成
        5. ポジションサイジング（max_position_pct による制限）で翌日の発注リスト作成
      - market_calendar は全件コピー（取引日計算に使用）
      - 日付範囲でコピーされるテーブル: prices_daily, features, ai_scores, market_regime（start_date - 300日 から end_date）
    - run_backtest は BacktestResult(history, trades, metrics) を返す。

### 仕様上の注意 / 未実装（既知の制約）
- シグナル生成側・戦略側は発注 API や実際の execution 層に依存しない設計だが、execution パッケージは空の初期化モジュールのみ存在（発注連携は別実装想定）。
- エグジット条件について未実装の要素:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）など
- generate_signals の weights 引数は不正値を細かく無視する（未知キー/非数値/負値/NaN/Inf をスキップ）し、合計が 1.0 になるように正規化する点に注意。
- feature_engineering は features テーブルへ書き込む際、avg_turnover をフィルタで利用するが features テーブル自体には avg_turnover を保存しない。
- calc_forward_returns の horizons は 1〜252 の整数であることを要求。
- バックテストのポジションサイズ計算・約定ロジックは簡易化（部分利確や複雑なオーダー管理は未対応）。
- DuckDB を利用しており SQL 実装は特定の構文（ウィンドウ関数等）に依存する。

### ドキュメント / 設計参照
- 各モジュール内に設計方針や処理フローのコメント（StrategyModel.md / BacktestFramework.md 等への言及）が含まれており、実装はそれら仕様に基づいています。

### 破壊的変更
- 初回リリースのため破壊的変更なし。

---

今後の予定（例）
- execution 層の実装（kabu API 連携）
- ポジション管理の強化（部分利確、トレーリングストップ、ピーク価格管理）
- モデル評価用の追加メトリクス・可視化ユーティリティ
- unit tests / CI の整備

（必要であれば上記変更内容をより細かく、各関数や仕様へのリンク付きで展開します。）