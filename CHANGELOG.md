CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
このログは "Keep a Changelog" の形式に準拠しています。

[Unreleased]
------------

なし

0.1.0 - 2026-04-18
------------------

初回リリース (初版)。 以下の機能群・ユーティリティ・CLI を含みます。

Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定・読み込み
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - .env ファイルの堅牢なパース（export 形式、クォート対応、インラインコメント処理等）。
    - Settings クラスにより環境変数をプロパティとして提供（J-Quants/Kabu/DB/監視/ログ等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 SQLite パス (PAPER_TRADING_SQLITE_PATH)、PID/kill flag 関連設定や閾値設定 (CPU/MEM/DISK) を提供。

- 設定支援 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成/更新するツールを追加。
    - J-Quants / kabu API / DB パス / LINE 通知 / ログレベル / Kill Switch の設定項目を含む。
    - 既存 .env の読み込み・マスク表示・確認プロンプトを実装。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前検証ツールを提供（必須環境変数チェック、KABUSYS_ENV 検証、ログレベル検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証 (PyYAML があればパースを実行)）。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番 (live) 向けの追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。

- 実行・監視スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory を用いたブローカークライアント生成（Mock/実環境切替）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立てて実行。Engine は別スレッドで実行、停止フラグ (data/stop_requested.flag) を検知して安全に停止。
    - PID ファイル生成用の設定と停止フラグ検知ロジックを実装。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値は警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を想定）。
    - 停止フラグ file によるループ終了検知と KeyboardInterrupt ハンドリング。
    - 起動時にプロセス優先度を "high" に設定。

- モニタリング DB 初期化
  - init_monitoring_db(sqlite_conn) 呼び出しを実行スクリプト側で行い、監視用テーブルの存在を保障（冪等）。

- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - すべての起動スクリプトで共通に使えるログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler (logs/<app_name>.log、30日保持) を設定。
    - 既存ハンドラのクリーンアップ、ログレベル解決順、ログディレクトリの自動作成試行、ディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収したプロセス優先度設定。
    - CPU affinity 設定ユーティリティを追加 (cpu_count を受け取り最初の N コアに固定)。
    - アクセス権限不足や未対応環境での安全なフォールバックとログ出力。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。スコアが全て 0 の場合は等配分にフォールバックして警告。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)。現在保有のセクター比率が上限を超える場合、新規候補を除外。unknown セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームはフォールバックで 1.0。

  - src/kabusys/portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を実装。
    - allocation_method 支持: "risk_based", "equal", "score"。
    - 単元株丸め (lot_size)、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。
    - スケールダウン後の残余配分を残差ソートで行い、lot 単位で追加配分するロジックを実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をエクスポートして外部使用を容易に。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite データ (デフォルト: data/paper_trading.db) からレポートを生成する CLI。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数 等。
    - 判定基準（閾値）を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、成立率 >= 90% 等）。
    - 日付フィルタ (--from, --to)、--db オーバーライド対応。
    - SQL の実行時にテーブルが存在しない場合は安全に N/A/0 を扱う。

- 研究用ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して Momentum / Value / Volatility / Liquidity の計算を行う設計。
    - モメンタム計算 calc_momentum の骨格（horizon 定義や欠損ハンドリング方針）を含む（実装続きあり）。

- パッケージ初期化
  - src/kabusys/tools/__init__.py と utils/__init__.py、portfolio パッケージ周りの __all__ を整備。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数やシークレットは .env に保存することを明示（config_setup のヘッダーに注意喚起）。ログ等へシークレットが出力されないようマスク処理を考慮した表示を行う（config_setup の確認表示など）。

Notes / 備考
- 監視・実行系はファイルベースの停止フラグ (data/stop_requested.flag)、Kill Switch (data/kill.flag 相当) を用いる設計で、運用時はこれらファイルの配置・取り扱いに注意してください。
- ログはデフォルトで logs/ に出力されます。ログディレクトリ作成に失敗した場合はコンソール出力にフォールバックします。
- process priority / cpu affinity の設定は OS 権限や psutil の機能に依存します。設定失敗時は警告ログを出して処理を継続します。
- 本リリースは比較的多機能な骨格実装を含む初版です。各モジュール（特に research.calc_momentum の続き実装や ExecutionEngine 内部の詳細）は今後のリリースで拡充されます。

要望・バグ報告
- README や運用手順、単体テスト、CI、ドキュメント（API／設計書）の追加を推奨します。