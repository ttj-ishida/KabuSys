# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。システム全体の初期リリース相当の内容を、コードベースから推測してまとめています。

## [0.1.0] - 2026-03-22

このバージョンはパッケージの初期公開相当のリリースです。日本株自動売買システムのコア機能（設定管理、ファクター計算、特徴量作成、シグナル生成、バックテスト基盤、シミュレータ、評価指標）を実装しています。

### Added
- パッケージ初期構成
  - kabusys パッケージ（__version__ = 0.1.0）を追加。公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml をルート判定）。
  - OS 環境変数を保護する読み込み順序（OS env > .env.local > .env）と override の挙動。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - 複雑な .env 行パース（export 形式、クォート内のエスケープ、インラインコメントの扱い）を実装。
  - Settings クラスを提供：
    - 必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値付き設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）。
    - env 値の検証（development, paper_trading, live）とログレベル検証。

- ファクター計算（kabusys.research.factor_research）
  - モメンタム（1M/3M/6M リターン、200日移動平均乖離率）calc_momentum を実装。
  - ボラティリティ / 流動性（20日 ATR、相対 ATR、20日平均売買代金、出来高比）calc_volatility を実装。
  - バリュー（PER、ROE）calc_value を実装。raw_financials から最新財務を取得して価格と結合。

- 研究支援ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
  - スピアマンランク相関（IC）calc_ic と rank ユーティリティ（同順位は平均ランク）。
  - factor_summary によるファクターの統計要約（count, mean, std, min, max, median）。
  - 外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルに日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
  - データ不足や欠損への堅牢なガード（None / 非数値扱い）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
    - final_score を重み付き合算（デフォルト重みは README/StrategyModel 相当の値を採用）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合）。
    - BUY は threshold（デフォルト 0.60）超で生成、Bear 時には BUY 抑制。
    - SELL はストップロス（-8%）および final_score の低下で判定（positions と最新価格を参照）。
    - signals テーブルへの日付単位置換（原子性のためトランザクションを使用）。
    - 重みのバリデーションと自動リスケール機能、無効な重みはスキップ。

- バックテストフレームワーク（kabusys.backtest）
  - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DuckDB からインメモリ DuckDB へ必要テーブルを日付範囲でコピー（start_date - 300 日のバッファ）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions テーブル更新 → 終値で時価評価 → generate_signals 呼び出し → 発注（ポジションサイジング）ループ。
    - signals の読み取り、positions 書き戻し、open/close 価格取得ユーティリティを提供。
  - PortfolioSimulator（kabusys.backtest.simulator）
    - 日次スナップショット（DailySnapshot）と TradeRecord のモデルを提供。
    - execute_orders: SELL を先に処理、BUY は残余現金で分配。SELL は保有全量クローズ。
    - スリッページ（デフォルト率をパラメータ化）と手数料率を反映した約定処理。
    - mark_to_market による終値評価と履歴記録（終値欠損時は 0 評価で WARNING）。
  - バックテストメトリクス（kabusys.backtest.metrics）
    - calc_metrics(history, trades) で BacktestMetrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を算出。

- データユーティリティ
  - zscore_normalize を含むデータ正規化ユーティリティを data.stats から利用可能（research/__init__ で再エクスポート）。

### Changed
- （初期リリースのため無し）

### Fixed
- （初期リリースのため無し）

### Deprecated
- （初期リリースのため無し）

### Removed
- （初期リリースのため無し）

### Security
- （現時点で特筆すべきセキュリティ修正は無し。ただし環境変数に機密情報を保持するため .env の取り扱いには注意）

### Notes / Known limitations
- 一部のエグジット条件は未実装（コード注釈に明記）:
  - トレーリングストップ（直近最高値から -10%）未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）未実装。
- generate_signals は features が空の場合、BUY を生成せず SELL 判定のみ行う挙動。features 欠損銘柄は final_score を 0.0 扱いで SELL 判定対象となる（ログ出力あり）。
- calc_forward_returns は horizons の妥当性チェックを行い、252 日超のホライズンは拒否（安全策）。
- .env パーサは多くのケースをカバーするが、極端なフォーマットの .env 行で予期せぬ動作をする可能性あり。
- DuckDB への依存がある（ソースコードは DuckDB 接続を前提として設計）。

---

将来的なリリースでは、以下を注力予定（TODO の想定）:
- execution 層の実装（kabu API 連携）と安全な発注ロジック。
- monitoring（Slack 通知等）モジュールの充実。
- より詳細なテストカバレッジと静的型注釈整備（型チェック強化）。
- 一部未実装のエグジットルール（トレーリング、時間決済）の追加。

もし CHANGELOG の書き方（フォーマットや日付）や記載追加を希望される箇所があれば教えてください。コードから読み取れる範囲で追記・修正します。