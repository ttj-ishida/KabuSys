CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。バージョン間の差分はコードベースから推測してまとめています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-22
--------------------

初回リリース — 日本株自動売買フレームワークのコア機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージ公開情報
  - パッケージ初期バージョンを src/kabusys/__init__.py にて "0.1.0" として定義。top-level の __all__ に data, strategy, execution, monitoring を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み順は OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、クォート付き文字列、バックスラッシュエスケープ、インラインコメントの扱い（スペース/タブ直前の # をコメントとして扱う）に対応。
    - .env 読み込み失敗時は警告を出力して安全に継続。
  - Settings クラスを導入し、コードから settings.jquants_refresh_token 等のプロパティで設定値を取得可能に。
  - 設定のバリデーション
    - KABUSYS_ENV は development / paper_trading / live のいずれかのみ許容。
    - LOG_LEVEL は DEBUG / INFO / WARNING / ERROR / CRITICAL のみ許容。
  - DB パス（DUCKDB_PATH, SQLITE_PATH）、API ベース URL 等の既定値を定義。

- 戦略関連 (src/kabusys/strategy)
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 層で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価、平均売買代金）を適用したうえで、指定列を Z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性確保）を実装。
    - 公開 API: build_features(conn: duckdb.DuckDBPyConnection, target_date: date) -> int
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - 正規化済み特徴量と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルに書き込む処理を実装。
    - 実装内容のポイント:
      - momentum / value / volatility / liquidity / news（AI） を重み付けして final_score を算出（デフォルト重みあり）。
      - weights の検証と補完、合計が 1 でない場合の再スケーリング。
      - AI に基づく市場レジーム判定（regime_score の平均が負で一定サンプル以上なら Bear）により BUY を抑制。
      - BUY 生成の閾値（デフォルト 0.60）、STOP-LOSS（-8%）等のルールを実装。
      - 保有ポジションのエグジット判定ロジック（ストップロス / スコア低下）を実装。
      - 日付単位の置換で signals テーブルを更新（冪等）。
    - 公開 API: generate_signals(conn: duckdb.DuckDBPyConnection, target_date: date, threshold: float = 0.6, weights: dict | None = None) -> int

- Research（研究用ユーティリティ） (src/kabusys/research)
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev を計算（200日移動平均はレコード数条件あり）。
    - Volatility / Liquidity: 20日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio を計算。true range は high/low/prev_close が揃っている場合のみ計算。
    - Value: raw_financials の最新財務データと prices_daily を結合して per, roe を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials のみを参照。
    - 公開 API: calc_momentum, calc_volatility, calc_value（いずれも conn, target_date を受ける）
  - 特徴量探索ツール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（horizons の検証: 正の整数かつ <=252）。
    - IC（Spearman の ρ）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（有効サンプルが 3 未満なら None を返す）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - ランキング補助: rank(values)（同順位は平均ランク、丸めによる ties 対応）。
    - 研究用ユーティリティをまとめて __all__ に公開。

- バックテストフレームワーク（src/kabusys/backtest）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator を実装（メモリ内でポジション管理、約定ロジック、約定記録 TradeRecord / DailySnapshot）。
    - 約定ルール:
      - SELL を先に処理、BUY を後に処理（資金確保のため）。
      - BUY: 始値にスリッページを加味して約定、手数料を考慮して購入株数を調整。
      - SELL: 始値にスリッページを適用して全量クローズ、手数料差引の純収入を計上、realized_pnl を算出。
      - mark_to_market: 終値で時価評価。終値欠損時は 0 評価で警告。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - CAGR, Sharpe Ratio（無リスク金利=0）、Max Drawdown、Win Rate、Payoff Ratio、total_trades を計算するユーティリティを実装。
    - 入力は DailySnapshot リストと TradeRecord リストのみ（DB 参照なし）。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...) を実装。
    - 実行フロー:
      - 本番 DB から必要データを抽出してインメモリ DuckDB（init_schema(":memory:")）にコピー（dates 範囲でフィルタ）。
      - 日次ループ: 前日シグナルを当日始値で約定 → positions テーブルに書き戻し → 終値で時価評価 → generate_signals（当日） → シグナル読み取り → ポジションサイジング → 次日注文準備。
      - open/close 価格取得、positions の書き戻しなど補助関数を提供。
    - 出力は BacktestResult(history, trades, metrics)。

Changed
- なし（初回リリースのため変更履歴はありません）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / 制約・既知の実装上の扱い
- 一部の設計は将来的な拡張（トレーリングストップ、時間決済、部分利確など）を想定しており、現時点では未実装の条件が明記されています（signal_generator のエグジット条件コメント等）。
- research モジュールは外部依存（pandas 等）を持たず標準ライブラリ + DuckDB で実装されています。
- DuckDB を用いるため、実行環境に duckdb が必要です。
- .env のパースは多くのケースに対応していますが、極端に複雑なシェル式はサポート外です。

今後の予定（推測）
- execution 層（実際の発注インターフェース）と monitoring（Slack 通知等）の実装拡張。
- feature / ai スコアリングの改良、レジーム判定ロジックの拡張。
- CI テスト、型チェック、ドキュメント整備や例示的な使用例の追加。

---

著: コードベースの内容から推測して作成しました。必要であれば各モジュールごとにより詳細なリリースノート（関数別の API 仕様や戻り値の詳細、例）を追記します。