# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリースはセマンティックバージョニングに従います。

※この CHANGELOG は提示されたコードベースから実装内容を推測して作成しています。

## [0.1.0] - 2026-03-22

### Added
- パッケージ初期リリース "kabusys" を追加。
  - src/kabusys/__init__.py にパッケージ名・バージョン (0.1.0) と公開サブパッケージ一覧を定義。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env のパースロジックを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 読み込み時の上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - Settings クラスを提供し、必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティで取得。値検証（KABUSYS_ENV、LOG_LEVEL）を実装。
  - データベースファイルパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）を提供。

- 戦略関連（feature engineering / signal generation）を追加。
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算された生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）を適用して特徴量を生成。
    - Zスコア正規化を行い ±3 でクリップ。features テーブルへ日付単位で冪等に UPSERT（DELETE + BULK INSERT）する build_features(conn, target_date) を実装。
    - 外れ値処理、価格欠損・データ不足への耐性を考慮。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合してファクター毎のスコアを計算し、最終スコア final_score を重み付き合算で算出する generate_signals(conn, target_date, ...) を実装。
    - デフォルト重み・閾値を仕様（StrategyModel.md に準拠）として組み込み。ユーザ渡しの weights は検証・補完・再スケールされる。
    - Bear レジーム検出（AI の regime_score 平均が負の場合）による BUY 抑制を実装。
    - 保有ポジションに対するエグジット判定（ストップロス、スコア低下）を実装し、SELL シグナルを生成。
    - signals テーブルへ日付単位で冪等に書き込む（トランザクション + バルク挿入）。

- リサーチ用ユーティリティ群（src/kabusys/research/*）を追加。
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日不連続や部分窓を考慮した計算を行う。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出（calc_forward_returns）、IC（スピアマン順位相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - pandas 等の外部依存無しで標準ライブラリ + DuckDB を想定した実装。
  - research パッケージ __init__ で主要関数・ユーティリティをエクスポート。

- データ系ユーティリティとの統合ポイント
  - feature_engineering や research モジュールは kabusys.data.stats.zscore_normalize 等のユーティリティを利用する想定（外部モジュールへの参照を定義）。

- バックテストフレームワークを追加（src/kabusys/backtest/*）。
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理、BUY/SELL の疑似約定ロジックを実装。
    - スリッページ / 手数料モデル、SELL を先に処理する方針、BUY の資金再計算（手数料込み）などを実装。
    - mark_to_market で終値評価・日次スナップショット（DailySnapshot）を記録。
    - TradeRecord/ DailySnapshot のデータクラス定義を提供。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、トレード数）を計算する calc_metrics を実装。
    - 個別の内部計算関数（_calc_cagr, _calc_sharpe, _calc_max_drawdown, _calc_win_rate, _calc_payoff_ratio）を提供。
  - src/kabusys/backtest/engine.py
    - run_backtest(conn, start_date, end_date, ...) を実装。実行フロー:
      1. 本番 DuckDB からバックテスト用インメモリ DuckDB へ必要テーブルを日付範囲でコピー（_build_backtest_conn）。
      2. 日次ループで前日のシグナルを当日始値で約定、positions テーブルへ書き戻し、終値評価、generate_signals による翌日シグナル生成、ポジションサイジング・約定準備を実施。
    - _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals 等の補助関数を実装。
    - BacktestResult を返す（history, trades, metrics）。

- パッケージの公開インターフェースを整備（strategy/__init__.py、backtest/__init__.py、research/__init__.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み中のファイル I/O エラーは警告出力してフェールしない挙動を採用（.env 読み込み失敗時の堅牢化）。

---

注記:
- 多くの関数は DuckDB の接続オブジェクト（DuckDBPyConnection）を引数に取り、prices_daily / raw_financials / features / ai_scores 等のテーブルを参照する設計です。これらのテーブルスキーマは data パッケージ（kabusys.data.schema 等）で管理される想定です。
- ドキュメント参照箇所（StrategyModel.md, BacktestFramework.md 等）は実装方針の説明に使用されています。実運用前にドキュメントとスキーマの整合性を確認してください。