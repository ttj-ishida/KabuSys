Changelog
=========

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現時点で未リリースの変更はありません）

0.1.0 - 2026-03-22
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン (0.1.0) とエクスポート一覧を追加。
  - 環境設定管理（src/kabusys/config.py）
    - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサ実装:
      - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
      - 行コメント、インラインコメント処理（クォート有無に応じた扱い）。
    - OS環境変数の保護機構（.env ロード時に既存 OS 環境変数を保護）。
    - 必須環境変数取得ヘルパ _require を導入（未設定時は ValueError）。
    - 設定クラス Settings を提供し、J-Quants / kabu API / Slack / DB パス / システム設定をプロパティとして公開。
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）、LOG_LEVEL の検証。
    - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）の挙動を定義。
  - 戦略（src/kabusys/strategy）
    - 特徴量生成モジュール（src/kabusys/strategy/feature_engineering.py）
      - 研究側（research）で計算した生ファクターを正規化・合成して features テーブルへ UPSERT（日付単位で置換）する処理を実装。
      - 処理フロー: calc_momentum / calc_volatility / calc_value の呼び出し → ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5e8 円） → Z スコア正規化 → ±3 でクリップ → トランザクション付きで features に挿入（冪等）。
      - DuckDB 接続を受け取り、prices_daily / raw_financials を参照する設計。
    - シグナル生成モジュール（src/kabusys/strategy/signal_generator.py）
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し final_score を生成。
      - デフォルト重みと閾値: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10、BUY 閾値 = 0.60。
      - Sigmoid 等の変換、欠損値は中立値 0.5 で補完するポリシー。
      - Bear レジーム検知（ai_scores の regime_score の平均が負でかつサンプル >= 3 の場合）で BUY を抑制。
      - エグジット判定（SELL）: ストップロス（終値ベースで -8% 以下）およびスコア低下（final_score < threshold）。SELL 判定は BUY より優先し、signals テーブルへトランザクションで日付単位置換。
      - 不整合・欠損時のログ出力（例: 価格欠損・features に存在しない保有銘柄など）。
    - strategy パッケージの公開 API: build_features, generate_signals。
  - 研究ユーティリティ（src/kabusys/research）
    - ファクター計算（src/kabusys/research/factor_research.py）
      - Momentum（mom_1m/mom_3m/mom_6m・ma200_dev）、Volatility（atr_20/atr_pct/avg_turnover/volume_ratio）、Value（per/roe）を DuckDB SQL ベースで実装。
      - 欠損データやウィンドウサイズ不足時は None を返す堅牢な実装。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算 calc_forward_returns（デフォルトホライズン [1,5,21]、horizons 検証あり）。
      - IC 計算 calc_ic（Spearman の ρ をランク計算で実装、サンプル数不足時は None）。
      - factor_summary（基本統計量: count/mean/std/min/max/median）。
      - rank ユーティリティ（同順位は平均ランク、浮動小数の丸めで ties を安定化）。
    - research パッケージの公開 API を整備。
  - バックテストフレームワーク（src/kabusys/backtest）
    - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
      - PortfolioSimulator、DailySnapshot、TradeRecord を実装。
      - 約定処理: SELL を先、BUY を後で処理。SELL は保有全量クローズ。スリッページ率／手数料率を適用。
      - mark_to_market で終値評価（終値欠損は 0 で評価し WARNING ログ）。
    - バックテストエンジン（src/kabusys/backtest/engine.py）
      - run_backtest 実装: 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（_build_backtest_conn）して日次ループを実行。
      - シグナル生成 → 約定 → positions 書き戻し → マーク・トゥ・マーケット → generate_signals の順で処理。
      - positions テーブルへの冪等書き戻し用ユーティリティ _write_positions、当日の open/close 取得ヘルパを実装。
    - メトリクス（src/kabusys/backtest/metrics.py）
      - CAGR、Sharpe（無リスク=0）、Max Drawdown、Win Rate、Payoff Ratio、総トレード数を計算する calc_metrics 実装。
  - パッケージエクスポート
    - backtest/__init__.py で run_backtest や型等を再エクスポート。
    - research/__init__.py で主要な研究ユーティリティを再エクスポート。

Changed
- N/A（初回リリースにつき変更履歴はなし）

Fixed
- N/A（初回リリースにつき修正履歴はなし）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Known limitations / Notes
- 一部戦略ロジックは未実装（ソース内コメント参照）:
  - トレーリングストップや時間決済（positions に peak_price / entry_date が必要なため未実装）。
  - BUY に関して部分利確・部分損切りは未対応（SELL は全量クローズ）。
- generate_signals の weights 入力は検証を行うが、合計が 0 の場合はデフォルト重みへフォールバック、合計が 1 でない場合は再スケールされる。
- .env パーサは一般的なケースをカバーするが非常に特殊な構文の .env（複雑なネストクォート等）には未対応の可能性あり。
- バックテスト用データコピーは日付範囲でフィルタされたテーブルをコピーする実装で、コピー失敗時はログを出してスキップする（データ欠損の可能性）。
- バックテストの年次化等は固定の前提（例: Sharpe は営業日252日）を使用。
- execution / monitoring パッケージはプレースホルダ（実運用向けの発注層、監視層は別途実装が必要）。

メモ
- 各モジュールは外部の発注 API に直接依存しない設計（DuckDB と純粋な計算ロジックで完結）。本番運用時は execution/monitoring 層およびセキュアな設定管理を組み合わせて利用してください。