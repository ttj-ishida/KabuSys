# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。  

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期リリース。基本的な自動売買システムのユーティリティ群と起動スクリプトを実装。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用の `sqlite_path` を使用して DB に接続。
    - 停止フラグファイル（data/stop_requested.flag）を検出して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 環境 `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動ロードを実装（CWD に依存しない）。
    - .env のパースはシングル/ダブルクォート、export プレフィックス、コメントのルールに対応。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。
    - 各種設定プロパティ（DB パス、PID/kill flag、阈値、env 判定、paper_trading 用設定など）を提供。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 主要な設定項目のプロンプト、既存 .env の読み込み・再利用、保存機能を提供。
- 設定検証ツール
  - validate_config.py: 起動前に .env や config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイル存在と（PyYAML があれば）パース検証、live 環境時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START）等を実装。
    - `--strict` オプションで警告をエラー扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 全スクリプトで共有できるロギング設定ユーティリティを実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを実装。
    - Windows / POSIX の差分を吸収して `set_process_priority(level)` を提供（high/normal/low）。
    - `set_cpu_affinity(cpu_count)` により最初の N コアに固定できる（実行環境で権限がない場合は警告でスキップ）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションのセクター別エクスポージャを計算し、上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py
    - position sizing の主要ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、利用可能現金に応じた aggregate cap スケーリング、cost_buffer を考慮した保守的計算を実装。
    - スケールダウン時に残差分を大きい順に lot 単位で再配分するアルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を集計して検証レポートを出力する CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - デフォルトパスは環境変数 `PAPER_TRADING_SQLITE_PATH`（data/paper_trading.db）。
    - 判定基準（閾値）を定義し、PASS/FAIL を表示。
- 研究用ファクター計算（骨格）
  - research/factor_research.py: DuckDB 接続を受け価格・財務データからファクター（Momentum/Value/Volatility/Liquidity）を計算する方針と一部実装を追加（モメンタム計算関数の枠組み、定数群を含む）。（実装途中）

### Changed
- なし（初期リリースのため新規追加が中心）

### Fixed
- なし（初期リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues / TODO
- research/factor_research.py は一部実装が途中で終了している箇所があり、完全実装は今後のリリースで行う予定です。
- position_sizing.calc_position_sizes と risk_adjustment.apply_sector_cap において、価格が欠損（0.0）の場合にエクスポージャや上限判定が過小評価される旨の TODO コメントがあり、将来的に前日終値や取得原価などのフォールバック価格導入を検討しています。
- logging_setup はログディレクトリ作成に失敗した場合に stderr へ警告を出しファイル出力を無効化します。運用環境ではログディレクトリの書き込み権限を確認してください。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性があり、失敗時は警告ログを出力して処理をスキップします。
- .env 自動ロードはプロジェクトルート検出に依存します。配布後に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

今後の予定: factor_research の完全実装、Strategy / Execution の詳細ロジック強化、ユニットテストと CI の整備。