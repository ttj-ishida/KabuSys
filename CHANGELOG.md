# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。

## [0.1.0] - 2026-04-23

初回公開リリース。自動売買システム KabuSys の基本コンポーネント（設定管理、起動スクリプト、ポートフォリオ構築、ユーティリティ、検証・レポートツールなど）を実装。

### Added
- 環境設定
  - .env 自動読み込み機能を追加（プロジェクトルートの `.env` と `.env.local` を順に読み込む）。OS 環境変数は上書きされないよう保護。
  - Settings クラスを導入し、環境変数経由で各種設定にアクセス可能に。
  - 新しい設定項目:
    - PAPER_FILL_MODE（paper trading の MockBroker 挙動制御、"instant" / "partial" / "never" / "reject" を検証）
    - PAPER_TRADING_SQLITE_PATH（paper trading 用 SQLite のパス）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・制御用）
    - 各種閾値: CPU/MEM/DISK の閾値設定
    - KABUSYS_ENV（development / paper_trading / live）とログレベル検証

- CLI ツール
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI（python -m kabusys.config_setup）。
    - シークレット項目のマスク表示、既存 .env の読み込み、保存前確認をサポート。
    - .env を絶対にリポジトリにコミットしない旨を明示。
  - validate_config: 起動前チェック CLI（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml 存在・パース検証（PyYAML がある場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - tools.paper_verification_report: ペーパートレード検証レポート生成 CLI（期間指定 --from / --to、--db オプション対応）。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下件数等。
    - 基準値 (Pass/Fail) を定義（例: 稼働率 >= 99%、P95 <= 200ms など）。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。実行 PID の管理（data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - 起動前に監視用テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番データの監視を想定）。
    - 停止フラグ検知でループ終了。check_once の例外はログに記録してループ継続。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全て 0 の場合はフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのエクスポージャ計算、sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数（未知レジームは警告と 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に従って発注株数を計算。
    - lot_size（単元）考慮、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を反映した aggregate cap によるスケーリング、余剰キャッシュ配分ロジックを実装。

- ユーティリティ
  - utils.logging_setup:
    - 統一ログ設定ユーティリティを導入。stdout ストリームハンドラと日次ローテーションのファイルハンドラ（logs/<app>.log、30 日バックアップ）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。ログレベル / ログディレクトリ解決ルールを実装。
  - utils.process_priority:
    - set_process_priority: Windows / POSIX (Linux/Mac/FreeBSD) に対応したプロセス優先度設定（psutil を使用）。権限不足や未対応 OS は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めするユーティリティ（安全にフォールバック）。

- データリサーチ
  - research.factor_research: ファクター計算モジュールの骨組みを追加（モメンタム / MA / ATR / 流動性等を計算する方針、DuckDB を使用）。（実装は継続中）

### Changed
- ロギング
  - ログ出力は標準出力（stdout）とファイル出力両方に統一。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - ログレベル決定順を明確化（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
- 起動時のプロセス優先度
  - run_execution/run_monitoring で起動直後に set_process_priority("high") を呼び出すよう変更。
- DB ハンドリング
  - run_execution で paper_trading モード時に paper 専用 SQLite を使用するよう明確化。監視テーブルの存在保証（init_monitoring_db）を追加。
- 停止フラグ処理
  - run_execution/run_monitoring でプロセス停止フラグ（data/stop_requested.flag）を監視し、安全にシャットダウンするように実装。

### Fixed
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring の _get_poll_interval が環境変数の不正な数値（負数や非整数）を検出して警告を出し、time.sleep で ValueError が発生しないようデフォルトにフォールバックするように修正。
- 例外耐性
  - run_monitoring のポーリング中に monitor.check_once() が例外を投げてもループを継続するよう例外捕捉とログ記録を追加。
- ログハンドラ二重登録防止
  - setup_logging が既存のハンドラをクリアしてから設定するように変更し、複数回呼び出した際の多重出力を防止。

### Security
- config_setup にて .env を Git にコミットしない旨をドキュメント化し、シークレット項目はマスク表示。

### Notes / TODO
- research.factor_research の実装は継続中（calc_momentum などの詳細実装が未完）。
- position_sizing の将来的拡張: 銘柄毎の lot_size を stocks マスタで持たせる設計への対応予定。
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価の利用）について検討予定。

---

今後のリリースでは、strategy 実装、ExecutionEngine のテスト強化、factor_research の完成、および既存モジュールのユニットテスト追加を予定しています。