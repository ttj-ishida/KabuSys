CHANGELOG
=========

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- 基本パッケージとバージョン
  - pakage: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境設定 / 自動 .env 読み込み (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルートの検出は __file__ を起点に親ディレクトリから .git または pyproject.toml を探索することで行う（配布後も CWD に依存しない挙動）。
  - .env / .env.local の自動読み込みを実装（読み込み順: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途に便利）。
  - .env パーサは以下に対応:
    - export KEY=val 形式
    - シングル・ダブルクォート内でのエスケープシーケンス処理
    - インラインコメントの扱い（クォート外で直前が空白またはタブの場合に '#' をコメントとみなす）
  - 自動上書きの制御: override フラグと OS 環境変数を保護する protected セットをサポート。
  - 必須変数が未設定の場合は _require() が ValueError を投げる。設定キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - 設定検証: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の妥当性チェックを実装。

- 戦略: 特徴量作成パイプライン (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで計算された生ファクターを取り込み、正規化して features テーブルへ UPSERT する build_features(conn, target_date) を実装。
  - パイプライン:
    1. calc_momentum / calc_volatility / calc_value から生ファクターを取得
    2. ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用
    3. 指定カラムを Z スコア正規化（外れ値は ±3 でクリップ）
    4. 日付単位で DELETE → INSERT（トランザクションで原子性を保証）
  - 正規化対象カラムや閾値（_MIN_PRICE, _MIN_TURNOVER, _ZSCORE_CLIP）は定数で管理。
  - DuckDB を直接利用して価格取得・一括挿入を行う。

- 戦略: シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
  - スコア計算:
    - momentum/value/volatility/liquidity/news のコンポーネントを計算（シグモイド変換や PER の逆スケール等）。
    - NONE（欠損）コンポーネントは中立値 0.5 で補完。
    - デフォルト重みは StrategyModel.md に準拠（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定 weights は検証・補完・正規化される。
  - Bear レジーム判定: ai_scores の regime_score の平均が負なら Bear（サンプル数が閾値未満の場合は Bear とみなさない）。
  - BUY 判定は閾値（デフォルト 0.60）以上、Bear レジーム時は BUY を抑制。
  - SELL 判定（エグジット）:
    - ストップロス（終値が平均取得価格から -8% 以下）
    - final_score が threshold 未満
    - 保有銘柄で価格が取得できない場合は判定をスキップ（誤クローズ防止）
  - signals テーブルへ日付単位で置換（DELETE → INSERT、トランザクションで原子性を担保）。

- research モジュール (src/kabusys/research/)
  - factor_research: calc_momentum, calc_volatility, calc_value を追加。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA のカウントチェックを含む）
    - calc_volatility: 20日 ATR（true range の NULL 伝播を考慮）、atr_pct、avg_turnover、volume_ratio
    - calc_value: raw_financials から最新財務データ（report_date <= target_date）を取得し PER / ROE を算出
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons) — 指定ホライズン(デフォルト [1,5,21]) の将来リターンを一度のクエリで取得
    - calc_ic(factor_records, forward_records, factor_col, return_col) — Spearman の ρ（ランク相関）を計算
    - rank(values) — 同順位は平均ランクで処理（丸めで ties 検出の安定化）
    - factor_summary(records, columns) — count/mean/std/min/max/median を算出
  - いずれも DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API 等にはアクセスしない設計。

- バックテストフレームワーク (src/kabusys/backtest/)
  - simulator:
    - PortfolioSimulator: メモリ内ポートフォリオ管理（cash, positions, cost_basis, history, trades）。
    - 約定ロジック:
      - execute_orders: SELL を先に処理、BUY は割当額から発注（shares は floor）。
      - スリッページ・手数料モデルの適用（slippage_rate, commission_rate）。
      - SELL は保有全量をクローズ（部分利確・部分損切りは非対応）。
      - mark_to_market: 終値で評価し DailySnapshot を記録（終値欠損は 0 として評価し警告）。
    - TradeRecord と DailySnapshot の dataclass を提供。
  - metrics:
    - calc_metrics(history, trades) → BacktestMetrics（CAGR, Sharpe, MaxDrawdown, Win rate, Payoff ratio, total trades）。
    - 内部アルゴリズム: CAGR（暦日ベース）、Sharpe（年次化、252 営業日基準）、MaxDrawdown、勝率・ペイオフ比の計算。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB からインメモリ DuckDB へ必要テーブルを日付範囲でコピー（prices_daily, features, ai_scores, market_regime, market_calendar 等）。signals/positions を汚染しない設計。
      - 日次ループ:
        1. 前日シグナルを当日始値で約定
        2. シミュレータの positions を positions テーブルへ書き戻し（generate_signals の SELL 判定に必要）
        3. 終値で時価評価しスナップショット記録
        4. generate_signals を実行して翌日のシグナルを生成
        5. ポジションサイジング（max_position_pct 制約）
      - デフォルトのスリッページ/手数料/初期資金等を指定

Changed
- 初期リリースにより変更履歴無し。

Fixed
- 初期リリースにより修正履歴無し。

Known limitations / TODOs
- signal_generator/_generate_sell_signals の未実装項目（コメント記載）:
  - トレーリングストップ（peak_price が positions に存在することが前提）
  - 時間決済（保有 60 営業日超過）
- calc_value は PBR / 配当利回りを未実装（コメントで明記）。
- simulator の SELL は全量クローズのみ。部分利確・部分損切り非対応。
- features 正規化に用いる zscore_normalize は data.stats 側で提供（このリリースに含まれるが詳細実装は別ファイル）。
- 一部の DB コピー処理では例外発生時にテーブルのコピーをスキップする（ログ警告）。データ欠損やスキーマ差異に注意。
- 戦略やリサーチ関数は DuckDB のテーブル構造（カラム名／nullable 性）に依存するため、スキーマ変更時は影響あり。

Notes
- ログ機能を広く利用しているため、運用時は LOG_LEVEL の設定とログ出力先の整備を推奨します。
- 自動 .env 読み込みは便利だが、OS 環境変数の保護を行うため .env.local の override 挙動や KABUSYS_DISABLE_AUTO_ENV_LOAD に注意してください。

--- 

（以上）