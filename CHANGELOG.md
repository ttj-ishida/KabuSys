CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従っています。
（フォーマット: https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
- なし

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージの初期リリース。
  - パッケージメタ: kabusys v0.1.0（src/kabusys/__init__.py）
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索する実装で CWD に依存しない設計。
  - 高度な .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォートの取り扱い（バックスラッシュエスケープ考慮）
    - インラインコメント判定の細かい仕様（クォートあり/なしでの挙動）
  - 自動ロードの優先順: OS 環境変数 > .env.local > .env
  - OS の既存環境変数を保護する protected オプション実装（上書き禁止）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化（テスト等向け）
  - Settings クラスを公開し、必須環境変数チェック（_require）と型変換/検証を提供（JQUANTS, KABU, Slack, DB パス等）
  - env / log_level の許容値チェック（不正な値は ValueError）

- 戦略・特徴量処理（src/kabusys/strategy）
  - feature_engineering.build_features:
    - research モジュールからの生ファクター取得（calc_momentum / calc_volatility / calc_value）
    - ユニバースフィルタ（最低株価・平均売買代金閾値）適用
    - 指定カラムの Z スコア正規化（zscore_normalize を利用）および ±3 でのクリップ
    - features テーブルへの日付単位の置換（DELETE + INSERT）のトランザクション実装で冪等性と原子性を保証
    - 欠損データや価格欠損に対する安全な取り扱い
  - signal_generator.generate_signals:
    - features と ai_scores を統合して final_score を計算（モメンタム/バリュー/ボラティリティ/流動性/ニュース）
    - デフォルト重み・閾値の実装（重みの検証・正規化を行い不正値は警告して無視）
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）
    - Bear レジーム検知（AI の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）
    - BUY シグナルの生成（Bear レジーム時は抑制）
    - SELL（エグジット）判定の実装:
      - ストップロス（終値/avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
    - signals テーブルへの日付単位の置換（トランザクション実装）
    - ログ出力による欠損・警告情報の記録

- リサーチ機能（src/kabusys/research）
  - factor_research: momentum / volatility / value の計算関数を実装
    - mom_1m/mom_3m/mom_6m, ma200_dev 等の計算
    - atr_20, atr_pct, avg_turnover, volume_ratio 等のボラティリティ・流動性指標
    - raw_financials を用いた per/roe の算出（最新報告日以前を参照）
    - DuckDB のウィンドウ関数を活用して効率的に取得
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）での将来リターン計算（一括クエリ）
    - calc_ic: スピアマンランク相関（IC）計算（ランク計算、ties の平均ランク処理）
    - factor_summary: count/mean/std/min/max/median の統計サマリー
    - rank: 値リストを同順位平均ランクで変換（round を用いた安定化）
  - research パッケージは pandas 等外部ライブラリに依存せず、DuckDB のみ使用する設計

- バックテスト（src/kabusys/backtest）
  - simulator: PortfolioSimulator（擬似約定・ポートフォリオ管理）
    - BUY/SELL の約定ロジック、スリッページ・手数料適用、平均取得単価の更新、全量クローズ方針
    - mark_to_market で終値評価と日次スナップショット記録（欠損終値は 0 に評価して警告）
    - TradeRecord / DailySnapshot dataclass 定義
  - metrics: バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）
  - engine.run_backtest:
    - 本番 DuckDB からインメモリ DuckDB へ必要データをコピーしてバックテスト用接続を作成（signals/positions を汚染しない）
    - コピー対象・日付範囲の制限（パフォーマンス配慮）
    - market_calendar の全件コピー
    - 日次ループ:
      1. 前日シグナルを当日始値で約定
      2. positions テーブルへシミュレータ状態を書き戻し（generate_signals の SELL 判定で参照）
      3. 終値で時価評価・履歴記録
      4. generate_signals を実行して翌日分のシグナルを生成
      5. 発注リストを組み立てポジションサイジング（max_position_pct 等を使用）
    - テーブルコピーが失敗した場合は該当テーブルのコピーをスキップし警告を出力

Changed
- トランザクション管理を各所に導入（features / signals の日付単位置換処理）して原子性を確保。
- 重みや閾値の扱いを堅牢化（不正なユーザ指定値の検出とフォールバック/再スケーリング）。

Fixed
- なし（初期リリース）

Security
- .env 読み込みで OS 環境変数を上書きしない既定動作を採用。OS 変数は protected として上書きから除外。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止を提供（CI/テスト向け）。

Performance / Implementation notes
- DuckDB のウィンドウ関数や一括クエリを多用し、必要範囲のデータだけをスキャンする設計（スキャンレンジにバッファを設けて祝日対応）。
- zscore 正規化は kabusys.data.stats.zscore_normalize に委譲（外部に依存しない内部ユーティリティとして想定）。
- バックテスト時はインメモリ DB に必要な期間だけコピーすることで本番 DB への負荷と副作用を低減。

Known issues / Limitations
- エグジット条件（signal_generator）で未実装の方針:
  - トレーリングストップ（peak_price が positions に必要だが 現バージョンで未保持）
  - 時間決済（保有日数ベースの自動決済）
- PortfolioSimulator は SELL を「全量クローズ」で処理し、部分利確／部分損切りはサポートしない。
- 約定は始値ベースの擬似約定のみ（成行/指値/約定板シミュレーション等は未実装）。
- generate_signals は features が空の場合に BUY を生成せず SELL 判定のみを実施する（ログ出力あり）。
- ai_scores が不足する場合のレジーム判定はサンプル閾値を用いて誤判定を抑止しているが、データ不足時の挙動に注意。
- テーブルコピー中に例外が発生したテーブルはスキップされる（バックテスト結果が不完全になりうるため警告を確認のこと）。

API（公開シンボル）
- kabusys.config.settings: 設定アクセス
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=None, weights=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.backtest.PortfolioSimulator / DailySnapshot / TradeRecord / BacktestMetrics

その他
- コード、SQL、アルゴリズムのドキュメントや設計指針（StrategyModel.md, BacktestFramework.md 等）を参照する設計になっているため、実運用前にこれらの仕様確認を推奨します。