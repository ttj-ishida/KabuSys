CHANGELOG
=========
このファイルは Keep a Changelog の形式に準拠しています。
https://keepachangelog.com/ja/1.0.0/

注: 以下の変更内容はリポジトリ内のソースコードから推測して作成しています。

## [0.1.0] - 2026-03-22

Added
-----
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージエントリポイント: src/kabusys/__init__.py にて
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用）
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント規則に対応
  - protected オプションにより OS 環境変数を上書きから保護
  - Settings クラスを提供し、アプリケーションで必要な設定値をプロパティ経由で取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得関数を用意（未設定時は ValueError を送出）
    - duckdb/sqlite のデフォルトパス、KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジックを実装
    - is_live / is_paper / is_dev のユーティリティプロパティを提供

- ファクター計算（research 層）
  - calc_momentum / calc_volatility / calc_value を実装 (src/kabusys/research/factor_research.py)
    - momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）
    - volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率
    - value: 最新の raw_financials から EPS/ROE を参照して PER/ROE を算出
    - SQL + DuckDB を用いた実装（外部ライブラリに依存しない設計）
  - 研究用ユーティリティ群 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 任意ホライズンの将来リターン計算（horizons データ検証、最大 252 日）
    - calc_ic: スピアマンの秩相関（ランク）を計算する IC 実装（同順位は平均ランク）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出
    - rank: 同順位（ties）処理ありのランク関数
  - research パッケージの __all__ を整備

- 特徴量エンジニアリング（strategy 層）
  - build_features を実装 (src/kabusys/strategy/feature_engineering.py)
    - research で算出した raw ファクター（mom/vol/value）を合成して features テーブルへ書き込み
    - ユニバースフィルタ実装:
      - 株価 >= 300 円 (_MIN_PRICE)
      - 20 日平均売買代金 >= 5 億円 (_MIN_TURNOVER)
    - 正規化: 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）
    - 外れ値処理: Z スコアを ±3 でクリップ
    - 日付単位での置換（DELETE + INSERT）をトランザクションで実行し冪等性と原子性を保証

- シグナル生成（strategy 層）
  - generate_signals を実装 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントスコアの算出ロジックを実装:
      - momentum: momentum_20, momentum_60, ma200_dev の平均（シグモイド変換）
      - value: PER を逆数的に変換（PER=20で0.5）
      - volatility: atr_pct の反転シグモイド（低ボラ = 高スコア）
      - liquidity: volume_ratio のシグモイド
      - news: ai_score のシグモイドまたは未登録時は中立
    - 重み付けと閾値:
      - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
      - ユーザー指定 weights の妥当性検証（未知キー・負値・非数を無視）、合計が 1.0 になるよう再スケール
      - BUY の閾値デフォルト 0.60
    - Bear レジームフィルタ:
      - ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合は Bear と判定し BUY を抑制
    - エグジット（SELL）判定:
      - ストップロス: (close / avg_price - 1) < -8% を優先的に SELL
      - スコア低下: final_score < threshold の場合 SELL
      - features に存在しない保有銘柄は final_score=0 として SELL 判定対象にする（警告ログ）
    - signals テーブルへの日付単位置換（DELETE + INSERT）をトランザクションで実行し冪等性を保証
    - ロギングを充実（WARN/INFO/DEBUG）

- バックテストフレームワーク (src/kabusys/backtest)
  - PortfolioSimulator の実装 (src/kabusys/backtest/simulator.py)
    - シンプルな約定ロジック（SELL 先、BUY 後）
    - スリッページと手数料を反映した約定価格と手数料計算
    - BUY: 購入株数は floor(alloc / entry_price)、手数料込みで不足する場合は再計算して調整
    - SELL: 保有全量をクローズ、realized_pnl を計算して TradeRecord に保存
    - mark_to_market: 終値で時価評価し DailySnapshot を記録（終値欠損時は 0 として WARN）
  - バックテストメトリクス (src/kabusys/backtest/metrics.py)
    - CAGR, Sharpe (年換算252日), Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算
    - trades と history のみを入力にとる純粋関数設計
  - バックテストエンジン (src/kabusys/backtest/engine.py)
    - run_backtest を実装
      - 本番 DB からインメモリ DuckDB へ必要テーブルを日付範囲でコピーしてテスト用接続を作成（signals/positions を汚さない）
      - market_calendar を全件コピー
      - 日次ループ:
        1. 前日シグナルを当日始値で約定（simulator.execute_orders）
        2. positions テーブルにシミュレータの保有状態を書き戻す（generate_signals の SELL 判定で参照）
        3. 終値で時価評価・スナップショット記録
        4. generate_signals を呼んで翌日用シグナルを生成
        5. signals を読み出しポジションサイジング（max_position_pct に基づく割当）
    - _build_backtest_conn によりコピー時の範囲制限・エラーハンドリングを実装
    - 各種ユーティリティ: _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals を実装

Changed
-------
- （初リリースのため変更履歴はありません）

Fixed
-----
- （初リリースのため修正履歴はありません）

Deprecated
----------
- （初リリースのため未廃止）

Removed
-------
- （初リリースのため未削除）

Security
--------
- 環境変数読み込みに関して、.env ファイル読み込み失敗時は warnings.warn を発行してプロセスを中断しない実装（IO エラーの取り扱いを安全に実装）
- 秘密情報は Settings クラスで必須チェックを行い、未設定時は ValueError を投げる（安全な初期化を促す）

Notes / 実装上の設計方針
---------------------
- DuckDB を主要なデータ基盤として使用。各モジュールは DuckDB 接続を受け取って SQL と Python の組合せで処理を行う（外部ネットワークアクセスを避ける設計）。
- 研究（research）コードと運用（strategy/backtest）コードを明確に分離。運用側は研究側の生ファクターを参照して正規化・合成する。
- ルックアヘッドバイアスを防ぐため、すべての計算は target_date 時点のデータのみを参照するよう設計。
- ロギングと入力検証を重視し、不正なパラメータやデータ欠損時に WARN/ERROR を出力して安全マージンを確保。
- トランザクション（BEGIN/COMMIT/ROLLBACK）＋ DELETE→INSERT のパターンで日次データの置換を行い、冪等性と原子性を確保。

既知の未実装 / TODO（コード内コメントより）
----------------------------------------
- signal_generator の SELL 条件に以下が未実装:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有期間 60 営業日超）
- 一部の機能は raw_financials の整備やデータの完全性に依存

Copyright
---------
- 本 CHANGELOG はソースコードの内容に基づく推測により作成されています。実際の変更履歴やリリースノートはリポジトリのコミットログ・リリース管理に基づいて作成してください。