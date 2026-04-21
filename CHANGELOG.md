# CHANGELOG

すべての著名な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

- プロジェクト初版: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 実行系 / 監視系起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - BrokerClientFactory を利用したブローカークライアント生成を行い、OrderRepository・OrderManager・RiskManager・Reconciler 等の組み立てを実施。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用 SQLite（`data/paper_trading.db`、または `PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全に分離。
    - エンジンは別スレッドで実行され、プロジェクトルート下の `data/stop_requested.flag` による安全な停止制御と `data/execution.pid` による PID 管理をサポート。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出力。
    - 監視 DB（SQLite）は環境にかかわらず本番 `sqlite_path` を使用する挙動。
    - 停止フラグファイル検知、例外捕捉によるループ継続、安全な DB 接続クローズ処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - src/kabusys/config.py
    - Settings クラスを導入し、環境変数から設定値を一元取得する API を提供（J-Quants、kabuAPI、LINE、DB パス、監視閾値、ログ等）。
    - プロジェクトルート自動検出ロジックを追加（.git / pyproject.toml を探索）。
    - `.env` / `.env.local` の自動ロード機能を実装（OS 環境変数を保護、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - `.env` パースにおいてシングル/ダブルクォートやエスケープ、`export KEY=...` 形式、インラインコメントを考慮した堅牢な実装。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode` 等の専用設定を追加。
    - 環境種別検証（development/paper_trading/live）やログレベル検証を内蔵。

  - config_setup.py
    - 対話式ウィザードにより `.env` を初期作成・更新する CLI を実装。
    - シークレット項目はマスク表示、既存 `.env` の読み込み・再利用に対応。
    - 生成テンプレート（コメント付き）で `.env` を出力。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル検証、DB パスの親ディレクトリチェック、YAML ファイルの存在・パース検証（PyYAML が利用可能な場合）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - live 環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性通知）を実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算、期間フィルタ（--from/--to）、DB パス解決（--db または PAPER_TRADING_SQLITE_PATH）をサポート。
    - 合格基準（デフォルト閾値）を設定:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 重み計算: 等分配（calc_equal_weights）、スコア加重（calc_score_weights）。全スコアが 0 の場合は等分配へフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対して 1.0/0.7/0.3 を返し、未知レジームは警告の上 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）:
      - allocation_method: "risk_based"（リスクベース） / "equal" / "score" をサポート。
      - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮。
      - aggregate cap 超過時のスケーリング処理と残差（fractional remainder）に基づく補正ロジックを実装。
      - 価格欠損時のスキップやログ出力、0価格対策に留意。

- 研究 / ファクター計算（基盤）
  - research/factor_research.py（開発中）
    - DuckDB を用いて prices_daily / raw_financials を参照し、Momentum/Value/Volatility/Liquidity 等のファクターを計算する設計を追加（モジュール骨子と定数群を含む）。（処理の続きを実装予定）

- ログ・OSユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング初期化ユーティリティを提供。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーへ設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリ自動作成、作成失敗時のフォールバック（コンソールのみ）を実装。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト。

  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice 値）を実装。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を実装。許可エラー等は警告を出して無視。
    - 無効値・未対応 OS への安全なフォールバックと詳細な警告を提供。

### Changed
- なし（初版）

### Fixed
- なし（初版）

### Security
- なし（初版）
  - ただし `.env` を Git にコミットしないよう、config_setup に注記を追加。

### Notes / Implementation details
- 監視（monitoring）コンポーネントは、監視 DB の初期化（init_monitoring_db）や DuckDB 接続を行い、例外時にもループ継続する堅牢性を重視している。
- run_execution は起動直後に停止フラグが既に立っている場合は起動を抑止する安全機構を持つ。
- `.env` の自動ロードは OS 環境変数を上書きしないことをデフォルト方針としているが、`.env.local` は上書き（override=True）される仕組み。
- 多くの関数は DB に依存しない純粋関数として設計されており、ユニットテストが容易な構成を目指している。

---

過去のバージョンはありません（初回リリース）。今後の変更はこのファイルに追記します。