# Changelog

すべての公開リリースの変更履歴は Keep a Changelog の形式に従って記述します。  
このファイルはコードベースの実装内容から推測して作成しています（実際のコミット履歴ではありません）。

フォーマット:
- Unreleased: 今後の変更予定
- 各リリースはバージョンと公開日を示します

## [Unreleased]

- ドキュメント化・テストの追加、運用監視の強化を予定。
- 細かな挙動改善（例: price フォールバック、lot_size の銘柄毎対応など）を検討中。

## [0.1.0] - 2026-04-17

初回リリース（推定）。以下の主要機能・実装を含みます。

### Added
- アプリケーション全体の設定管理
  - Settings クラスを導入し、環境変数経由で各種設定を取得（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH など）。
  - J-Quants / kabuステーション / LINE 関連の設定プロパティを提供。
  - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。不正値で例外を送出。
  - paper_trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。

- .env 自動読み込み・パーサー
  - プロジェクトルート（.git または pyproject.toml）から .env/.env.local を自動ロード。
  - .env の行パースを独自実装（export キー対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントルール）。
  - OS 環境変数を保護するための上書きルール（.env.local は上書き、既存 OS 環境変数は保護）。

- 設定ウィザード CLI
  - python -m kabusys.config_setup で対話式に .env を初期作成/更新するウィザードを提供。
  - 主要な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を支援。
  - 生成される .env のテンプレートは秘匿項目をマスク表示。

- 設定検証 CLI
  - python -m kabusys.validate_config で環境変数・config/*.yaml の存在と基本的妥当性を検証。
  - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば内容検証）などを実施。
  - --strict モードで警告も失敗扱いにできる。

- 実行系・監視プロセス起動スクリプト
  - run_execution.py: ExecutionEngine 起動エントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 専用 DB（data/paper_trading.db など）に記録して本番 DB と分離する設計。
    - 停止フラグ (data/stop_requested.flag) の検知による安全停止、pid ファイル管理、スレッドでのエンジン実行制御。
    - Execution に必要なコンポーネント（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立て。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を用意。initial_portfolio_value は broker.get_available_cash() を使用。

  - run_monitoring.py: SystemMonitor のポーリングループ起動用スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。無効値はフォールバックして警告。
    - 監視 (monitoring) は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを一元化。
    - 停止フラグ (data/stop_requested.flag) によるループ停止処理、例外発生時はログを残して次ポーリングへ継続。

- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db(sqlite_conn) を呼び出して監視用テーブルの存在を保証（冪等）。

- 実用ユーティリティ
  - process_priority.py: psutil を用いたプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) により Windows / POSIX を吸収して優先度を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定可能（未サポート環境や権限不足時は警告）。
  - 起動時にプロセス優先度を "high" に設定する呼び出しを run_* スクリプトで実行。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights: N 分割の等金額配分。
    - calc_score_weights: スコア正規化による配分。全てのスコアが 0.0 の場合は等分配にフォールバックして WARNING を出力。

  - risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは 1.0 で警告ログ。

  - position_sizing.py
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、per-stock の最大上限（max_position_pct）や aggregate cap（available_cash）を考慮してスケールダウン。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト見積りと、端数分配ロジック（fractional remainder に基づく lot_size 単位での再配分）を実装。
    - 価格欠損時はログを出してスキップ。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルからファクター（Momentum, Value, Volatility, Liquidity）を計算する機能の実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。データ不足対応。
    - calc_volatility: ATR, 相対 ATR, 20 日平均売買代金、出来高比率を計算する処理（途中まで実装）。
    - 計算窓やスキャン日数は定数化（例: 200 日 MA, ATR 20 日など）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 集計指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg / max / P95）。
    - P95 計算ロジック、日付フィルタ（--from / --to）、閾値による PASS/FAIL 判定を実装。
    - デフォルト閾値: 稼働率 >= 99.0%、fill >= 90%、send >= 95%、P95 latency <= 200 ms。

- パッケージ情報
  - kabusys/__init__.py にて __version__ = "0.1.0" を設定。

### Changed
- 初回リリースのため変更履歴はなし（初期実装）。

### Fixed
- 初回リリースのため修正履歴はなし（初期実装）。

### Notes / 運用上の注意
- 監視プロセスは MONITOR_POLL_INTERVAL によるポーリング間隔制御をサポート。0 以下や非整数の値は無効と見なしてデフォルト 60 秒にフォールバックする。
- run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計（監視データの一元化）。
- run_execution は paper_trading 環境では DB を分離しているため、本番データと混在しないが、運用時は PAPER_TRADING_SQLITE_PATH の設定を確認すること。
- process priority / cpu affinity の設定は権限・OS に依存し、失敗すると警告ログのみでスキップする実装。
- .env は絶対に Git にコミットしないこと（config_setup で注意喚起を記載）。
- config/*.yaml の存在確認は PyYAML がインストール済みであればパース検証を行う（未インストール時は警告を出す）。

### Potential future improvements（既コード中の TODO 等）
- price 欠損時のフォールバック（前日終値や取得原価）を position sizing / sector exposure に導入。
- lot_size を銘柄ごとに持たせる（stocks マスタに lot_size フィールドを追加）。
- factor_research の残り実装（ボラティリティ集計の完了、Value ファクターの ROE/PER 取得など）。
- テスト追加（ユニット/統合）と CI ワークフロー整備。

---

この CHANGELOG はコードの現状から実装内容を推測してまとめたものです。実際のコミット履歴やリリースノートを作成する際は、各コミットや PR の記録に基づいて更新してください。