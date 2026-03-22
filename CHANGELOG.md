CHANGELOG
=========

すべての重要な変更を時系列で記録します。フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- なし（現時点の最新リリースは 0.1.0）

[0.1.0] - 2026-03-22
-------------------

初回リリース。日本株自動売買システムのコアライブラリを提供します（モジュール設計、ファクター計算、シグナル生成、バックテスト基盤など）。

Added
- 基本パッケージとバージョン情報を追加
  - pakage: kabusys, __version__ = "0.1.0"

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - Shell 形式の .env 行パースを独自実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）等のプロパティを提供。
  - 環境変数必須チェック用の _require と値検証（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research 側で計算された生ファクターを取得・マージ・ユニバースフィルタ適用・Zスコア正規化・±3 でクリップし、features テーブルへ日付単位で置換（冪等）。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - DuckDB を用いたバルク挿入とトランザクションで原子性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合して各銘柄の最終スコアを算出し、BUY/SELL シグナルを signals テーブルへ日付単位で置換（冪等）。
  - デフォルト重みと閾値を設定:
    - momentum: 0.40, value: 0.20, volatility: 0.15, liquidity: 0.15, news: 0.10
    - default threshold: 0.60
  - AI スコア統合（ai_scores テーブルから ai_score, regime_score を参照）、レジーム集計により Bear 相場検出（サンプル閾値あり）で BUY を抑制。
  - コンポーネントスコア計算（モメンタム、バリュー、ボラティリティ、流動性、ニュース）と欠損値は中立 0.5 で補完する方針。
  - エグジット（SELL）判定を実装:
    - ストップロス（終値が avg_price より -8% を超える）
    - スコア低下（final_score が閾値未満）
  - positions テーブル参照時の価格欠損／features 欠損に対するログ出力と安全処理。
  - weights 入力のバリデーションと正規化（未知キー・非数値・負値・NaN/Inf を無視し、合計が 1.0 になるよう再スケール）。
  - トランザクション + バルク挿入で signals の日付単位置換を実装。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m / ma200_dev を算出（必要行数不足は None）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、volume_ratio を算出。
    - calc_value(conn, target_date): raw_financials から直近財務データを取得して PER / ROE を計算（EPS が 0 または欠損の場合は PER=None）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズン先の将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算（有効サンプル < 3 は None）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー。
    - rank(values): 同順位は平均ランクとするランク付けユーティリティ。
  - これらは DuckDB のみに依存する形で設計（本番 API へのアクセスなし、外部ライブラリに依存しない実装方針）。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: メモリ内で cash/positions/cost_basis/history/trades を管理。
    - execute_orders(signals, open_prices, slippage_rate, commission_rate, trading_day): SELL を先に処理、BUY は資金に応じて発注、部分利確は非対応。スリッページ・手数料モデルを適用。
    - mark_to_market(trading_day, close_prices): 終値で評価し DailySnapshot を記録。不足価格は 0 で評価して警告ログ。
    - TradeRecord / DailySnapshot のデータクラス。
  - バックテストエンジン（kabusys.backtest.engine）
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーションを実行。signals 生成（generate_signals）→ 発注 → positions 書き戻し → マーク・トゥ・マーケット → シグナル生成 の流れを実装。
    - データコピー時に date 範囲フィルタ（prices_daily, features, ai_scores, market_regime）を適用し、本番テーブルの汚染を防止。
    - 取引当日の始値/終値取得ユーティリティ、positions 書き戻しユーティリティを提供。
  - バックテストメトリクス（kabusys.backtest.metrics）
    - calc_metrics(history, trades): CAGR / Sharpe ratio / Max drawdown / Win rate / Payoff ratio / total_trades を計算。
    - 各種内部計算関数を実装（年次化は暦日ベース、シャープは年換算 sqrt(252) を使用）。

- その他
  - strategy パッケージで build_features と generate_signals を公開。
  - research パッケージで主要ユーティリティを公開。
  - backtest パッケージで run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。
  - execution パッケージのプレースホルダファイルを追加（今後の発注実装予定）。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

Known issues / TODO
- signal_generator 内で言及されている一部のエグジット条件は未実装:
  - トレーリングストップ（peak_price/entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- calc_value では PBR や配当利回りは未実装。
- research モジュールは標準ライブラリのみで実装しているため、大規模データ処理における最適化余地あり。
- execution 層（実際の発注 API との連携）は未実装。実運用環境での API 呼び出し・認証・安全確認は今後実装予定。
- 一部 SQL 実行中の例外処理はロギングでの警告に留めており、運用上の堅牢化（リトライ・監視）は今後の課題。

注記
- 設計方針として「ルックアヘッドを避ける」「DB 書き込みはトランザクション + バルク挿入で原子性を確保」「発注層への直接依存を持たない（テスト容易性）」を採用しています。
- ログ出力と警告により、価格欠損やデータ不足の状況を明示するよう実装されています。

----