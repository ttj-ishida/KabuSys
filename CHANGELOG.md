CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows semantic versioning.

0.1.0 - 2026-03-22
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
- パッケージ公開情報
  - パッケージバージョン: 0.1.0
  - パッケージルート: kabusys（__all__ で data, strategy, execution, monitoring を公開）

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で利用可能）。
  - .env パーサ実装の強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - インラインコメントの扱い（クォート有無での挙動）
  - 環境変数のロード時に OS の既存環境変数を保護する protected オプションを実装（.env.local は override=True だが protected に入っているキーは上書き不可）。
  - Settings クラスを提供し、アプリが必要とする主要な設定値（J-Quants, kabu API, Slack, DB パス, env/log_level 判定等）をプロパティとして取得可能。値検証（KABUSYS_ENV, LOG_LEVEL）の実装あり。
  - 必須環境変数が未設定の場合は明確な ValueError を送出する _require 関数を実装。

- 戦略（strategy）
  - 特徴量生成 (kabusys.strategy.feature_engineering)
    - research 側で計算された生ファクター（mom/vol/value）を取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用して特徴量を作成。
    - 正規化: 指定の数値カラムを Z スコアで正規化（zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへの日付単位置換（DELETE + INSERT）をトランザクションで行い冪等性・原子性を保証。
    - ユニバースフィルタ条件: 株価 >= 300円、20日平均売買代金 >= 5億円。
    - target_date のみのデータを使用しルックアヘッドバイアスを回避。

  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して各銘柄の component score（momentum/value/volatility/liquidity/news）を計算。
    - 各 component の変換ユーティリティ（sigmoid、平均化、各スコア計算）を実装。
    - final_score を重み付き合算で計算（デフォルトウェイトは StrategyModel.md に準拠）。ユーザ提供の weights は検証（正の数値かつ既知キーのみ受入）し合計が 1.0 でなければ再スケールする。
    - Bear レジーム検知（ai_scores の regime_score 平均 < 0 かつサンプル数閾値以上で検出）時は BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄で BUY を生成。SELL は保有ポジションに対するエグジット判定（ストップロス -8% / final_score が閾値未満 等）を行う。
    - features が空の場合は BUY を生成せず SELL 判定のみ行う旨のログ出力。
    - 価格欠損時の振る舞い（価格未取得なら SELL 判定をスキップする、features に存在しない保有銘柄は score=0 と見なして SELL 判定する等）を明示的に実装。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を確保。
    - generate_signals は最終的に書き込んだシグナル数（BUY + SELL）を返す。

- Research 用ユーティリティ (kabusys.research)
  - calc_momentum / calc_volatility / calc_value を提供し、prices_daily / raw_financials から各種ファクター（mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe 等）を計算する。
  - calc_forward_returns: 指定日からの将来リターン（デフォルト horizons = [1,5,21]）を一度の SQL で取得する実装。
  - calc_ic: スピアマンランク相関（Information Coefficient）を計算。データ不足（有効サンプル < 3）は None を返す。
  - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - rank: 同順位の平均ランク（タイ同値処理）を返す。float の丸め（round(v,12)）で ties 検出の安定化を行う。
  - いずれも DB 参照は prices_daily / raw_financials に限定し、本番発注 API 等へのアクセスは行わない設計。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ (kabusys.backtest.simulator)
    - DailySnapshot / TradeRecord dataclass を定義。
    - PortfolioSimulator によりメモリ内でキャッシュ・ポジション管理、BUY/SELL の擬似約定を実行。
    - 約定ロジック: SELL を先に処理してから BUY。BUY は割当資金に基づき始値・スリッページ・手数料を考慮して購入株数を計算（不足時は再計算して調整）。
    - SELL は保有全量クローズ（部分利確/部分損切りは非対応）。
    - mark_to_market で終値評価、終値欠損時は 0 評価とし WARNING ログ出力。
  - メトリクス計算 (kabusys.backtest.metrics)
    - CAGR, Sharpe Ratio（無リスク金利=0）, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を計算するユーティリティを実装。
    - 安全なデフォルト値（サンプル不足時は 0.0）を返す実装。
  - バックテストエンジン (kabusys.backtest.engine)
    - 本番 DB からインメモリ DuckDB へ必要テーブルを日付フィルタしてコピーする _build_backtest_conn を実装（signals/positions を汚染しないため）。
    - 日次ループでの処理フローを実装:
      1. 前日シグナルを当日の始値で約定（simulator.execute_orders）
      2. simulator の positions を positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals による当日分シグナル生成（positions を参照して SELL 判定）
      5. signals から買付リストを作成して次日に約定、など
    - run_backtest のデフォルトパラメータを設定（initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known limitations / Notes
- 一部仕様は README/StrategyModel.md 等の外部ドキュメント（参照設計書）に依存する（重みや閾値の由来）。
- features / signals / positions 等のテーブルスキーマは kabusys.data.schema に依存する（本差分には schema 定義ファイルを含まず）。
- 一部未実装・将来の拡張予定:
  - _generate_sell_signals 内でのトレーリングストップや時間決済はコメントで将来的な要件として記載（positions テーブルに peak_price / entry_date 情報が必要）。
  - run_backtest 内のポジションサイジング・買付割当のロジックはベーシックな実装（詳細な資金管理や分散制約のさらなる拡張が想定される）。
- エラーハンドリングはトランザクション（BEGIN/COMMIT/ROLLBACK）＋ログで堅牢化しているが、外部環境（DuckDB IO エラー等）での例外は呼び出し元での対処が必要。

Authors
- 実装チーム（コードから推測して作成）  

ライセンス
- プロジェクトの実際のライセンス表記をリポジトリルートで確認してください。