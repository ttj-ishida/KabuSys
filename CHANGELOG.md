CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
- 環境設定・読み込み
  - .env / .env.local を自動読み込み（プロジェクトルートが検出できる場合）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース処理を実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ対応、インラインコメント処理など）。
  - Settings クラスを実装し、環境変数から各種設定（J-Quants トークン、kabu API、DB パス、ログレベル、実行環境フラグ等）を取得・検証。
  - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
  - 環境タイプ（development/paper_trading/live）とログレベルの検証。

- 設定支援・検証ツール
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数の未設定検出、KABUSYS_ENV の guard、YAML のパースチェック（PyYAML が無い場合は警告）等を実施。--strict オプションで警告をエラー扱いにできる。

- 実行系（Execution）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼ぶ）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを注入し、OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立て、ExecutionEngine をデーモンスレッドで起動。
    - data/stop_requested.flag による外部停止フラグ検知と安全停止処理を実装。PID ファイル管理（data/execution.pid）をサポート。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit 等）をデフォルトで設定。

- 監視系（Monitoring）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値や 0 以下はデフォルトへフォールバックして警告を出力。
    - 監視用 DB 初期化（init_monitoring_db）を実行。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動（設定注釈あり）。
    - data/stop_requested.flag による停止フラグ検知、KeyboardInterrupt のハンドリング、例外発生時のログ出力と継続を行う。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: setup_logging を実装。root ロガーを統一的に設定（stdout への StreamHandler、日次ローテートのファイルハンドラ）。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: set_process_priority と set_cpu_affinity を実装。Windows/Linux(Mac 等) の差分を吸収し、安全に失敗（権限不足や未対応 OS）した場合は警告を出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でタイブレークして候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、超過セクターの候補を除外（"unknown" セクターは対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知レジームは警告と共に 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数算出を実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、1 銘柄上限・集計キャップ、cost_buffer に基づく保守的見積り、可用現金に合わせたスケーリング／端数配分ロジックを実装。
    - 複数の安全弁（価格未取得時のスキップ、0 以下価格処理、max_per_stock の考慮）を含む。

- 研究・解析ユーティリティ（部分実装）
  - research/factor_research.py: DuckDB を使ったファクター計算基盤を追加（モメンタム・MA200・ATR・出来高指標等の計算方針実装）。calc_momentum 等の関数を提供（部分的に実装中、データ不足時の挙動定義あり）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し PASS/FAIL を判定する。閾値はスクリプト内で定義（例: 稼働率 >= 99% 等）。日付フィルタと DB パス上書きオプションをサポート。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- 各所での防御的実装:
  - MONITOR_POLL_INTERVAL が不正な場合は警告してデフォルトにフォールバック。
  - .env パーサの堅牢化（空白・コメント・クォート・エスケープ処理）。
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力を継続。
  - process_priority の未対応 OS やアクセス権限不足をハンドリングして失敗を許容。

Known issues / Notes
- research/factor_research.py は一部未完（calc_momentum の実装途中）。将来的な追加実装が予定されている。
- position_sizing.calc_position_sizes の価格欠損時（price == 0.0）の扱いに関する TODO 注記あり（フォールバック価格の導入など）。
- run_monitoring は「常に本番 sqlite_path を使う」との設計注記があるため、環境分離が必要な場合は運用ポリシーに注意。
- config/*.yaml の内容検証には PyYAML が必要。未インストール時は内容検証をスキップして警告のみ出す。

Authors
- KabuSys 開発チーム

README 等の利用手順や API 仕様は別ドキュメント（/docs など）を参照してください。