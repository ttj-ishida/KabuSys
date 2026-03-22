# Changelog

すべての重要な変更点は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-22

初期リリース — 日本株自動売買システム "KabuSys" のコアライブラリを追加。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。パッケージ公開用の主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
    - .env/.env.local の読み込み順（OS環境変数 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式やクォート・エスケープ、行内コメント処理に対応したパーサを実装。
    - Settings クラスを提供（J-Quants / kabu API / Slack / データベースパス / env/log_level バリデーション、is_live/is_paper/is_dev 補助プロパティ）。
    - 必須環境変数未設定時は _require() が ValueError を投げる。

- 戦略・特徴量処理
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date): research で計算した生ファクターを集約・ユニバースフィルタ適用・Zスコア正規化（±3 でクリップ）し、features テーブルへ日付単位の置換（トランザクション＋バルク挿入で冪等）で書き込む。
    - ユニバースフィルタ（最低価格・最低平均売買代金）実装。
    - Z スコア正規化は kabusys.data.stats.zscore_normalize を利用。
    - トランザクション失敗時のロールバックおよびロギング処理を実装。

  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、final_score に基づいて BUY/SELL シグナルを作成、signals テーブルへ日付単位の置換で書き込む（冪等）。
    - AI レジームスコアに基づく Bear 判定実装（サンプル不足時の誤判定回避ロジックあり）。
    - BUY シグナルは閾値・Bear 抑制・SELL 優先ルールで生成。SELL 対象は BUY から除外してランク付けし直す。
    - weights の検証・既定値フォールバック・再スケール処理を実装（未知キーや無効値は無視）。
    - SELL の判定ロジックにストップロス（-8%）とスコア低下を実装。positions と prices の欠損時に安全にスキップ・警告ログを出力。

- Research（研究）機能
  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターンおよび MA200 乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility(conn, target_date): ATR20、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算（部分窓の扱いを明確化）。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER/ROE を計算。EPS 欠損や 0 の場合の取り扱いを定義。
    - すべて DuckDB 接続（prices_daily / raw_financials）だけを参照し、本番 API へはアクセスしない設計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons): 翌日/翌週/翌月などの将来リターンを計算。horizons の妥当性検査（1〜252）を実装。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算を実装（有効レコードが 3 件未満なら None）。
    - rank(values): 同順位の平均ランク処理を含むランク変換ユーティリティ（丸めによる ties 対応）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー関数。
    - 実装は標準ライブラリのみで依存を持たない設計。

  - src/kabusys/research/__init__.py
    - 主要ユーティリティ（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）をエクスポート。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: 擬似約定（スリッページ・手数料モデル）とポートフォリオ状態管理を実装。BUY/SELL の約定ロジック、平均取得単価管理、mark_to_market（終値で評価）および DailySnapshot/TradeRecord データ構造を提供。
    - SELL は保有全量クローズ（部分利確非対応）。約定時の始値欠損はスキップして警告を出力。
    - mark_to_market は終値欠損時に 0 評価で WARNING を出す。

  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を実装。
    - 端数・エッジケース（データ不足・ゼロ除算）に対する安全なデフォルト（0.0）を定義。

  - src/kabusys/backtest/engine.py
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へデータをコピーし、日次ループで generate_signals を呼び出してシミュレーションを実行するエンジンを実装。戻り値は BacktestResult（history, trades, metrics）。
    - _build_backtest_conn: 日付範囲で必要なテーブルを切り出してインメモリ DB にコピー（market_calendar は全件コピー）。コピー失敗時は警告ログを出す安全設計。
    - 日次処理の流れ（前日シグナル約定 → positions 書き戻し → mark_to_market → generate_signals → ポジションサイジング→次日の約定準備）を実装。
    - positions テーブルへの冪等書き戻し関数 _write_positions を実装。generate_signals の SELL 判定が positions を参照するための連携を考慮。

- モジュールエクスポート整備
  - src/kabusys/strategy/__init__.py, src/kabusys/backtest/__init__.py にて主要関数/クラスを整理してエクスポート。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Notes / Implementation details
- DB 書き込み処理は日付単位の削除→挿入で置換を行い、トランザクション＋バルク挿入で原子性と冪等性を担保する設計。
- 多くの箇所でデータ欠損（価格/財務データ/AI スコア等）を安全に扱い、欠損値は中立値で補完するか処理をスキップして警告ログを出す方針を採用。
- 重み・閾値・閾値に関するデフォルト値は StrategyModel.md / BacktestFramework.md に基づく設計思想を反映。
- 本リリースはあくまでライブラリコアであり、外部接続（発注 API 等）や CLI/UI、テスト用モックは含まれない。DuckDB をデータレイヤとして重視し、外部依存（pandas 等）は避ける設計。

---- 

今後の予定（例）
- 部分利確・トレーリングストップ・時間決済などのエグジット戦略の追加
- execution 層（kabu API 連携）・monitoring 層（Slack 通知等）実装
- テストカバレッジ拡充と CI 設定

（必要であれば、各モジュールごとのより詳細な変更点や想定される入力/出力スキーマを追記します。）