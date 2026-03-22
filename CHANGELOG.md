Keep a Changelog に準拠した CHANGELOG.md（日本語）

全般
- 本ファイルは Keep a Changelog の様式に従います。
- 変更履歴は semver に準拠します（MAJOR.MINOR.PATCH）。
- リリース日は本カタログ生成日（2026-03-22）を使用しています。

Unreleased
- （今後の変更をここに記載）

[0.1.0] - 2026-03-22
Added
- 基本パッケージ構成を実装（kabusys 名前空間、__version__ = 0.1.0、公開 API 定義）。
- 環境設定モジュールを実装（kabusys.config）。
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml に基づく）。
  - export 形式・クォート・エスケープ・インラインコメント等に配慮した .env パーサ実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - 必須環境変数チェック（_require）と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL）とデフォルトパス（DUCKDB_PATH, SQLITE_PATH）を提供。
- 戦略層を実装（kabusys.strategy）。
  - feature_engineering.build_features
    - research 側で算出した生ファクターを統合・ユニバースフィルタ（株価・平均売買代金）適用・Zスコア正規化・±3 クリップ・features テーブルへの日付単位 UPSERT（トランザクションで原子性確保）を実装。
    - 価格は target_date 以前の最新価格を参照（祝休日や当日欠損に対応）。
  - signal_generator.generate_signals
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算、重み付きで final_score を算出。
    - Bear レジーム検知（ai_scores の regime_score 平均が負の場合で判定、最小サンプル閾値あり）と Bear 時の BUY 抑制。
    - BUY（閾値: デフォルト 0.60）と SELL（ストップロス -8% 等）シグナル生成、signals テーブルへの日付単位置換（トランザクション）。
    - weights の検証・補完・再スケール処理を実装。
- Research モジュールを実装（kabusys.research）。
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR / 相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（EPS 欠損や 0 の場合は None）。
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括取得。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）計算（有効サンプルが 3 未満なら None）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリー。
  - research パッケージ public API をエクスポート。
- Backtest フレームワークを実装（kabusys.backtest）。
  - simulator.PortfolioSimulator
    - 擬似約定ロジック（BUY/SELL のスリッページ・手数料適用、SELL は全量クローズ）および日次評価（mark_to_market）、トレード記録保持を実装。
    - 約定失敗時のログ出力、手数料再計算による株数調整、平均取得単価の更新などを実装。
  - metrics.BacktestMetrics / calc_metrics
    - CAGR、Sharpe、最大ドローダウン、勝率、ペイオフ比、総トレード数を計算。
  - engine.run_backtest
    - 本番 DB からインメモリ DuckDB へデータを安全にコピーするユーティリティ（_build_backtest_conn）。
    - 日次ループ: 前日シグナルの約定 → positions 書戻し → 時価評価 → generate_signals 呼び出し → 発注リスト作成（ポジションサイジング）を実装。
    - DuckDB ベースでのデータ抽出/書き戻しヘルパー（価格取得、signals 読み出し、positions 書込）を提供。
  - BacktestResult データ構造を公開。
- 明示的な設計方針・安全策を導入
  - ルックアヘッドバイアス回避: target_date 時点のデータのみ参照して計算（各 docstring に注記）。
  - データ欠損や異常値に対する防御（None / 非有限値の扱い、ログ記録）。
  - DB 更新はトランザクション＋バルク挿入で日付単位の置換とし冪等性を確保。
  - 外部依存を最小化（research.feature_exploration は標準ライブラリのみで記述する方針を明示）。
- パッケージ公開 API を整備（各サブパッケージの __all__ / __init__ で主要関数をエクスポート）。

Fixed
- 初期リリースのため該当なし。

Changed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

注意事項（既知の設計上の未実装 / 制約）
- execution および monitoring パッケージはインターフェイスの準備はあるが、発注 API 連携や監視ロジックは本バージョンでは未実装または最小実装です。
- signal_generator の SELL 条件でドキュメントに記載されている「トレーリングストップ」「時間決済」は positions テーブルに peak_price / entry_date 等の追加フィールドが必要で、現状は未実装（コード内に注記あり）。
- research.calc_value は PBR／配当利回りを未実装（将来追加予定）。
- 実行には DuckDB 等の依存が必要（requirements によるインストールを想定）。
- run_backtest は本番 DB の複製を行うが、あるテーブルのコピー失敗はログに記録してスキップする設計のため、環境によりバックテストに必要なデータが不足する可能性あり。
- .env のパースは多くのケースをカバーしているが、特殊なフォーマットやマルチライン値などは想定外の挙動をする可能性あり。

期待される DB スキーマ（本実装が参照/更新するテーブル）
- prices_daily, raw_financials, features, ai_scores, positions, signals, market_calendar, market_regime
- 上記のカラム構成はソース内 SQL コメントおよびクエリに依存するため、スキーマ定義（kabusys.data.schema.init_schema 等）と合わせて利用してください。

環境変数（主要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意、デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意、development|paper_trading|live、デフォルト: development）
- LOG_LEVEL（任意、DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（任意、1 に設定で .env 自動読み込みを無効化）

導入メモ（簡易）
- DuckDB 等の依存をインストールし、プロジェクトルートに .env（または環境変数）を配置してください。
- 必要な DB スキーマは kabusys.data.schema.init_schema を利用して初期化してください（該当モジュール参照）。
- 単体テスト／研究用途で auto env load を無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の予定（例）
- execution 層の実装（kabusys.execution — 実際の発注 API との連携）
- monitoring 層の実装（Slack 通知等の監視・アラート）
- 未実装戦略条件（トレーリングストップ・時間決済等）の追加
- 指標・解析機能（PBR、配当利回り、拡張的 IC 分析）の追加
- 単体テストと CI 設定の整備

参照
- 各モジュールの docstring に設計方針・仕様メモを多数記載しています。具体的なアルゴリズムや SQL は該当ソースファイルを参照してください。