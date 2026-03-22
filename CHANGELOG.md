CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
初回リリース v0.1.0 の内容は、コードベースから推測できる機能追加・設計方針・既知の制限をまとめたものです。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-22
--------------------

Added
- 初期リリース: kabusys パッケージの基本機能を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
  - 独自の .env パーサを実装:
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - インラインコメント判定（クォート外で # の前がスペース/タブの場合はコメント扱い）などの扱い
    - 読み込み失敗時は警告を発行
  - 設定ラッパークラス Settings を提供（settings インスタンスをエクスポート）
    - 必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - DB パスのデフォルト（DUCKDB_PATH, SQLITE_PATH）
    - KABUSYS_ENV 検証（development, paper_trading, live のみ許容）
    - LOG_LEVEL 検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev のブールプロパティ

- 戦略モジュール (kabusys.strategy)
  - feature_engineering.build_features
    - research 環境で計算された生ファクターを統合・正規化して features テーブルへ書き込み
    - 処理フロー:
      1. calc_momentum / calc_volatility / calc_value で生ファクター取得
      2. ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）
      3. 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）
      4. Z スコアを ±3 でクリップ
      5. 日付単位で DELETE→INSERT のトランザクション（冪等性）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照
  - signal_generator.generate_signals
    - features テーブルと ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ書き込み
    - 特徴:
      - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）
      - ユーザ重みの検証（未知キーや非数値、負値、NaN/Inf を除外）、合計が 1.0 でなければ再スケール
      - AI スコアが無ければ neutral 値（0.5）で補完
      - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル >= 3 の場合）
        - Bear の場合は BUY シグナルを抑制
      - エグジット判定（SELL）:
        - ストップロス: 終値 / avg_price - 1 < -8%
        - スコア低下: final_score < threshold
      - positions テーブルを参照して保有銘柄のエグジット判定を実施
      - 日付単位で DELETE→INSERT のトランザクション（冪等性）
      - エラー時の ROLLBACK を試み、失敗ログを残す仕組み

- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1/3/6 ヶ月リターン、200日移動平均乖離率を計算（prices_daily を参照）
    - calc_volatility: 20日 ATR, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播に注意）
    - calc_value: 最新財務データ（raw_financials）と当日の株価を使って PER, ROE を計算
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクにするランク関数（float 丸め対策あり）
  - DuckDB のみ参照し、外部依存（pandas 等）なしで実装

- バックテストフレームワーク (kabusys.backtest)
  - simulator.PortfolioSimulator
    - メモリ内でポートフォリオ状態を管理し、約定（擬似約定）を実行
    - SELL を先に処理し全量クローズ、BUY は資金・手数料を考慮して購入株数を決定
    - スリッページ・手数料モデルを適用（引数で slippage_rate / commission_rate 指定可能）
    - mark_to_market で DailySnapshot を蓄積し、終値欠損時は警告出力して 0 評価
    - TradeRecord / DailySnapshot の dataclass を定義
  - metrics.calc_metrics
    - history（DailySnapshot）と trades（TradeRecord）から各種メトリクスを計算
      - CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, Total Trades
  - engine.run_backtest
    - 本番 DuckDB からインメモリ DuckDB へデータをコピーしてバックテストを実行
      - コピー対象テーブル: prices_daily, features, ai_scores, market_regime（指定日範囲）
      - market_calendar は全件コピー
      - コピー用 start 範囲は start_date - 300 日（features 等の履歴のため）
    - 日次ループ:
      1. 前日シグナルを当日始値で約定（simulator.execute_orders）
      2. positions を DB に書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価（mark_to_market）
      4. generate_signals を呼出し翌日シグナルを生成
      5. シグナルを読み取り発注リストを組立（ポジションサイジング）
    - DuckDB 接続を分離して本番テーブルを汚染しない設計

- パッケージ再エクスポート
  - backtest / research / strategy の主要関数・クラスを __init__ 経由で公開

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Known issues / 限界・未実装
- トレーリングストップや時間決済（保有 60 営業日超）などの一部エグジット条件は未実装（コメント記載）。
  - 実装には positions テーブルに peak_price / entry_date の追跡が必要。
- signal_generator 側で AI スコアが無い場合は中立（0.5）で補完するため、AI スコアがない環境では AI の影響は無効化される。
- generate_signals / build_features のトランザクションは DuckDB の制約に依存。極端な例外時のロールバック失敗時は警告を出す設計。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布先でルートが検出できない場合は自動ロードがスキップされる（手動で環境設定する必要あり）。
- 一部モジュールは kabusys.data のユーティリティ（zscore_normalize, init_schema, calendar_management 等）へ依存しており、それらの実装により挙動が変わる可能性がある（本ログは提示されたコード範囲からの推測）。

Notes（設計上の方針）
- ルックアヘッドバイアスを防ぐため、各処理は target_date 以前のデータのみを参照するよう設計されている。
- 発注 API や本番口座への直接アクセスは行わない（戦略層と execution 層の分離）。
- DuckDB を主要なデータ処理基盤とし、SQL と純 Python を組み合わせて高効率な集計を行う方針。
- ロギングと警告を多用してデータ欠損や不整合時の挙動を明示する実装。

今後の作業候補（推奨）
- トレーリングストップ・時間決済条件の実装（positions に peak_price / entry_date を保持）
- signal_generator のユニットテスト、バックテストの end-to-end テスト整備
- AI スコア連携部分の検証・異常値処理（Regime 判定のロバスト化）
- ドキュメント（StrategyModel.md / BacktestFramework.md 等）の充実と実装差分の整合性確認

----