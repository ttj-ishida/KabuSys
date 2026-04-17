# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠します。  
このファイルは、コードベースから推測される導入機能・設計上の決定・既知の制約を基に作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース（推定）。自動売買システム KabuSys のコア機能群を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定 / 設定読み込み
  - Settings クラスを実装し、環境変数から各種設定（J-Quants / kabuステーション / DB パス / ログレベル / 監視閾値 など）を取得可能に。
  - プロジェクトルート検出ロジックを実装（.git / pyproject.toml を起点）。
  - 自動 .env ロード機能を実装（優先順: OS 環境変数 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能を強化：export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。.env の作成・更新を容易にする。
  - 入力項目定義（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE など）を含む。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証機能を実装。
  - 必須環境変数チェック、KABUSYS_ENV 値チェック、パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、ライブ環境向けの追加ガード等を提供。
  - `--strict` オプションで警告を FAIL として扱う。

- 実行・監視エントリポイント
  - `run_execution.py`：ExecutionEngine を組み立て起動する CLI エントリポイントを追加（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て）。
    - paper_trading 環境では paper 専用 SQLite（`PAPER_TRADING_SQLITE_PATH`/`data/paper_trading.db`）を使用して本番 DB と分離。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、フラグがある場合は起動しない安全措置。
    - 実行中は同フラグをポーリングして安全に停止。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する（設計上の決定）。

- 監視 DB 初期化
  - `monitoring_db.init_monitoring_db` を呼び出して監視テーブルの存在を保障（冪等）。

- Paper Trading / Mock ブローカー対応
  - paper_trading 環境では MockBrokerClient を利用してペーパートレードを実行・記録。
  - paper_trading 用の検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を行う。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

- ポートフォリオ構築ライブラリ（純関数群）
  - `kabusys.portfolio` モジュールを追加（pure functions, DB 参照なし）。
  - portfolio_builder:
    - select_candidates（スコア降順、同点時は signal_rank で tiebreak）
    - calc_equal_weights
    - calc_score_weights（全スコア 0 の場合は等金額にフォールバックし WARNING）
  - risk_adjustment:
    - apply_sector_cap（既存保有を基にセクター集中度チェック、"unknown" セクターは除外対象としない）
    - calc_regime_multiplier（regime による投下資金乗数: bull=1.0, neutral=0.7, bear=0.3、未知は警告のうえ 1.0 でフォールバック）
  - position_sizing:
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score"、lot_size 単位で丸め、aggregate cap スケールダウンと余剰配分ロジック、cost_buffer を考慮）

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
  - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性等の計算関数を用意。
  - スキャン範囲・ウィンドウ長などは定数化（例: MA200=200, ATR=20 等）。

- プロセス優先度・CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` に set_process_priority/set_cpu_affinity を実装。
  - Windows（psutil の HIGH_PRIORITY_CLASS 等）および POSIX（Linux/Darwin/FreeBSD の nice 値）を吸収し、未対応 OS ではスキップする設計。
  - 権限不足や未対応 API 呼び出しは警告ログで安全にフォールバック。

- その他ユーティリティ
  - pkg exports を整備（portfolio モジュールの主要関数を top-level から import 可能に）。

### Changed
- 設計・挙動に関する重要な決定点（リリース時の仕様として記載）
  - 監視 (run_monitoring) は、どの環境でも本番用 SQLite（monitoring.db）を参照するように設計。監視データは環境によらず一元化して収集する想定。
  - run_execution は paper_trading 時にのみ paper_sqlite_path を使用し、本番 DB と完全に分離するように実装。
  - ロギングの初期化はエントリポイントで INFO レベルを使用（簡易起動時の見やすさ重視）。

### Fixed / Robustness
- .env パーサーの堅牢化
  - クォート内でのバックスラッシュエスケープ処理、コメントの取り扱い、export プレフィックスをサポート。
- 監視ループ・実行エンジンの停止ハンドリング
  - stop flag（data/stop_requested.flag）や KeyboardInterrupt を検知して安全に終了する実装。
- DuckDB / PyYAML の依存に対する耐性
  - config 検証時に PyYAML が未インストールの場合は警告を出し、YAML 内容検証をスキップする。

### Known limitations / Notes
- .env は機密情報を含むため絶対に Git にコミットしない旨の注意喚起をウィザードに含めている。
- apply_sector_cap は price_map に欠損価格（0.0）がある場合にエクスポージャーを過小評価する可能性がある旨の TODO コメントが残っている（将来的に前日終値等のフォールバックを導入予定）。
- position_sizing の lot_size は現状全銘柄共通の固定値（デフォルト 100）を前提。将来的には銘柄別 lot map を受け取れるように拡張予定。
- process priority / cpu affinity の設定は OS 権限や psutil の実装状況に依存するため、失敗時はログ警告でスキップするのみ。
- Monitoring の設計上、環境によらず本番 sqlite_path を使う決定は運用ポリシーに依存するため、必要に応じて設定の上書きを検討すること。

### Security
- .env の取り扱いに関する注意を明示（ウィザードで .env を生成するが Git にコミットしないことを強く推奨）。

---

注: 上記 CHANGELOG は、提供されたコードの API・コメント・設計意図から推測して作成したものです。実際のコミット履歴や変更差分が存在する場合は、正確な差分に基づいて更新してください。