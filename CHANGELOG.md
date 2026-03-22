# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このプロジェクトの初期リリースに相当する変更点は、コードベースから推測して記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-22
初回公開リリース。日本株自動売買システムのコアライブラリを統合したバージョンです。

### Added
- パッケージ基盤
  - パッケージメタ情報を定義（kabusys.__version__ = "0.1.0"）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env ファイルのパース機能を独自実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数を保護する protected 上書きロジック（.env.local は上書き可能だが OS 環境変数は保護）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- 戦略: 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で計算した生ファクター（momentum / volatility / value）を統合して features テーブルへ保存する build_features(conn, target_date) を実装。
  - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金 >= 5 億円）を適用。
  - 指定列の Z スコア正規化（zscore_normalize を利用）および ±3 でクリップ。
  - DuckDB 上で日付単位の置換（DELETE + INSERT をトランザクションで行い原子性を保証）。
  - ルックアヘッドバイアスを避けるため target_date 時点までのデータのみを参照。

- 戦略: シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を結合し、複数のコンポーネント（momentum, value, volatility, liquidity, news）を統合して final_score を計算する generate_signals(conn, target_date, threshold, weights) を実装。
  - デフォルト重みと閾値を実装（momentum 0.40 等、BUY閾値 0.60）。
  - ユーザー指定の weights を検証・補完・再スケールするロジック（未知キー・非数値・負値を無視）。
  - AI レジームスコアを用いた Bear レジーム判定（サンプル数が閾値未満の場合は判定を抑制）。Bear の場合は BUY シグナルを抑制。
  - BUY シグナルはスコア >= threshold の銘柄、SELL は保有ポジションに対してストップロス（-8%）またはスコア低下で判定。
  - SELL 優先のポリシー（SELL 対象銘柄は BUY リストから除外、ランク再付与）。
  - signals テーブルへの日付単位置換をトランザクションで実施（原子性保証）。
  - 欠損データ処理: コンポーネントが None の場合は中立値 (0.5) に補完、価格欠損時は SELL 判定をスキップする等の保護ロジックを実装。

- Research（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials テーブルのみ参照）。
    - momentum: 1M/3M/6M リターン、200 日移動平均乖離率（データ不足時は None）。
    - volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - value: per（株価/EPS、EPS が 0 または NULL の場合は None）、roe（最新財務データの取得）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons) — 将来リターン（複数ホライズン）を一括取得。
    - calc_ic(factors, forwards, factor_col, return_col) — スピアマンランク相関（IC）を実装（有効レコード < 3 の場合は None）。
    - factor_summary(records, columns) — count/mean/std/min/max/median の統計サマリー。
    - rank(values) — 同順位は平均ランクを返すランク関数（浮動小数点丸め対策あり）。
  - 実装方針として外部ライブラリ（pandas 等）に依存せず、DuckDB + 標準ライブラリのみで実装。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator クラスを実装。メモリ内で現金・ポジション・平均取得単価・履歴・トレードログを管理。
    - execute_orders: SELL を先に処理し全量クローズ、BUY は配分（alloc）に基づく購入。スリッページと手数料を反映。
    - mark_to_market: 終値で時価評価し DailySnapshot を記録。終値欠損時は 0 で評価し警告ログ。
    - TradeRecord と DailySnapshot dataclass を定義。
  - metrics:
    - バックテスト指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を calc_metrics(history, trades) で提供。
  - engine:
    - run_backtest(conn, start_date, end_date, ...) を実装。実稼働 DB からインメモリ DuckDB に必要データをコピーして日次ループを実行。
    - _build_backtest_conn: 本番 DB から指定日付範囲のテーブル（prices_daily, features, ai_scores, market_regime, market_calendar など）をインメモリ DB にコピー。
    - 日次処理フローを実装（前日シグナル約定 -> positions 書き戻し -> 時価評価 -> generate_signals -> ポジションサイジング -> 発注）。
    - positions テーブルへシミュレータ状態を冪等的に書き込むユーティリティを提供。
    - signals の読み取りユーティリティを提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 注意事項
- DB スキーマ依存:
  - 多くの関数は DuckDB の特定テーブル（prices_daily, features, ai_scores, raw_financials, positions, signals, market_calendar 等）とカラム名を前提としています。実行前にスキーマが期待通りであることを確認してください（kabusys.data.schema.init_schema を参照する想定）。
- ルックアヘッド回避:
  - feature / signal / research モジュールは target_date 時点までのデータのみを使用するよう設計されています（バックテストの過学習・リークを防止）。
- 自動 .env ロードの挙動:
  - 自動読み込みはプロジェクト構造の検出に依存し、配布後に想定外の動作となる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。
- 標準的なログ出力を多用:
  - 内部で logger を利用し、WARN/INFO/DEBUG の出力を行います。LOG_LEVEL 設定により挙動を変更可能です。
- 未実装の機能（将来的な拡張メモ）:
  - signal_generator のエグジット条件にて、トレーリングストップや時間決済（保有 60 営業日超）に関連するデータ（positions に peak_price / entry_date）が現時点では必要であり未実装箇所がある旨のコメントが含まれます。

### Security
- 機密情報（API トークン等）は環境変数で管理する設計です。 .env の取り扱いに注意してください。

---

以上はソースコードから推測した変更点・機能一覧です。リリースノートやバージョン管理の運用方針に合わせて、公開後の実績・修正点に応じて更新してください。