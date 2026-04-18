# Changelog

すべての重要な変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

最新のリリースは下記の通りです。

## [0.1.0] - 2026-04-18

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御はプロジェクトルートの data/stop_requested.flag により行う。停止時は Engine.stop() を呼んで安全に終了。
    - 起動時に pid ファイル（data/execution.pid）を書き、監視用テーブルの初期化を行う。
    - BrokerClientFactory を利用してブローカクライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。

- 監視用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを実行する起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して初期化（監視テーブルの存在を保証）。
    - 停止フラグ (data/stop_requested.flag) の検知でループを抜けて終了。
    - 起動時にプロセス優先度を "high" に設定。

- 環境設定・検証 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを追加。
    - J-Quants / kabu API 等の必須項目、DB パス、LOG_LEVEL、Kill Switch の初期設定をサポート。
    - シークレット値はマスク表示、既存 .env の読み込み・再利用に対応。
  - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パーサ（PyYAML）有無による挙動、KABUSYS_ENV=live 時の追加警告等を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- 設定管理改善
  - config.py: 自動 .env ロード機能を実装（プロジェクトルートの検出により .env / .env.local を読み込み）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用）。
    - .env のパースは `export KEY=val` 形式、クォートあり/なし、エスケープ・インラインコメントへの対応を実装。
    - Settings クラスを導入し、環境変数へのアクセスをプロパティで統一（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の妥当性チェック（"instant"|"partial"|"never"|"reject"）を実装。
    - 環境値（KABUSYS_ENV, LOG_LEVEL）の妥当性検証を追加。

- ロギング・プロセスユーティリティを追加
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテート、30日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで外部スケジューラ実行時の stdout/stderr 一元化に対応。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度設定を行うユーティリティを追加（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリを追加（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中の上限チェック（既存ポジションのセクター別時価算出、上限超過セクターの候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返すユーティリティ（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
      - risk_based: リスク許容率・損切り率に基づく株数算出。
      - equal/score: ウェイトに基づく金額割当て→単元株 (lot_size) に丸め。
      - aggregate cap により利用可能現金を超える場合はスケールダウンし、残余キャッシュで端数を lot_size 単位で再配分するアルゴリズムを実装。
      - コストバッファ (cost_buffer) を利用して手数料・スリッページを保守的に見積もる。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db）から統計を集計して検証レポートを出力。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - P95 実装、閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency <= 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ (--from / --to) に対応。

- パッケージ初期バージョン設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- 監視テーブル初期化の呼び出しを起動処理に追加
  - run_execution と run_monitoring の両方で init_monitoring_db(sqlite_conn) を呼び、監視用テーブルが存在することを保証（冪等）。

- ログ出力挙動の統一
  - 全起動スクリプトは setup_logging を呼び出してログ設定を統一（ファイル出力とコンソール出力の挙動を整備）。

### Fixed
- .env パーサの堅牢性向上
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの正しい扱いなどを実装して .env の多様な書式に対処。

- MONITOR_POLL_INTERVAL の不正値処理
  - 0 以下や数値以外の値が設定された場合に警告を出してデフォルト（60秒）を使用するよう修正。time.sleep に渡して ValueError が発生しないように保護。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

-----

注記:
- 本リリースは初期機能群の導入を目的としており、戦略本体（シグナル生成等）や実取引ブローカーの詳細実装は別モジュールで提供される想定です。
- run_monitoring は実行環境にかかわらず監視用 DB パス（Settings.sqlite_path）を使用します。これにより監視データは環境に依存せず一元管理されます（paper_trading を本番 DB と完全分離したい用途では設計上の注意が必要です）。
- research/factor_research.py 等、分析・研究系モジュールは DuckDB を利用した計算基盤のスケルトンを含みます。今後、関数群の完成・最適化を予定しています。