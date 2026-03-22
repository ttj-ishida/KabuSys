# Changelog

すべての注目すべき変更履歴をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

フォーマットについて: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-22

初期公開版。日本株自動売買フレームワークのコア機能を提供します。  
設計方針として、研究・戦略・バックテスト層は発注 API や本番口座に直接依存しない（DuckDB を通じたデータ駆動）ことを重視しています。以下はコードベースから推測される主要な追加点・仕様・既知の制限です。

### Added
- パッケージ初期化
  - kabusys パッケージ初期化とバージョン情報 (__version__ = "0.1.0") を追加。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定をロードする Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
    - OS 環境変数は保護（上書き禁止）し、.env.local は .env を上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 必須設定の取得メソッド _require（未設定時は ValueError）。
  - デフォルト値とバリデーション:
    - KABUSYS_ENV 有効値: development / paper_trading / live（無効な値は ValueError）。
    - LOG_LEVEL 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL。
    - KABU_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
    - データベースパスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
  - Settings が提供する主なプロパティ:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- 戦略：特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を追加:
    - research 層（calc_momentum / calc_volatility / calc_value）から生ファクターを取得し正規化して features テーブルへ UPSERT（対象日を削除して挿入）を行う。
    - ユニバースフィルタ:
      - 最低株価 _MIN_PRICE = 300 円
      - 20日平均売買代金 _MIN_TURNOVER = 5e8 円（5億円）
    - 正規化:
      - 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を zscore 正規化（zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - DuckDB トランザクション（BEGIN/COMMIT/ROLLBACK）で日付単位の置換を実装し、原子性を確保。
    - ログ出力で処理結果を報告。

- 戦略：シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を追加:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news（AIニュース）コンポーネントを計算、重み付き合算により final_score を算出。
    - デフォルト重みは StrategyModel.md に基づく値を採用（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights 引数は妥当性チェック・正規化を行う（未知キーや負値などは無視）。
    - AI スコアが存在しない場合は中立値（0.5）で補完。AI の raw スコアはシグモイド変換で [0,1] に変換。
    - Bear レジーム検出（ai_scores の regime_score の平均が負かつサンプル数 >= 3 で判定）時は BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト _DEFAULT_THRESHOLD = 0.60。
    - SELL（エグジット）判定ロジック:
      - ストップロス _STOP_LOSS_RATE = -0.08（終値 / avg_price - 1 <= -8% で即SELL）
      - final_score が threshold 未満でのSELL
      - SELL 判定は BUY より優先、SELL 対象は BUY リストから除外してランクを再付与
    - signals テーブルへの日付単位置換（トランザクション処理）を実行。
    - ログで処理状況と警告を出力（features 空時の挙動、価格欠損時のスキップなど）。

- research（研究）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。必要なウィンドウ長未満なら None を返す。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover（20日平均売買代金）, volume_ratio を計算。true_range の計算で high/low/prev_close が欠損した場合は NULL 伝播を厳密に扱う。
    - calc_value(conn, target_date): raw_financials から直近財務データを取得して PER/ROE を算出（EPS が 0/NULL の場合は PER=None）。raw_financials の最新レコード取得に ROW_NUMBER を使用。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 指定ホライズンの将来リターンを計算。horizons の妥当性チェック（1..252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関を計算。十分な有効サンプル（>=3）がない場合は None。
    - rank(values): 同順位は平均ランクで処理（round(..., 12) を用いて ties の検出安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算（None 値除外）。
  - research パッケージは外部ライブラリ（pandas 等）に依存せず、DuckDB のみ利用する設計。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator: メモリ内でポートフォリオを管理（cash, positions, cost_basis, history, trades）。
    - 約定ロジック:
      - execute_orders(signals, open_prices, slippage_rate, commission_rate, trading_day): SELL を先に全量クローズ、BUY は alloc（資金配分）から株数を計算。スリッページ・手数料反映。手数料込みで買付可能株数を再計算するロジックあり。
      - mark_to_market(trading_day, close_prices): 終値で評価、終値欠損銘柄は 0 評価とし WARNING を出力。
    - TradeRecord/DailySnapshot データクラスを提供。
  - metrics:
    - calc_metrics(history, trades) により BacktestMetrics を返す（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）。
    - 内部での計算ロジック: CAGR（暦日ベース）、Sharpe（年次化、252営業日）、最大ドローダウン、勝率、ペイオフ比率等を提供。サンプル不足／ゼロ分散時の安全なフォールバック（0.0）に対応。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB から必要テーブルをインメモリ DuckDB にコピー（_build_backtest_conn）。signals / positions を汚さない設計。
      - 日次ループ:
        1. 前日シグナルを当日の始値で約定（simulator.execute_orders）
        2. positions テーブルにシミュレータ保有状態を書き戻し（_write_positions）
        3. 終値で時価評価（simulator.mark_to_market）
        4. generate_signals（bt_conn 上で）で翌日シグナル生成
        5. ポジションサイジングに基づき買付用のアロケーションを計算
      - データコピーは日付範囲でフィルタ（prices_daily, features, ai_scores, market_regime）し、market_calendar は全件コピー。
      - コピー失敗時は警告ログを出してスキップする耐障害性あり。

- パッケージ API エクスポート
  - kabusys.strategy: build_features, generate_signals を公開。
  - kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats 由来）, calc_forward_returns, calc_ic, factor_summary, rank を公開。
  - kabusys.backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。

### Fixed
- （初期リリースのため該当なし）

### Changed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 側の環境変数を保護する仕組みを導入（protected set）。.env ファイル読み込み失敗時は warnings.warn により通知。

### Known limitations / Notes（既知の制限・未実装点）
- signal_generator の SELL 条件でトレーリングストップや時間決済（保有 60 営業日超）等は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）。
- calc_value は PBR・配当利回りを未実装。
- research 層は外部 API や本番発注への直接アクセスを行わない設計（データは DuckDB の prices_daily / raw_financials などに依存）。
- calc_forward_returns の horizons は 252 日以内の整数のみをサポート。
- .env パーサは多くのケースに対応するが、全てのシェル構文を網羅するわけではない（簡易的に export/quote/comment をサポート）。
- バックテストでの資金配分ロジックはシンプル（BUY の均等配分・max_position_pct に基づく）であり、高度なポジションサイズ最適化は未実装。

---

メンテナンスやバグ修正、機能追加を行った場合は本 CHANGELOG を更新してください。