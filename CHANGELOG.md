Keep a Changelog
=================

すべての注目すべき変更を記録します。  
このファイルは "Keep a Changelog" の慣習に準拠します。  

フォーマット:
- 変更はセクション（Added, Changed, Fixed, …）ごとに分類しています。
- 日付はリリース日を表します。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基礎機能を実装。
  - パッケージバージョンを __version__ = "0.1.0" として設定。
- 実行・監視エントリポイントを追加。
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時に MockBrokerClient を利用し、paper_trading 用の SQLite DB（デフォルト: data/paper_trading.db）を使用する実行フローを実装。停止フラグ（data/stop_requested.flag）と pid ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検出、監視用 DB 初期化処理を実装。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理と初期化ツールを追加。
  - config.py: .env 自動読み込み（.env と .env.local、OS 環境変数保護）、.env フォーマットの堅牢なパーサ、Settings クラス（各種環境変数への型付きアクセサ）を実装。
  - config_setup.py: 対話式 .env ウィザード（.env の作成・更新を支援）。シークレット項目のマスク表示や既存値の再利用をサポート。
  - validate_config.py: 起動前チェック CLI。必須環境変数、パス、config/*.yaml の存在や YAML パース（PyYAML があれば実行）などを検証。--strict モードをサポート。
- ポートフォリオ構築関連（純粋関数群）を追加。
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み算出（スコア全0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック。既存保有を考慮して新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数決定ロジック。risk_based / equal / score 方式に対応。単元（lot_size）丸め、aggregate cap（利用可能現金を超える場合のスケーリング）や cost_buffer による保守的見積りを実装。
  - portfolio/__init__.py: 主要 API をエクスポート。
- 解析・調査ユーティリティを追加。
  - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を設計に基づき追加（DuckDB 経由で prices_daily / raw_financials を参照する想定）。（注: ファイル途中まで実装）
- 運用ユーティリティを追加。
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバック。
    - ログレベル/ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - プロセス優先度設定（set_process_priority）を実装。Windows (psutil の定数) と POSIX (nice 値) を吸収し、対応外 OS はスキップ。CPU affinity 設定（set_cpu_affinity）を実装。
- モニタリング DB 初期化共通処理を監視モジュールに実装（init_monitoring_db を各起動処理で呼び出し、監視テーブル存在を保証）。
- 実用ツールを追加。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツール。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し PASS/FAIL を判定する CLI。しきい値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）を定義。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- .env 読み込みの堅牢化:
  - export KEY=val 形式、クォート付き値、インラインコメント処理、OS 環境の保護（protected）をサポート。
- ログ設定の堅牢化:
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソール出力を継続するように変更。
- プロセス優先度設定の障害耐性:
  - 権限不足や未対応プラットフォームでの例外を捕捉し、警告ログを出して処理を継続するように改善。
- Execution / Monitoring の DB 接続ロジック:
  - Monitoring は常に（環境にかかわらず）production の sqlite_path を使用する仕様を明記。Execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離。

Notes / Known limitations
- research/factor_research.py はファイル末尾で未完（関数実装途中の形跡あり）。まだ完全実装されていないため、ファクター計算の一部は未提供です。
- position_sizing.calc_position_sizes 内で価格欠損（price が 0.0）の場合のフォールバック（前日終値や取得原価など）は未実装（TODO コメントあり）。価格データの欠損があるとエクスポージャーが過少見積りされる可能性があります。
- apply_sector_cap は "unknown" セクターを上限適用除外としているため、マスタにセクター情報が欠けると実効的なセクター制約が緩くなる点に注意。
- 一部の機能（例: Engine の詳細な実装、BrokerClientFactory の実装、monitoring.system_monitor の実装など）はこの差分からは参照のみで具体的実装は該当モジュールを参照してください。

開発者向け補足
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われるため、配布後は CWD に依存せず正しく動作する想定です。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログは stdout に出力されるため、cron やコンテナ運用時に stdout/stderr を適切にリダイレクトしてください。
- Paper Trading と Live は DB を分離する設計になっているため、検証時に本番 DB を誤操作しないようデフォルト設定を確認してください。

References
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0" に準拠。