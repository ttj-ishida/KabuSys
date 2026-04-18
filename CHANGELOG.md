# Changelog

すべての変更は「Keep a Changelog」形式に従い、日本語で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

最新リリース
=============

Unreleased
----------

（現在のスナップショットに基づく変更点は次回リリースに含まれます）

0.1.0 - 2026-04-18
-----------------

Added
- 基本バージョン 0.1.0 を公開。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用して paper_trading 用 DB に記録する（本番 DB と完全分離）。停止フラグ（data/stop_requested.flag）・実行 PID 管理（data/execution.pid）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を使用する旨を明記。
  - kabusys.config_setup: 対話式 .env 作成/更新ウィザードを追加（Python モジュール経由で実行可能）。機密値はマスク表示。生成テンプレートを .env に書き出す。
  - kabusys.validate_config: 起動前設定検証 CLI を追加。必須環境変数や設定ファイル（config/*.yaml）の存在や基本的な妥当性をチェック。`--strict` オプションで警告を FAIL 扱いにできる。
  - kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を算出・判定する。コマンドライン引数で期間指定や DB パス指定が可能。
- 設定 / 環境周り
  - kabusys.config.Settings クラスを追加。環境変数から設定を一元管理。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須取得）
    - KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH 等
    - PAPER_FILL_MODE（paper_trading 時の挙動。"instant", "partial", "never", "reject" をサポート、検証あり）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite パス）
    - 各種監視閾値（CPU/MEM/DISK 等）、PID/kill flag パス等
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。読み込み順: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。既存の OS 環境を保護する仕組みあり。
  - .env パーサを堅牢化:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォートなしは '#' の前が空白/タブの場合にコメントと判断）
    - 上書き制御（override / protected）
- ログ・プロセス管理ユーティリティ
  - kabusys.utils.logging_setup.setup_logging を追加。ルートロガーに以下を設定:
    - StreamHandler を stdout に出力（cron/task でのリダイレクトを想定）
    - TimedRotatingFileHandler による日次ローテーション（30 日保持）でファイル出力を行う。ログディレクトリは引数/環境変数で指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）に対応する優先度設定を抽象化。権限不足や未対応 OS は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン止めするユーティリティ（権限不足や未対応環境は警告でスキップ）。
- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコアで上位 N を選択（スコア降順、同点時は signal_rank をタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告を出す。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき候補を除外するロジック。既存保有のエクスポージャ計算、"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいて発注株数を計算。リスクベースの計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer（スリッページ/手数料の保守的見積）に基づくスケーリングを実装。余り分は fractional 残差に基づいて安定的に配分。
  - portfolio パッケージ __init__ で主要関数をエクスポート。
- 研究 / ファクター計算基盤
  - kabusys.research.factor_research: DuckDB 接続を受け取り、prices_daily/raw_financials を使ったモメンタム / Value / Volatility / Liquidity 等のファクター計算基盤設計。実装は（スナップショットの都合で）途中まで含むが、設計と定数、calc_momentum の骨組みを追加。
- モニタリング / 監視 DB
  - monitoring_db.init_monitoring_db が各起動スクリプトで呼ばれ、監視テーブルの存在を冪等的に保証する実装を採用。
- Paper Trading 検証ツール
  - paper_verification_report は稼働率（uptime）、注文関連統計（Created/Filled/Sent）、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に対する PASS/FAIL 判定を出力する。SQLite DB パス解決ロジック（--db > env > デフォルト）を実装。

Changed
- 監視（run_monitoring）に関する挙動説明を明確化:
  - Monitoring は KABUSYS_ENV にかかわらず設定されている sqlite_path（本番用）を使用する仕様となっていることを明示。運用時は注意（paper_trading と本番 DB の混在を防ぐために実際の運用では監視 DB の分離を検討してください）。
- ロギングのデフォルト出力先は stdout（StreamHandler）優先とし、cron 等からの起動時に stdout/stderr の一貫した扱いをしやすくした。

Fixed
- .env 読み込みにおける基本的なパーシングの改善（引用符、エスケープ、export 構文、インラインコメントの取り扱い）により、設定読み込みの頑健性を向上。

Security
- 現時点で特別なセキュリティ修正はありませんが、.env 生成ウィザードでは機密値をマスク表示し、README 相当の注意文（.env を絶対に Git にコミットしない等）を .env テンプレートに記載。

Migration notes / 注意点
- Monitoring はデフォルトで Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。paper_trading 用に監視データを完全に分離したい場合は運用側で別パスを設定してください。
- PAPER_FILL_MODE は無効な値を渡すと ValueError を送出します。利用時は "instant", "partial", "never", "reject" のいずれかを指定してください。
- process_priority の設定は権限や OS により失敗する場合があります（その場合は警告ログを出してスキップします）。
- logging_setup によりログが stdout に出力されるため、既存の監視ツールやログ収集の設定を確認してください。ログファイル出力が不要な環境では LOG_DIR を調整するか、ファイルハンドラ作成に失敗した際の挙動（コンソールのみ）を利用できます。

参考: 実行例
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 実行スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

今後の予定（例）
- factor_research の完全実装（Value, Volatility, Liquidity の計算関数）
- 銘柄別 lot_size のサポート（stocks マスタとの連携）
- 監視/検証向けの自動アラート（LINE 通知連携）の強化

----- 

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース履歴や日付はプロジェクト運用に合わせて調整してください。