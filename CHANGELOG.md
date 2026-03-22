# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
=============

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-22
-------------------
初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装・公開しました。

Added
- パッケージ基本情報
  - パッケージバージョン: 0.1.0
  - パッケージ説明: "KabuSys - 日本株自動売買システム"

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準に判定。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いなどに対応。
    - クォートあり／なしでのコメントの取り扱い差分を考慮。
  - .env 読み込み時の上書き制御:
    - override フラグと protected キーセットにより、OS環境変数などの保護が可能。
  - Settings クラスによる強い型の設定アクセス:
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DBパスのデフォルト設定（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。
    - 環境（KABUSYS_ENV: development | paper_trading | live）の検証。
    - ログレベル（LOG_LEVEL）の検証。
    - is_live / is_paper / is_dev の補助プロパティ。

- 研究（research）モジュール群
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比率を計算。NULL伝播を考慮して true_range を算出。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER / ROE を計算。EPS=0 等は None。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、研究用途向けに設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。入力検証（1〜252日）あり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。ties は平均ランクで処理、サンプル不足（<3）で None。
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）。
    - rank ユーティリティ: 同順位は平均ランク、丸め誤差対策として round(v, 12) を使用。
  - research/__init__ で主要 API を再エクスポート。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date):
    - 研究モジュール（calc_momentum, calc_volatility, calc_value）から生ファクターを取得。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位で features テーブルにトランザクション＋バルク挿入で置換（冪等・原子性保証）。
    - 正規化対象カラムやクリップ閾値等は定数で明示。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features / ai_scores / positions を読み込み、各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - Z スコアをシグモイド変換し、欠損は中立値（0.5）で補完。
    - デフォルト重みを使用し、外部から与えられた重みは検証（未知キーや負値・非数は無視）して合計が 1.0 になるように再スケーリング。
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、サンプル数 >= 3 の場合に BUY を抑制。
    - BUY シグナルは threshold を超えた銘柄（Bear 時は抑制）。SELL シグナルは保有ポジションに対してストップロス（-8%）およびスコア低下を判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換（トランザクションで原子性）。
    - ロギングと不整合（features 未存在、価格欠損等）への注意喚起。

- バックテストフレームワーク (kabusys.backtest)
  - simulator:
    - PortfolioSimulator によるメモリ内ポジション管理、約定処理（SELL 先処理・BUY 後処理）、スリッページと手数料モデル、トレード記録（TradeRecord）と日次スナップショット（DailySnapshot）の蓄積。
    - BUY: 始値・スリッページ・手数料考慮、資金不足時の株数再計算、平均取得単価更新。
    - SELL: 保有全量クローズ、手数料と実現損益計算、保有/コスト情報削除。
    - mark_to_market: 終値評価、終値欠損は 0 評価で警告ログ。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB から in-memory DuckDB へデータをコピー（_build_backtest_conn）。コピー対象は日付範囲でフィルタしたテーブル（prices_daily, features, ai_scores, market_regime）および market_calendar。
      - 日次ループ: 前日シグナルの約定、positions テーブルへの書き戻し、終値評価、generate_signals による当日シグナル生成、ポジションサイジング→注文作成。
      - 生成された履歴・トレードを用いて評価指標を計算して BacktestResult を返却。
    - 補助関数: _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals。

  - metrics:
    - calc_metrics(history, trades) による BacktestMetrics の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 内部実装: CAGR（暦日ベース）、Sharpe（年次化、無リスク=0）、最大ドローダウン、勝率、ペイオフレシオ等。

- パッケージ公開 API
  - top-level __all__ に data, strategy, execution, monitoring を含む。
  - strategy パッケージは build_features, generate_signals をエクスポート。
  - research パッケージは主要な研究用関数を再エクスポート。

Notes / Known limitations
- 実運用関連
  - execution パッケージの __init__ は存在するが実際の発注 API 連携実装はこの差分には含まれていません（Execution 層は別途実装を想定）。
  - monitoring モジュール（トップレベルに名前があるが詳細実装は本差分に含まれない可能性あり）。
- 戦略上の未実装 / 将来実装予定（ソース内コメント）
  - トレーリングストップ（直近高値からの % ベース）や時間決済（保有期間超過）等は未実装。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
  - Value 指標の一部（PBR、配当利回り）は未実装。
- データ依存
  - build_features / 各種 calc_* は DuckDB の特定スキーマ（prices_daily, raw_financials, features, ai_scores 等）を前提とするため、スキーマの整備が必要。
  - zscore_normalize は kabusys.data.stats に依存（本差分に実装は含まれない）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

その他
- ロギングを広く活用し、データ欠損や想定外入力に対して警告/情報ログを出す設計になっています。
- SQL クエリは DuckDB を想定して書かれており、大量データを扱うためウィンドウ関数や一括取得を多用しています。

---

今後のリリースでは以下を想定しています（例）:
- execution 層の実装（kabuステーション API 等の実取引連携）
- monitoring / alerting 機能の追加（Slack 通知等）
- 戦略の拡張（トレーリングストップ、時間決済、追加ファクター）
- ドキュメント・テストの充実（CI 連携、型チェック、サンプルデータ）

フィードバックや改善要望があればお知らせください。