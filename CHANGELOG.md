CHANGELOG
=========

この変更履歴は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルには重要な変更点と新機能を記録します。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 日本株自動売買システムのコアライブラリを追加。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ロード実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD 非依存でパッケージ配布後も動作。
    - 読み込み順序: OS 環境変数 > .env.local（上書き）> .env（未設定のみ）。
    - OS 環境変数を保護する protected キーセットを利用して意図しない上書きを防止。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサは以下に対応:
    - 空行 / コメント行（# 開始）の無視。
    - export KEY=val 形式のサポート。
    - クォート（' または "）を考慮した値のパース（エスケープシーケンスを処理）。
    - クォートなしのインラインコメント判定（# の直前がスペース/タブの場合のみコメント扱い）。
  - Settings クラスを提供（プロパティ経由でアプリ設定取得）
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - システム設定: KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL（DEBUG/INFO/... 検証）
    - is_live / is_paper / is_dev ヘルパー

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で計算した生ファクターを統合して features テーブルへ書き込む build_features(conn, target_date) を実装。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value からファクター取得
    - ユニバースフィルタ（最低株価・最低平均売買代金）適用
      - 最低株価: 300 円
      - 最低 20 日平均売買代金: 5 億円
    - 指定列の Z スコア正規化（zscore_normalize を利用）、±3 でクリップ（外れ値抑制）
    - 日付単位での置換（DELETE + バルク INSERT）により冪等性と原子性を確保（トランザクション使用）
  - DuckDB を用いる SQL ベース実装、欠損値の扱いに注意

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
  - デフォルトの重み・閾値等:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - BUY 閾値: 0.60
    - ストップロス閾値: -8%
    - Bear 判定に必要な最小サンプル数: 3
  - 実装上の特徴:
    - シグモイド変換で Z スコアを [0,1] に変換、欠損コンポーネントは中立値 0.5 で補完
    - AI ニューススコア未登録時は中立（0.5）補完、レジームスコアで Bear 相場を判定（平均が負の場合）
    - SELL（エグジット）判定:
      - ストップロス（最優先）
      - final_score が閾値未満
      - 価格欠損時は判定をスキップして誤クローズを防止
    - BUY/SELL を日付単位で置換（トランザクション＋バルク挿入）で冪等性を確保
    - weights 引数は検証・補完・正規化される（未知キーや不適切な値は無視）

- リサーチユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離率）を計算
      - ルックバックやウィンドウは営業日ベース（近似のためカレンダーバッファを使用）
    - calc_volatility: 20 日 ATR（atr_20）、atr_pct（相対 ATR）、avg_turnover（20 日平均売買代金）、volume_ratio を計算
      - true_range の NULL 伝播制御により ATR のカウント精度を担保
    - calc_value: raw_financials を元に per / roe を計算（直近報告書を使用）
    - すべて DuckDB SQL ベースで prices_daily / raw_financials のみ参照（外部 API なし）
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得
      - horizons の入力検証（正の整数かつ <= 252）
      - パフォーマンス対策としてカレンダーバッファを使用してスキャン範囲を制限
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算
      - None 値除外、有効レコードが 3 未満なら None を返す
      - ties 対策として値を round(..., 12) で丸めてランク付け
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクで処理

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ (kabusys.backtest.simulator)
    - PortfolioSimulator クラスを実装
      - initial_cash から開始、positions / cost_basis / history / trades を管理
      - execute_orders: SELL を先に処理、BUY は資金に応じて株数を算出（切り捨て）
      - スリッページと手数料の適用（BUY は始値*(1+slippage), SELL は始値*(1-slippage)）
      - BUY の際、手数料込みで購入可能な株数に再計算
      - SELL は保有全量をクローズ（部分利確未対応）
      - mark_to_market: 終値で時価評価、終値欠損は 0 評価して WARNING を出力
    - TradeRecord / DailySnapshot dataclass を定義
  - メトリクス計算 (kabusys.backtest.metrics)
    - calc_metrics により BacktestMetrics を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）
    - 各指標の実装詳細（年次化や分散計算など）を実装
  - エンジン (kabusys.backtest.engine)
    - run_backtest(conn, start_date, end_date, ...) を実装
      - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（signals / features 等は日付範囲でフィルタ）
      - market_calendar は全件コピー
      - 日次ループ:
        1. 前日シグナルを当日始値で約定
        2. positions を DB に書き戻し（generate_signals の SELL 判定に必要）
        3. 終値で時価評価・スナップショット記録
        4. generate_signals を呼び出して当日分の signals を生成
        5. ポジションサイジング（max_position_pct デフォルト 0.20）して翌日の約定リスト作成
      - run_backtest は (history, trades, metrics) を BacktestResult として返す
    - 内部ユーティリティ:
      - _build_backtest_conn: データコピー時の例外を捕捉してログ出力
      - _fetch_open_prices / _fetch_close_prices: 指定日の価格取得
      - _write_positions: 冪等に positions を書き込む
      - _read_day_signals: signals テーブルから BUY/SELL を読み出す

- その他
  - パッケージ __init__ でバージョン (0.1.0) と公開 API を定義
  - kabusys.strategy と kabusys.research の __all__ を整備
  - execution パッケージのプレースホルダを追加（将来的な発注層実装用）
  - ロギングを各モジュールで利用し、例外時はロールバック失敗や I/O エラー等を WARN として記録する実装を採用
  - DuckDB を中心とした SQL ベース処理により、本番 DB 参照を最小化（バックテストでは in-memory を使用）

Fixed
- 初版のため該当なし

Changed
- 初版のため該当なし

Removed
- 初版のため該当なし

Security
- 初版のため該当なし

Notes / 実装上の注意
- すべてのデータ処理モジュールはルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ参照）を重視しています。
- 外部 API 呼び出しや本番発注はこのバージョンでは実装を分離しており、strategy 層と execution 層の依存を切り離す方針です。
- DuckDB のスキーマ初期化や zscore_normalize 等は kabusys.data 側のユーティリティに依存しています（このリリースで参照実装あり）。
- 現在未実装の機能（トレーリングストップ、時間決済、部分利確など）はコード内コメントで明記しています。