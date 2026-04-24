# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記述しています。  
リリース / 変更内容はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能群を追加。
  - パッケージ構成
    - 実行関連: run_execution.py（ExecutionEngine 起動スクリプト）
    - 監視関連: run_monitoring.py（SystemMonitor ポーリングループ起動スクリプト）
    - 設定管理: config.py（環境変数/.env 読み込みと Settings クラス）
    - 設定ウィザード: config_setup.py（対話式 .env 作成/更新ツール）
    - 設定検証: validate_config.py（起動前に環境・設定ファイルをチェックする CLI）
    - ツール: tools/paper_verification_report.py（Paper Trading の検証レポート生成）
    - ポートフォリオ構築: portfolio/*（候補選定、重み計算、リスク制約、ポジションサイズ計算）
    - 研究用: research/factor_research.py（ファクター計算の骨格）
    - ユーティリティ:
      - utils/logging_setup.py（統一的なログ設定、日次ローテーション）
      - utils/process_priority.py（クロスプラットフォームのプロセス優先度 / CPU affinity 設定）
- Settings / 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。
  - OS 環境変数を保護して .env.local で上書き可能。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
- Settings により多数の設定プロパティを提供
  - J-Quants / kabu API トークン取得、データベースパス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH）、PID / Kill Flag パス、閾値（CPU/MEM/DISK）、KABUSYS_ENV/LOG_LEVEL 判定など。
  - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）。
- 実行エンジン（run_execution）
  - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成（paper/live を切替可能）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててバックグラウンドスレッドで実行。
  - 停止フラグファイル（data/stop_requested.flag）と PID 管理（data/execution.pid）を使用した安全停止処理。
  - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。
- 監視プロセス（run_monitoring）
  - SystemMonitor を定期ポーリングして system_status 等を記録。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下・非整数）はログ警告の上デフォルトにフォールバック。
  - 監視は環境にかかわらず本番用 sqlite_path を参照する（明示的な設計決定）。
  - 停止フラグ検知・例外ハンドリング・キーボード割り込みへの対応を実装。
- ログ設定ユーティリティ
  - setup_logging(): stdout（StreamHandler）と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。
  - ログレベル解決順とログディレクトリ解決順を文書化（引数 > 環境変数 > デフォルト）。
  - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールログのみ継続。
- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority(level: "high"|"normal"|"low")：Windows と POSIX（Linux/Mac/FreeBSD）を抽象化して nice / priority を設定。失敗時は警告ログでスキップ。
  - set_cpu_affinity(cpu_count)：最初の N コアに固定。権限不足や未対応環境は警告でスキップ。
- ポートフォリオ構築ロジック
  - select_candidates, calc_equal_weights, calc_score_weights：候補選定と重み付けロジック（スコアゼロ時のフォールバック警告あり）。
  - apply_sector_cap：セクター集中上限チェックと候補フィルタリング（"unknown" セクターは除外の対象外）。
  - calc_regime_multiplier：market regime に応じた投下資金乗数（bull/neutral/bear、未知レジームはフォールバック）。
  - calc_position_sizes：risk_based / equal / score の配分方式、lot_size（単元株）丸め、aggregate cap によるスケーリングロジック、cost_buffer（スリッページ/手数料見積り）を考慮した調整を実装。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py: paper_trading DB を読み、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定（閾値付き）を出力。
  - P95 計算、日付フィルタ、DB 存在チェック、エラーハンドリングを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- MONITOR_POLL_INTERVAL の不正値（非整数や 0/負値）に対して safety fallback を実装し、time.sleep に渡しての ValueError 回避と警告ログ出力を行うようにした。
- .env 読み込み時にファイル読み込み失敗が発生した場合、警告を出して処理を続行するようにした（テスト・CI での堅牢化）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数に関する注意喚起をドキュメント（config_setup のヘッダ）に追加: .env を決して Git にコミットしないことを明示。

---

注意:
- 上記はソースコードから推測してまとめた CHANGELOG です。実際のリリース日付やバージョン、細かい実装仕様はリポジトリ管理者のリリースノートに従ってください。