CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
本プロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-22
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py（__version__ = 0.1.0、__all__ = ["data", "strategy", "execution", "monitoring"]）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは以下に対応：
    - 空行・コメント行（#）の無視、export KEY=val 形式のサポート。
    - シングル/ダブルクォート、バックスラッシュエスケープ処理、インラインコメントの扱い。
  - Settings クラス（settings インスタンス）のプロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別 KABUSYS_ENV（development/paper_trading/live のバリデーション）および LOG_LEVEL バリデーション
    - is_live / is_paper / is_dev ユーティリティプロパティ
  - 必須環境変数未設定時は ValueError を送出する安全設計。

- 戦略関連（src/kabusys/strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールの生ファクターを結合・正規化して features テーブルへ保存する build_features(conn, target_date) を実装。
    - 処理フロー：
      1. calc_momentum / calc_volatility / calc_value からファクター取得
      2. ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）適用
      3. 指定列を Z スコア正規化し ±3 でクリップ
      4. DuckDB 上で日付単位の置換（トランザクション + バルク挿入）により冪等で書き込み
    - ルックアヘッドバイアス回避の設計（target_date 時点のデータのみ使用）。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - 機能概要：
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
      - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
      - final_score を重み付けして算出（デフォルト重みは source 内で定義）。
      - Bear レジーム判定（ai_scores の regime_score の平均が負の場合。ただし十分なサンプル数が必要）。
      - BUY（閾値以上）・SELL（エグジット条件：ストップロス -8% または score 低下）を生成。
      - SELL を優先し、signals テーブルへ日付単位の置換で書き込み（冪等）。
    - 重みの受け入れと検証、合計が 1.0 でない場合の再スケール、無効な重みの警告などを実装。
    - 欠損データや価格欠損時にはログ出力で安全性を確保（不完全なデータで誤発注を防止）。

- 研究用モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、MA200 乖離を計算（データ不足は None）。
    - calc_volatility(conn, target_date)：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
    - calc_value(conn, target_date)：raw_financials から最新財務（EPS/ROE）を結合し PER/ROE を算出（EPS が 0 または欠損の場合は None）。
    - DuckDB 上のウィンドウ関数を活用し、営業日ベースの窓を想定した実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])：複数ホライズンの将来リターンを計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（IC）を計算（有効サンプル < 3 の場合は None）。
    - factor_summary(records, columns)：count/mean/std/min/max/median を返す統計サマリー。
    - rank(values)：同順位は平均ランクとして扱うランク関数実装。
  - これらは外部 API に依存せず、DuckDB の prices_daily/raw_financials のみを参照する設計。

- バックテストフレームワーク（src/kabusys/backtest）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator クラスを実装。メモリ内状態管理（cash, positions, cost_basis, history, trades）。
    - 約定ロジック（execute_orders）：SELL を先に処理、BUY は割当 alloc に基づく株数算出、スリッページ・手数料考慮、手数料込みで株数再計算、平均取得単価更新。
    - mark_to_market による終値評価と DailySnapshot 記録。終値欠損は 0 評価で警告ログ。
    - TradeRecord/DailySnapshot の dataclass 定義。
  - 評価指標（src/kabusys/backtest/metrics.py）
    - calc_metrics(history, trades) による BacktestMetrics 計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 内部で使用する計算関数（年次化・分散計算・ドローダウン等）を実装。
  - エンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...) を実装。
    - 本番 DB からインメモリ DuckDB へ必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を日付範囲でコピーする _build_backtest_conn。
    - 日次ループ：
      1. 前日シグナルを当日の始値で約定（simulator.execute_orders）
      2. positions を DuckDB に書き戻し（_write_positions） — generate_signals の SELL 判定に必要
      3. 終値評価（simulator.mark_to_market）
      4. generate_signals を呼び翌日用シグナル生成
      5. ポジションサイジング・BUY リスト作成・次日約定準備
    - open/close 価格取得ユーティリティ（_fetch_open_prices/_fetch_close_prices）と signals の読み取り関数を提供。
    - run_backtest は BacktestResult（history, trades, metrics）を返す。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Deprecated
- （なし）

Removed
- （なし）

Security
- 環境変数の未設定時は明示的に ValueError を発生させる設計により、意図しない動作（例: API トークンなしでの実行）を抑止。
- .env 読み込みは OS 環境変数を保護（既存キーは上書きしない、.env.local は override）する実装を採用。

Notes / 既知の制約・未実装項目
- 戦略側
  - 一部エグジット条件（トレーリングストップ、時間決済）は未実装（コード内に TODO 記載）。これらは positions テーブルに peak_price / entry_date 等の追加情報が必要。
  - per（PER）の正規化（逆数スコア変換）は feature_engineering の NORM 列に含まれず、別途扱いの設計になっている点に注意。
  - PBR・配当利回りは現バージョンでは未実装。
- バックテスト
  - run_backtest におけるデータコピーは日付範囲に基づく単純コピーであり、大量データ時のメモリ使用に注意。
- 汎用
  - DuckDB を前提とした SQL 実装。入力テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals, market_calendar 等）が期待するスキーマで存在することが前提。
  - 外部依存（発注 API 等）へは直接アクセスしない安全設計。ただし production execution 層（execution/monitoring）との統合は別途。

今後の予定（例）
- トレーリングストップや時間決済などエグジット条件の実装
- PBR / 配当利回りの追加
- より柔軟なポジションサイジング・部分利確対応
- 単体テスト・CI の充実、ドキュメントの拡張

以上。必要であれば各モジュール毎の変更点をさらに細かく分けたリリースノート（関数一覧・引数説明・ログ出力の挙動など）を作成します。どの粒度がよいか指示してください。