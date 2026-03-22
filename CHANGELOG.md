Keep a Changelog
================

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。
バージョン管理ツール（例: Git）のコミットログとは別に、利用者に向けた高レベルな変更点を記載します。

Unreleased
----------

- なし（初回リリースは 0.1.0 を参照してください）

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初回リリース。
- パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出: __file__ の親階層から .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない）。
  - .env パーサ:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を正しく扱う。
    - インラインコメントの扱い（クォート外で # の直前が空白/タブの場合のみコメントとみなす）をサポート。
  - .env ロードの上書きルール:
    - OS 環境変数は保護（protected）され、.env/.env.local による上書きを防止。
    - .env を先に読み込み、.env.local は override=True で上書き可能。
  - Settings クラスを提供し、環境変数をラップして型・妥当性チェックを実行（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 各種既定値を提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV など）。KABUSYS_ENV / LOG_LEVEL の値検証を実装。
  - 環境判定ユーティリティ: is_live / is_paper / is_dev。

- 戦略関連（kabusys.strategy）
  - 特徴量エンジニアリング（strategy.feature_engineering）
    - build_features(conn, target_date) を実装。
    - research モジュールで計算した生ファクター（momentum / volatility / value）をマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT）をトランザクションで行い原子性を保証。
    - ユニバースフィルタ条件は定数化（_MIN_PRICE=300 円、_MIN_TURNOVER=5e8 円 等）。
  - シグナル生成（strategy.signal_generator）
    - generate_signals(conn, target_date, threshold, weights) を実装。
    - features と ai_scores を統合して各要素スコア（momentum, value, volatility, liquidity, news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重みと閾値を実装（デフォルト閾値 0.60、デフォルト重みは StrategyModel.md に準拠）。
    - 重みの検証・補完・正規化処理（未知キーや不正値は無視し、合計が 1.0 でない場合はスケーリング）。
    - AI スコア統合: ai_scores がない場合は中立値（0.5）で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → Bear。ただしサンプル数が不足（デフォルト _BEAR_MIN_SAMPLES=3）なら Bear とみなさない）。Bear 時は BUY シグナルを抑制。
    - BUY シグナル生成・ランク付け、SELL（エグジット）シグナル生成を実装。SELL 判定条件（実装）:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - final_score が threshold 未満（score_drop）
    - SELL 対象は BUY から除外し、BUY のランクを再付与（SELL 優先ポリシー）。
    - signals テーブルへの日付単位置換（DELETE + bulk INSERT）をトランザクションで行い原子性を保証。
    - ログ出力で欠損データや異常値を警告。

- Research（kabusys.research）
  - ファクター計算（research.factor_research）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev を計算。データ不足時は None。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御によりATRカウントの過大評価を防止。
    - calc_value(conn, target_date): raw_financials から最新の財務データ（report_date <= target_date）を取得し PER/ROE を計算。EPS が 0/欠損のときは PER を None に。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズン（日数）ごとの将来リターンを計算。horizons の検証と SQL による一括取得で性能を考慮。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク相関）で IC を計算。サンプル不足（<3）やゼロ分散時は None を返す。
    - rank(values): 同順位は平均ランクで扱う。丸め（round(v, 12)）して浮動小数点誤差の ties 検出漏れを抑制。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算（None 値は除外）。
  - research パッケージは外部ライブラリ（pandas 等）に依存しないよう標準ライブラリ + duckdb を利用する方針。

- データ/DB 関連（設計・安全性）
  - DuckDB を主要な時系列データ操作に利用（prices_daily, features, ai_scores, raw_financials 等）。
  - DB 書き込みはトランザクションで行い、失敗時は ROLLBACK を試行（ROLLBACK 失敗時は警告ログ）。

- バックテスト（kabusys.backtest）
  - run_backtest(conn, start_date, end_date, ...) を実装。
    - 本番 DuckDB から必要期間のデータをインメモリ DuckDB にコピーしてバックテスト用接続を構築（signals/positions を汚染しない）。
    - コピー対象テーブルは日付フィルタ付き（prices_daily, features, ai_scores, market_regime など）。market_calendar は全件コピー。
    - 日次ループでの処理フローを実装:
      1. 前日シグナルを当日の始値で約定（SELL を先に約定、BUY は残金を分配して約定）
      2. simulator の positions を positions テーブルへ書き戻す（generate_signals が使用）
      3. 終値で時価評価して DailySnapshot を記録
      4. generate_signals を実行して翌日の signals を生成
      5. ポジションサイジングと次日の注文組立て
    - 戻り値: BacktestResult(history, trades, metrics)
  - ポートフォリオシミュレータ（backtest.simulator）
    - PortfolioSimulator を実装:
      - cash, positions, cost_basis, history, trades を管理
      - execute_orders(signals, open_prices, slippage_rate, commission_rate): SELL を先、BUY を後に処理。BUY は alloc を用いて株数を計算（手数料込みで調整）。SELL は保有全量をクローズ（部分利確は未対応）。
      - スリッページ・手数料モデルを適用（BUY は entry_price = open * (1 + slippage)、SELL は exit_price = open * (1 - slippage)）。
      - mark_to_market(trading_day, close_prices) で DailySnapshot を記録（終値欠損時は 0 で評価して警告ログ）。
    - TradeRecord / DailySnapshot の dataclass を提供。
  - バックテストメトリクス（backtest.metrics）
    - calc_metrics(history, trades) を実装し、CAGR, Sharpe Ratio（無リスク=0、年次化 252 日）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算して BacktestMetrics を返却。
    - 各内部関数はエッジケース（データ不足・ゼロ除算等）を防ぐため安全なデフォルト（0.0）を返す。

Changed
- 新規リリースのため、設計方針や関数公開 API を整理し、モジュール間の責務を明確化（strategy は execution に依存しない、research は DB のみを参照する等）。

Fixed
- 初期リリースのため該当なし（実装段階で考慮された堅牢性・入力検証を反映）。

Deprecated
- なし

Removed
- なし

Security
- 機密情報（API トークン等）は Settings 経由で環境変数から読み込むように設計。.env ファイル自動ロードは明示的に無効化可能。

Notes / Known limitations
- 一部のエグジット条件は未実装（コメントで明記）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の追加情報が必要であり、今後の実装課題。
- strategy や research の多くの仕様はドキュメント（StrategyModel.md, BacktestFramework.md, 等）に依存。実装はそれらに基づいているが、外部リソース/ドキュメントと合わせて利用すること。
- 現時点でデータ入出力は DuckDB 前提。外部依存（pandas 等）を使わない設計だが、運用時は大規模データの取り扱いに注意。
- execution 層（実際の発注 API との接続）はこのリリースのコアには含めていない（strategy と execution 層は疎結合）。

作者
- kabusys 開発チーム

（終）