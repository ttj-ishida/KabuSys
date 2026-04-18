# Changelog

すべての重要な変更をこのファイルに記録します。  
この変更履歴は「Keep a Changelog」形式に準拠します。  

なお、本ファイルはソースコードから挙動を推測して作成しています（実装コメント・定数等に基づく）。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。以下の機能・ユーティリティを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定。
    - 環境に応じて本番用 DB / ペーパートレード用 DB を切り替え（KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行を行う。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動制御・終了処理を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（monitoring 用テーブルの冪等初期化）と DuckDB 接続を確立。
    - 停止フラグ検知でループを終了、例外発生時はログ出力して次ポーリングまで待機。

- 設定管理
  - config.py: .env 自動読み込み実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - `.env` / `.env.local` の読み込み順、OS 環境変数保護（protected）に対応。
    - 行のパースで export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントなどをサポート。
    - Settings クラスを提供（各種環境変数をプロパティで取り出し、検証を実施）。
    - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, 各種閾値（CPU/MEM/DISK）、KABUSYS_ENV, LOG_LEVEL など。
    - PAPER_FILL_MODE の有効値チェック（"instant"|"partial"|"never"|"reject"）とエラー報告。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（想定値以外は ValueError）。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env ウィザードを追加。
    - 対話形式で主要な環境変数を入力し .env を生成・更新。
    - シークレット項目はマスク表示、既存値の再利用に対応。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検査（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live の場合の追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性等）。
    - --strict モードで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログディレクトリ + 日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX 差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - psutil が投げる AccessDenied 等を安全にハンドリングし、失敗時は警告ログでスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレーク（signal_rank）で選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比例配分。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有比率がセクター上限を超える場合、新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じて発注株数を算出。
      - lot_size（単元株）で丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積）を考慮。
      - aggregate cap 超過時はスケーリングし、残差は fractional 残差の大きい順に lot 単位で再配分。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を読みレポートを生成。
    - システム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算して PASS/FAIL 判定（閾値はソース内定数で定義）。
    - CLI オプション `--from` / `--to` / `--db` を提供。
    - DB スキーマが存在しない場合（OperationalError）は該当指標を N/A 扱いで耐障害性を確保。

- 研究用モジュール（始動）
  - research/factor_research.py を追加（モメンタム・バリュー・ボラティリティ・流動性等のファクター計算を予定）。
    - DuckDB 接続を用いた prices_daily / raw_financials 参照設計。現時点でモジュールが計算ロジックを含む（途中実装があることを示唆）。

### Changed
- なし（初版のため）。

### Fixed
- なし（初版のため）。

### Security
- なし（該当事項なし）。

---

注記:
- 実装はファイルシステム上のフラグファイル（data/stop_requested.flag, data/execution.pid, data/kill.flag など）に依存する箇所があります。運用時は適切な権限とパス設定を行ってください。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます（テスト用途を想定）。
- ペーパートレードと本番 DB は分離される設計です（PAPER_TRADING_SQLITE_PATH）。ペーパートレード環境では MockBrokerClient を使用する想定がソースコメントにあります。

（以上）