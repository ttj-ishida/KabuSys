# Changelog

すべての notable な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-22

初回リリース — 日本株自動売買ライブラリ "kabusys" の初期実装を追加。

### 追加（Added）
- パッケージ構成
  - kabusys パッケージを追加。主要サブパッケージ: data, strategy, execution, monitoring, research, backtest 等を想定したモジュール構成を提供。
  - __version__ = "0.1.0" を設定。

- 環境設定（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env の行パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメント判定（クォート外かつ '#' の直前が空白かタブの場合のみコメント扱い）
  - 環境変数保護（OS環境変数を protected として上書きを抑止）をサポートする読み込みロジック。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV 検証（development / paper_trading / live のみ有効）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ

- リサーチ用ファクター計算（src/kabusys/research/factor_research.py）
  - calc_momentum(conn, target_date)
    - mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
  - calc_volatility(conn, target_date)
    - 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。ウィンドウ不足を考慮。
  - calc_value(conn, target_date)
    - raw_financials から最新の財務データを取得して PER / ROE を計算。EPS が 0/欠損のときは PER を None。
  - すべて DuckDB を用いた SQL ベース実装で、外部 API には依存しない設計。

- 特徴量正規化・合成（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date)
    - research の各ファクター（momentum / volatility / value）を取得してマージ。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
    - 数値ファクターを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE + BULK INSERT、トランザクションで原子性を確保）。
    - 設計上ルックアヘッドを防ぐため target_date 時点のデータのみを使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネントスコア:
      - momentum: momentum_20 / momentum_60 / ma200_dev の sigmoid 平均
      - value: PER をスケーリングしてスコア化（PER=20 で 0.5）
      - volatility: atr_pct の Z スコアを反転して sigmoid 変換（低ボラ＝高スコア）
      - liquidity: volume_ratio を sigmoid 変換
      - news: ai_score を sigmoid（未登録時は中立 0.5）
    - weights の入力検証・補完・再スケーリング（デフォルト重みを使用、合計が 1 になるよう正規化）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数 >= _BEAR_MIN_SAMPLES の時）により BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60。
    - SELL（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）
      - final_score が閾値未満
      - （コメントに記載）トレーリングストップ・時間決済は未実装（追加データが必要）
    - signals テーブルへ日付単位で置換して保存（トランザクションで原子性確保）。
    - 欠損データ時のログ出力や安全なフォールバック（None を 0.5 として補完）を実装。

- 解析・探索ユーティリティ（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])：複数ホライズンの将来リターンを一括取得。
  - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman の ρ（ランク相関）を実装。
  - rank(values)：同位ランクは平均ランクで処理（round(v,12) により浮動小数の tie を安定検出）。
  - factor_summary(records, columns)：count/mean/std/min/max/median を計算。
  - いずれも pandas 等の外部ライブラリに依存せず標準ライブラリで実装。

- バックテスト（src/kabusys/backtest）
  - simulator.py:
    - DailySnapshot / TradeRecord の dataclass を提供。
    - PortfolioSimulator：メモリ内でポートフォリオ管理・擬似約定を実装。
      - execute_orders: SELL を先に処理、その後 BUY（SELL は保有全量クローズ、部分利確未対応）。
      - スリッページ（slippage_rate）、手数料（commission_rate）を適用。買いは資金に収まるようシェア数を再計算。
      - mark_to_market: 終値評価で DailySnapshot を記録（終値欠損時は 0 で評価し WARNING を出力）。
  - metrics.py:
    - calc_metrics(history, trades) → BacktestMetrics（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）。
    - 各評価指標の実装（年次化・営業日252日基準等）。
  - engine.py:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DB からインメモリ DuckDB へデータをコピーして安全にバックテスト実行（signals/positions を汚染しない）。
      - 日次ループ: 前日シグナルの約定 → positions の書き戻し → mark_to_market → generate_signals（当日）→ ポジションサイジング → 次日約定のための signals_prev 作成。
    - ヘルパー: _build_backtest_conn（必要テーブルを期間範囲でコピー）、_fetch_open_prices/_fetch_close_prices、_write_positions、_read_day_signals。

- API エクスポート
  - strategy/__init__.py, research/__init__.py, backtest/__init__.py 等で主要関数・クラスを __all__ で公開。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初期実装において、外部環境依存や例外時に安全に挙動するよう以下を考慮:
  - .env ファイル読み込み時のファイルオープン失敗を警告で扱う。
  - トランザクション中の例外で ROLLBACK を試み、失敗時は警告を出力。
  - weights パラメータの不正値（非数値/負値/NaN/Inf/未知キー）をスキップするバリデーションを追加。
  - 価格欠損時は SELL 判定をスキップしてログ出力（誤クローズ防止）。

### 既知の制約・未実装（Known / Todo）
- signal_generator の一部エグジット条件は未実装（コードコメント参照）:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超）
- calc_value は現時点で PBR・配当利回りを実装していない。
- AI スコアが存在しない銘柄はニューススコアを中立 0.5 として扱う（保守的な設計）。
- research/feature_exploration は pandas 等を使わない実装のため、大規模データでの最適化余地あり。
- 部分利確や部分売却、複雑な資金管理ロジックは未実装（シンプルな全量クローズ/全量建てが前提）。
- market_calendar の完全な扱い（祝日や特殊取引日の細部）は将来的な改善対象。
- バックテストは prices_daily 等の品質に依存する（欠損データが多いと結果に影響）。

---

その他メモ:
- ロギングや警告を多用し、欠損データや異常入力時に安全に動作するよう設計されています。
- 本リリースは主に内部バックテスト/戦略開発用途を想定しており、本番発注層（execution）や監視（monitoring）との結合は今後の拡張ポイントです。

（今後のリリースではエグジット条件の拡張、ポジションサイジングの高度化、execution 層の実装、ドキュメント・型注釈強化等を予定）