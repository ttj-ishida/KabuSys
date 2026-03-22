CHANGELOG
=========

このプロジェクトは Keep a Changelog のフォーマットに準拠しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

0.1.0 - 2026-03-22
-----------------

Added
- 初期公開リリース。
- パッケージ構成を追加:
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラス（プロパティ経由で設定値を取得）。
    - 必須環境変数未設定時に ValueError を投げる _require()。
    - サポートする環境値（KABUSYS_ENV = development | paper_trading | live）とログレベル検証。
  - kabusys.research
    - factor_research モジュール:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算。
      - calc_volatility: 20 日 ATR／相対 ATR（atr_pct）、20 日平均売買代金、出来高比率の計算。
      - calc_value: raw_financials と prices_daily を用いた PER / ROE の計算。
    - feature_exploration モジュール:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
      - calc_ic: スピアマンのランク相関（IC）計算。
      - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
      - rank: 同順位は平均ランクとするランク付けユーティリティ。
    - research パッケージの API エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize の再エクスポートを含む）。
  - kabusys.strategy
    - feature_engineering.build_features:
      - research で計算した生ファクターをマージ、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
      - 指定カラムの Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
      - features テーブルへの日付単位 UPSERT（トランザクション＋バルク挿入で冪等性を確保）。
    - signal_generator.generate_signals:
      - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
      - momentum/value/volatility/liquidity/news の各コンポーネントを計算するユーティリティ実装。
      - デフォルト重みと閾値（DEFAULT_WEIGHTS / DEFAULT_THRESHOLD）、ユーザー重みの検証と正規化（合計を 1.0 に再スケール）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）による BUY 抑制。
      - エグジット条件（ストップロス、スコア低下）に基づく SELL シグナル生成。
      - signals テーブルへ日付単位の置換（トランザクションで原子性）。
    - strategy パッケージ API エクスポート（build_features, generate_signals）。
  - kabusys.backtest
    - simulator:
      - PortfolioSimulator（ポートフォリオ状態管理、BUY/SELL の擬似約定、スリッページ・手数料モデル）。
      - DailySnapshot / TradeRecord のデータクラス。
      - 実装上のルール：SELL を先に処理、SELL は保有全量クローズ、手数料は約定金額に対する率で計算、始値がない場合はログ出力して処理スキップ。
      - mark_to_market による時価評価と履歴記録（終値欠損時は 0 で評価し WARNING を出力）。
    - metrics:
      - バックテスト指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - engine.run_backtest:
      - 本番 DB からインメモリ DuckDB へ必要データをコピーして日次バックテストを実行するワークフロー。
      - _build_backtest_conn によるテーブルの期間フィルタ付きコピー（prices_daily, features, ai_scores, market_regime, market_calendar）。
      - 日次ループ: 前日シグナルを当日始値で約定 → positions を書き戻し → 終値評価 → generate_signals 呼び出し（次日のシグナル生成）→ サイジングして次営業日のオーダーを作成。
      - 公開 API として run_backtest をエクスポートし、BacktestResult を返却。
  - kabusys.config の .env パースロジックは POSIX 風の export KEY=val、クォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート。
- 共通設計上の防御的実装:
  - 多くの関数で欠損データに対する安全処理（None / NaN / Inf チェック）を実装。
  - generate_signals では欠損コンポーネントを中立値 0.5 で補完し、欠損データによる不当な降格を防止。
  - トランザクション + バルク挿入で日付単位の置換を行い冪等性を確保。

Changed
- （なし、初回リリース）

Fixed
- （なし）

Removed
- （なし）

Security
- （なし）

Known limitations / TODO / 注意事項
- 未実装の機能（コード内コメントに記載）:
  - トレーリングストップ（peak_price / entry_date を positions テーブルに保持する必要）。
  - 時間決済（保有 60 営業日超過での強制決済）。
  - バリュー指標の一部（PBR・配当利回り）は現バージョンでは未実装。
- features テーブルには avg_turnover は保存しない（ユニバースフィルタ時のみ使用）。必要に応じてスキーマ拡張が必要。
- execution パッケージは空（将来的に発注層との結合を実装予定）。monitoring も __init__ で参照されているが具象実装は含まれていない点に注意。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後や特殊なレイアウトのプロジェクトでは動作しない可能性あり。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- generate_signals は ai_scores が小さいサンプル数の場合に Bear 判定を行わない（_BEAR_MIN_SAMPLES）。
- calc_forward_returns の horizons は営業日ベースであり、入力は正の整数かつ <= 252（チェックあり）。
- バックテストのデータコピー処理は例外を握りつぶしてコピーをスキップする実装（警告ログ）。必要なテーブルがコピーされないとバックテスト結果に影響するため注意。
- バックテストの期間設定・デフォルトパラメータ（スリッページ/手数料/最大ポジション比率）は今後調整する可能性あり。

開発者向けメモ
- 主要な公開 API:
  - kabusys.settings: 設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, is_live/is_paper/is_dev）
  - kabusys.strategy.build_features(conn, target_date) -> int
  - kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=None) -> int
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.backtest.run_backtest(conn, start_date, end_date, ...) -> BacktestResult
  - kabusys.backtest.simulator.PortfolioSimulator, DailySnapshot, TradeRecord
  - kabusys.backtest.metrics.calc_metrics
- version はパッケージの __init__ にて __version__ = "0.1.0" として設定。

今後のリリース候補
- execution 層の実装（kabu API / 発注ロジックの結合）。
- monitoring（Slack 通知等）実装。
- features / signals のスキーマ拡張（avg_turnover, peak_price, entry_date 等）。
- 追加のエグジットロジック（トレーリングストップ、時間決済）。
- より詳細なテスト、型注釈の強化、CI による自動チェック導入。