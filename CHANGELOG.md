CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日はソースから推測可能な最新日付を記載しています。

[Unreleased]
-------------

- （現在未リリースの変更はありません。）

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本機能を実装
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient による分離された動作をサポート。
      - 起動時にプロセス優先度を "high" に設定。
      - stop フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応し、外部からの停止要求により安全に終了可能。
      - ExecutionEngine の組み立て: BrokerFactory、OrderRepository、OrderManager、RiskManager（デフォルト構成値含む）、Reconciler などのコンポーネントを初期化。
    - run_monitoring.py: SystemMonitor をポーリングして監視データを収集する監視プロセスの起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告後デフォルトへフォールバック。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視 DB は本番パスを参照）。
      - stop フラグ検出と KeyboardInterrupt によるグレースフル終了を実装。
  - 設定管理
    - config.py: Settings クラスを実装し、環境変数から設定を抽出。
      - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を検出）を基に .env/.env.local を読み込み。OS 環境変数を保護する仕組みあり（上書き制御）。
      - .env パーサは export 形式、クォート（シングル/ダブル）やエスケープ、行内コメントなどに堅牢に対応。
      - 各種設定プロパティを提供（DB パス、Paper Trading 用パス、PID/kill flag 関連、しきい値、ログレベル、環境判定ユーティリティ等）。
    - config_setup.py: 対話式ウィザードで .env ファイルを生成・更新する CLI を追加。
      - 既存 .env の読み込み・マスク表示・選択肢提示・保存までの対話を実装。
    - validate_config.py: 起動前の環境検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの追加ガード等を実装。
      - --strict オプションで警告を失敗扱いにできる。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
      - ログディレクトリ自動作成、既存ハンドラのクリア、ログレベル解決ルールを実装。
      - ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続。
    - utils/process_priority.py: psutil を利用したプロセス優先度設定・CPU affinity 設定ユーティリティを追加。
      - Windows と POSIX(Linux/macOS/FreeBSD) を吸収する実装。
      - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(...) を提供。権限不足や非対応環境では警告を出してスキップ。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py:
      - select_candidates: スコア順ソート＋上位 N 選定。
      - calc_equal_weights / calc_score_weights: 等配分・スコア正規化配分。全てのスコアが 0 の場合は等配分にフォールバック。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中制限（既存保有含めたエクスポージャー計算に基づく候補フィルタリング）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバックで 1.0。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく発注株数計算、単元株丸め、per-position および aggregate の上限、cost_buffer（手数料/スリッページを保守的に見積もる）を考慮したスケーリングロジックを実装。
      - lot_size 単位での切り捨て／残余再配分ロジックを実装。
  - 研究／計算モジュール
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性等を想定）。calc_momentum 等のインターフェースと計算方針を実装（コードは一部省略あり）。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード用 SQLite から検証レポートを生成する CLI を追加。
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等の集計と閾値判定（PASS/FAIL）を行う。
      - 日付レンジ指定（--from/--to）と DB パスの指定（--db または 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
  - パッケージ情報
    - __init__.py: パッケージバージョンを 0.1.0 に設定。

Changed
- N/A（初期リリースのため既存からの変更は無し）

Fixed
- N/A（初期リリースのため修正履歴は無し）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の注記
- 監視（monitoring）は意図的に本番用 sqlite_path を使用する設計（環境に左右されない監視データ収集）。
- config の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用）。
- PyYAML 未インストール時は config/*.yaml の内容検証はスキップして警告を出す。
- position_sizing、apply_sector_cap など一部ロジックは入力データ欠損（price が 0 や未定義）の場合に注意が必要（TODO コメントで将来の改善案を提示）。
- Paper Trading と本番 DB は明確に分離される設計（PAPER_TRADING_SQLITE_PATH を利用）。

参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照しています。