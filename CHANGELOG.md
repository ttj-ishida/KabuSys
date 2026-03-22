CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-22
--------------------

Added
- 初回リリース: kabusys パッケージ（バージョン 0.1.0）。
  - パッケージ公開 API:
    - kabusys.__all__ により "data", "strategy", "execution", "monitoring" をエクスポート。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動ロード対象を特定。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - OS側既存の環境変数は protected として上書き制御。
  - .env パーサの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート文字列対応（バックスラッシュでのエスケープ処理を考慮）。
    - クォート無しの値に対するインラインコメント処理（# の直前がスペース/タブの場合にコメント扱い）。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得（未設定時は ValueError）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH の既定値。
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- 戦略：特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
  - ユニバースフィルタ実装（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）。
  - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）と ±3 でのクリップ。
  - features テーブルへの日付単位の置換（DELETE → INSERT）をトランザクションで行い冪等性を確保。
  - 休場日や当日欠損に対応するため、target_date 以前の最新株価をユニバース判定に使用。
- 戦略：シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
  - コンポーネントスコア変換:
    - Z スコアをシグモイドで [0,1] に変換。
    - PER は逆数スコア（PER=20 で 0.5 のようなスケーリング）。
    - 欠損コンポーネントは中立値 0.5 で補完。
  - 重み付け (デフォルト weights) のマージ・検証機能（不正値は無視、合計が 1.0 になるよう再スケール）。
  - Bear レジーム検出（ai_scores の regime_score 平均が負の場合）による BUY シグナル抑制。
  - BUY シグナル閾値デフォルト _DEFAULT_THRESHOLD=0.60。
  - SELL（エグジット）判定の実装:
    - ストップロス（終値/avg_price - 1 < -8%）を優先。
    - final_score が閾値未満の場合のクローズ。
    - SELL 対象は BUY から除外し、ランクを付け直す。
  - signals テーブルへの日付単位置換をトランザクションで実行し冪等性を確保。
- リサーチツール（src/kabusys/research/*）
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いたファクター計算を実装。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（MA200 が未満の場合は None）。
    - Volatility: 20日 ATR / atr_pct, avg_turnover, volume_ratio（必要なデータ不足時の None 処理）。
    - Value: target_date 以前の最新財務データを参照して PER / ROE を計算（EPS 0 の場合は PER=None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを一括取得。
    - calc_ic: 要素結合後に Spearman のランク相関（IC）を計算。サンプル 3 未満は None。
    - rank: ties を平均ランクで処理（比較前に round(v, 12) により安定化）。
    - factor_summary: count, mean, std, min, max, median を算出。
  - すべて外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装。
- バックテストフレームワーク（src/kabusys/backtest/*）
  - run_backtest API（engine.py）:
    - 本番 DB から必要テーブルを切り出してインメモリ DuckDB にコピー（signals/positions を汚染しない）。
    - 日次ループでシグナル取得 → 約定（PortfolioSimulator）→ positions テーブルへ書き戻し → マーク・トゥ・マーケット → generate_signals 呼出し → 発注配分処理 を実行。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
  - データコピーのユーティリティ: _build_backtest_conn（date 範囲でのフィルタコピー、market_calendar の全件コピー）。
  - PortfolioSimulator（simulator.py）:
    - 擬似約定ルール（SELL を先、BUY を後で処理。SELL は保有全量クローズ）。
    - スリッページ（始値 × (1 ± slippage_rate)）、手数料率をモデル化。
    - 平均取得単価（cost_basis）管理、TradeRecord / DailySnapshot の記録。
    - mark_to_market で終値評価。終値欠損時は 0 評価かつ WARNING ログ。
  - 評価指標（metrics.py）:
    - BacktestMetrics dataclass（cagr / sharpe_ratio / max_drawdown / win_rate / payoff_ratio / total_trades）。
    - CAGR, 年次化 Sharpe（無リスク金利=0、252 日換算）、最大ドローダウン、勝率、Payoff Ratio を実装。

Documentation / Design notes
- 各モジュールに詳細な docstring を追加。StrategyModel.md / BacktestFramework.md 等の設計文書に基づくことを明記。
- 各関数は look-ahead バイアスを避ける設計（target_date 時点のデータのみ使用）を強調。

Known issues / TODO
- _generate_sell_signals 内で未実装のエグジット条件:
  - トレーリングストップ（peak_price が positions に保存されている必要があるが現状未保存）。
  - 時間決済（保有 60 営業日超過）も未実装。
- feature_engineering は merged レコードで avg_turnover をフィルタに使うが features テーブル自体には avg_turnover を保存していない（設計上の注意）。
- raw_financials 取得ロジックは ROW_NUMBER を使用（DuckDB 互換を前提）。他 DB への移植時は注意が必要。
- run_backtest のデータコピー処理は例外時にテーブルのコピーをスキップして続行する実装のため、必要データが欠けていると警告が出る可能性がある。
- 外部依存: DuckDB が必須（DuckDBPyConnection を多用）。

Breaking Changes
- 初回リリースのため該当なし。

Security
- 初版のため該当なし。機密情報（API トークン等）は Settings._require で必須化し、.env の取り扱いに注意すること。

作者メモ
- 本リリースは「研究で計算した生ファクターを本番戦略に取り込み、シグナル生成→バックテストまで一貫して試せる」初期実装を目的としています。今後はポジションサイジングの高度化、エグジットルールの追加、監視・実取引層の実装を予定しています。