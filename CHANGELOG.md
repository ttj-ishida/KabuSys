# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-24

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- 基本パッケージとメタ情報
  - パッケージ初期化とバージョン設定を追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は KABUSYS_ENV に依らず本番用 sqlite_path を使用。
    - 停止はプロジェクト下の data/stop_requested.flag ファイルで検出。
    - DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理を実装。
    - スレッド実行によるエンジン起動と安全な停止処理を実装。

- 設定管理と検証
  - config.py: 環境変数読み込み・ラッパー Settings を実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出 .git / pyproject.toml 基準）。
    - export KEY=val やクォート付き値、インラインコメント処理に対応した .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
    - 設定値の検証（env/log level/各種パス/紙取引設定など）を行うプロパティ群を実装。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 sqlite パス、しきい値等をプロパティで提供。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在/パース確認（PyYAML が無い場合はスキップ）などを実装。
    - --strict オプションで警告を失敗扱いにできる。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。
    - よく使う設定項目の質問/デフォルト、シークレット入力マスク、保存機能を提供。
    - .env 書き込みテンプレート（.env に絶対にコミットしない旨のヘッダ）を生成。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定ユーティリティを追加。
    - コンソール出力（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR の優先解決ロジックを持つ。
    - ログディレクトリ作成失敗時はファイル出力をスキップして安全に継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD） を吸収した実装。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(n) を提供。
    - 権限不足等の例外を安全にログ警告で扱う。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抽出。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター時価に基づき新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告と 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベース計算、単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash によるスケーリング）、cost_buffer 考慮、端数再配分アルゴリズムを実装。
    - 価格欠損時のスキップやログ出力による可視化を行う。

- 調査用ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH）を読み、システム稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計して判定（PASS/FAIL）を出力。
    - デフォルト基準値（稼働率 >= 99%、成立率 >= 90% 等）で判定。
    - 日付フィルタ（--from / --to）と --db オプションに対応。

- 研究/計算 基盤（着手）
  - research/factor_research.py: ファクター計算モジュールを追加（設計と一部実装）。
    - Momentum / Value / Volatility / Liquidity といったファクター群の計算方針を実装予定。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定しようとします（set_process_priority）。権限がない環境では警告ログを出してスキップします。
- .env のパース実装は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポートします。既存 OS 環境変数は保護され、.env.local による上書きが可能です。
- Paper Trading 環境では sqlite DB を分離して実データと干渉しないようにしています。
- ログは標準出力にも出力するため、cron/Task Scheduler などから起動した場合のログ集約がしやすくなっています。
- 一部モジュール（research/factor_research.py）は実装途中で末尾が切れている箇所があるため、今後の拡張で完成します。

### Breaking Changes
- なし

### Security
- なし

---

開発者向け: 次の予定は research モジュールの完了、ExecutionEngine 周りの Broker 実装（Mock と本番）の整備、テストカバレッジ追加、config/*.yaml の具体的な仕様記述と検証強化です。