CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

0.1.0 - 2026-03-22
-----------------

Added
- 初回公開リリース。
- パッケージ構成
  - kabusys パッケージを追加。主要サブパッケージ/モジュール:
    - kabusys.config: 環境変数 / 設定管理（自動 .env ロード、設定検証）
    - kabusys.research: 研究用ファクター計算・探索ユーティリティ
    - kabusys.strategy: 特徴量エンジニアリングとシグナル生成
    - kabusys.backtest: バックテスト用エンジン・シミュレータ・メトリクス
    - kabusys.execution: モジュールプレースホルダ（パッケージ公開時のエクスポート対象）
- 設定管理（kabusys.config）
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動でプロジェクトルートを探索し、.env/.env.local を読み込む実装を導入（CWD に依存しない）。
  - .env パーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント判定（空白の前の # のみをコメント扱い）に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途想定）。
  - Settings クラスを導入し、主要設定をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）。
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（Path を返す）。
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- リサーチ機能（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: target_date 以前の最新財務データと株価から PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 与えられたホライズンでの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを与えるランク関数。
  - research パッケージ __all__ に主要関数をエクスポート。
  - 実装は DuckDB の prices_daily / raw_financials テーブルのみを参照する設計（外部 API へアクセスしない）。
- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールで計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）適用、Z スコア正規化（指定カラム）→ ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション + バルク挿入）する処理を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を算出して BUY/SELL シグナルを生成。
    - デフォルト重みと閾値を定義（デフォルト threshold=0.60）。weights 引数は検証・正規化され、未知キーや不正値は無視。
    - Sigmoid 変換、欠損コンポーネントの中立値(0.5)補完、Bear レジーム検知（AI の regime_score 平均が負で一定数以上のサンプルがある場合）により BUY を抑制。
    - 保有ポジションに対するエグジット判定を実装（ストップロス -8%、final_score が閾値未満）。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）。
- バックテスト（kabusys.backtest）
  - simulator.PortfolioSimulator:
    - SELL を先に処理、BUY は資金に応じて約定。スリッページ・手数料を適用し、約定記録 (TradeRecord) と日次スナップショット (DailySnapshot) を保持。
    - mark_to_market で終値評価、終値欠損時は 0 で評価して警告ログ。
  - metrics.calc_metrics: history/trades から CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、総トレード数を計算するユーティリティ。
  - engine.run_backtest:
    - 本番 DB からバックテスト用に必要テーブルを日付範囲でコピーしてインメモリ DuckDB を構築（signals/positions を汚染しない）。
    - 日次ループで約定、positions 書き戻し（generate_signals が参照するため）、時価評価、generate_signals 呼び出し、発注リスト組立て、次日の約定処理。戻り値として BacktestResult（history, trades, metrics）を返す。
    - market_calendar は全件コピー。コピーに失敗したテーブルは警告ログでスキップ。
- トランザクション保護とロールバック
  - features / signals への日付単位置換処理で BEGIN/COMMIT/ROLLBACK を用いて原子性を確保。ROLLBACK 失敗時は警告ログを出力。

Fixed / Improved
- SQL の NULL/欠損ハンドリングを丁寧に実装（例: true_range や prev_close が NULL の場合、ATR 集計やスコア計算に影響しないように制御）。
- .env 読み込み失敗時は warnings.warn を出して処理を継続するよう改善（致命的クラッシュを回避）。
- weights の入力検証を強化し、不正値（非数値、NaN/Inf、負値、bool）はスキップして安全にフォールバックするように実装。
- generate_signals / _generate_sell_signals で価格欠損時に判定をスキップして誤クローズを防止（ログ出力あり）。

Known issues / Limitations
- 一部のエグジット条件は未実装（コメントに記載）:
  - トレーリングストップ（peak_price 情報が positions に無いため未実装）
  - 時間決済（保有 60 営業日超過など）
- features 側で per（PER）は Z スコア正規化の対象外（逆スコア化の扱いとして設計上除外）。
- ai_scores が未登録の場合、ニューススコアは中立（0.5）で補完される。
- Settings の必須環境変数が未設定だと ValueError を投げるため、環境変数の準備が必要。
- execution モジュールはパッケージのエクスポート対象に含まれるが、個別の実装（外部 API 呼び出し等）は本リリースの範囲外またはプレースホルダとなっている。

Breaking Changes
- 本が初回リリースのため、既存利用者向けの破壊的変更はありません。ただし Settings の必須環境変数（JQUANTS_REFRESH_TOKEN 等）が未設定だと実行時に例外が発生しますので注意してください。

Security
- .env ファイルの自動ロードはデフォルトで有効だが、テストや CI 環境向けに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数は読み込み時に保護（上書き禁止）されるよう実装。

その他
- パッケージバージョンは kabusys.__version__ = "0.1.0"。

今後の予定（例）
- execution 層の具体的な注文送信実装（kabuステーションや証券 API との接続）
- モニタリング・アラート機能（Slack 連携の活用等）
- 未実装エグジット条件（トレーリングストップ・時間決済）の実装
- performance 改善（大規模データセット向けのクエリ最適化）

--- 
この CHANGELOG は、ソースコードのコメント・実装内容から推測して作成しています。実際のリリースノートとして使用する際は必要に応じて調整してください。