# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__ に基づきます。

## [0.1.0] - 初回リリース
公開日: 未設定

概要: 日本株自動売買システム「KabuSys」の最初のリリースです。バックテスト、ファクター計算、特徴量生成、シグナル生成、環境設定など、戦略開発と検証に必要な主要コンポーネントを実装しています。以下に主な追加機能と設計上の注意点を記載します。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - モジュール群: data, strategy, execution, monitoring（公開 API 用 __all__）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護されて上書きされないように実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの取り扱い（クォート有無で挙動を区別）
  - Settings クラスによる環境変数ラップ:
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）や必須チェック（_require）を実装
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）
    - is_live / is_paper / is_dev の便宜プロパティ

- 研究用ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算
    - calc_value: raw_financials から最新財務データを取得し PER, ROE を計算
    - DuckDB のウィンドウ関数を用いて効率的に集計（営業日→カレンダー日バッファ取り扱い）
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（ties は平均ランク）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算
    - rank ユーティリティ: 同順位は平均ランク、丸めによる ties 検出漏れを抑制

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得
    - ユニバースフィルタ: 最低株価（300 円）、20 日平均売買代金（>= 5 億円）を適用
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize）および ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）し冪等性を保証
    - 欠損・外れ値に対する頑健化とログ出力

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.6, weights=None):
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - 各コンポーネントはシグモイド変換等で [0,1] に変換し、欠損は中立値 0.5 で補完
    - デフォルト重みを提供（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
    - ユーザー指定 weights の検証・補完・再スケーリング（無効値の警告ログ）
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合に BUY を抑制）
    - BUY 生成: threshold を超える銘柄（ランク付け）、SELL 生成: ポジションに対するエグジット条件（ストップロス、スコア低下）
    - signals テーブルへ日付単位で置換（DELETE + bulk INSERT）し冪等性を保証
    - SELL が BUY を優先排除するポリシーを実装

- バックテストフレームワーク (src/kabusys/backtest/)
  - simulator.py
    - PortfolioSimulator: メモリ上のポートフォリオ状態管理、約定ロジック、マーク・トゥ・マーケット
    - execute_orders: SELL を先に処理、BUY は配分 alloc に基づき始値で約定（スリッページ・手数料考慮）
    - BUY の際の平均取得単価更新・現金管理・手数料再計算（手数料込みで購入株数再調整）
    - SELL は保有全量をクローズし realized_pnl を記録
    - mark_to_market: 終値評価、終値欠損時は 0 評価で警告ログ
    - DailySnapshot / TradeRecord の dataclass 定義
  - metrics.py
    - calc_metrics と評価指標の実装: CAGR, Sharpe Ratio（無リスク 0 を仮定）, Max Drawdown, Win Rate, Payoff Ratio, total_trades
    - 内部補助関数はエッジケース（データ不足・ゼロ分散等）に対して安全なデフォルトを返す
  - engine.py
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 conn からインメモリ DuckDB に必要テーブルをコピーしてバックテスト専用接続を構築（signals/positions を汚さない）
      - 日次ループ: 前日シグナルの約定 → positions 書き戻し → 終値で評価 → generate_signals 呼び出し → 発注配分生成
      - get_trading_days の使用、取引日の列挙・ループ処理
      - 内部で使用するユーティリティ: _build_backtest_conn / _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals
    - BacktestResult の dataclass 定義（history, trades, metrics）

- パッケージの公開エントリポイント (各 __init__.py で主要関数・クラスをエクスポート)

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 設計上の注意・制約
- DuckDB を中心に設計しており、ほとんどの処理は DB（prices_daily / raw_financials / features / ai_scores 等）を前提とする。
- ルックアヘッドバイアスを防ぐため、すべての時系列計算は target_date 時点のデータまたはそれ以前のみを参照するように設計。
- 外部ライブラリ（pandas 等）への依存を避け、標準ライブラリ + duckdb での実装を優先。
- 発注 API / execution 層への直接依存は持たない（signals テーブルを介して分離）。
- 冪等性を重視：features や signals、positions への書き込みは日付単位の削除→挿入で原子性を確保（トランザクションを使用）。
- ログと例外処理を通じて欠損データ・不正入力に対する防御的な挙動を記録する。

### 既知の未実装（将来タスク）
- Signal の一部エグジット条件（トレーリングストップ、時間決済など）は未実装（コメントで明示）。
- PBR・配当利回り等のバリューファクターは現バージョンで未実装。
- strategy.execution 層（実際の注文発行）はパッケージに含まれていない（execution パッケージは空のプレースホルダ）。

---

今後のバージョンでは、ドキュメントの充実、追加ファクター・リスク管理機能、外部 API 連携（発注／マーケットデータ）、およびパフォーマンス最適化を予定しています。