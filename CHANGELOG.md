CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています（日本語表記）。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-19
------------------

Added
- 基本リリース: パッケージバージョンを __version__ = "0.1.0" として公開。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は起動環境にかかわらず設定されている sqlite_path（本番用）を使用して監視データを保存。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全停止を実装。
    - プロセス優先度を起動時に "high" に設定する処理を導入。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立てを実装。
    - 実行中スレッドをデーモンで起動し、停止フラグ検知での安全停止をサポート。
    - PID ファイル出力（data/execution.pid）処理との連携。
- 設定・環境管理
  - config.Settings: 環境変数アクセスラッパーを追加。
    - J-Quants / kabu API / LINE / DB パス / 監視しきい値 等のプロパティを提供。
    - KABUSYS_ENV/LOG_LEVEL 等の値検証を実装（無効値は ValueError）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant|partial|never|reject）。
    - paper_sqlite_path、pid_file_path、kill_flag 関連の設定を提供。
  - 自動 .env 読み込み機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースはクォート／エスケープ／インラインコメント等に対応（詳細な挙動実装）。
- 設定ユーティリティ
  - config_setup: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 標準の設定項目リスト（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。
    - シークレット項目はマスク表示、確認プロンプト、.env 書き出しテンプレートを提供。
  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict を指定すると警告も FAIL 扱いで exit(1)。
- ログ / プロセスユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通関数を提供。
    - LOG_DIR/LOG_LEVEL の環境変数順で設定を解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority:
    - set_process_priority(level) で Windows / POSIX を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定するユーティリティを追加。
    - 権限不足や未対応プラットフォームは警告ログを出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・同点のタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア重みの重み算出。スコア合計が 0 の場合は等金額へフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別エクスポージャ算出に基づく候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供。未知レジームは警告の上で 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した発注株数計算を実装。
    - 単元株（lot_size）で丸め、per-stock/max_utilization/aggregate cap（available_cash）を考慮したスケーリングと余り配分アルゴリズムを実装。cost_buffer により手数料・スリッページを保守的に見積もる。
    - price 欠損時はスキップする等の堅牢性を考慮。
- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標を集計しレポート出力（期間フィルタ可能）。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、平均/最大/P95 レイテンシ等。
    - 判定基準（デフォルト閾値）を定義し PASS/FAIL として判定。
    - P95 計算実装、クエリ生成と日付フィルタ化をサポート。DB テーブルが存在しない場合は安全に N/A を扱う。
- research
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールを追加（モメンタム関連の実装を開始）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Breaking changes / 注意事項
- 監視コンポーネントのデータ保存先について:
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっています。開発環境で監視データを完全分離したい場合は環境設定 (SQLITE_PATH) を明示的に変更してください。
- Paper Trading 分離:
  - run_execution は paper_trading 環境時に専用の SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用するため、本番データと混在しません。
- .env の自動ロード:
  - プロジェクトルート検出ロジックは .git または pyproject.toml を基準とするため、配布後や特定の配置では自動ロードをスキップする可能性があります。自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ出力:
  - デフォルトで logs/<app_name>.log に日次ローテーションでログが蓄積されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 実装上の TODO / 注意:
  - portfolio.risk_adjustment.apply_sector_cap は price が欠損 (0.0) の場合にエクスポージャを過少評価する可能性があり、将来的にフォールバック価格（前日終値等）を導入することが想定されています（ソース内に TODO コメントあり）。
  - research.factor_research はファイル末尾が途中で切れている（実装継続の痕跡）ため、完全実装は今後の作業を要します。

参考: 実行例 / ユーザー操作
- 環境検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- .env ウィザード:
  - python -m kabusys.config_setup
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定

---
この CHANGELOG はソースコードから推測できる機能・設計意図に基づいて作成しています。実際の変更履歴や公開バージョンの注記と差異がある場合は、差分を反映するよう更新してください。