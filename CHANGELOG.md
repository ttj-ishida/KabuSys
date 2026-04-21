# Changelog

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従います。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
- 環境設定/設定管理
  - 環境変数を扱う Settings クラスを追加（src/kabusys/config.py）。
  - .env 自動読み込み機能を追加（プロジェクトルートの検出は .git または pyproject.toml に基づく）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の読み込み優先順: OS 環境 > .env.local > .env（既存 OS 環境変数は保護される）。
  - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い等を実装。
  - Settings で各種設定値をプロパティとして取得可能（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

- 設定ウィザード CLI
  - 対話式に .env を作成/更新する config_setup CLI を追加（src/kabusys/config_setup.py）。
  - デフォルトや既存値の再利用、シークレット項目のマスク表示、保存前確認などの機能を備える。

- 設定検証 CLI
  - .env と config/*.yaml の起動前検証を行う validate_config CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML が無い場合はスキップ）、KABUSYS_ENV=live 向けの追加ガード等を実装。
  - --strict モードで警告を失敗扱いにできる。

- 実行/監視エントリポイント
  - Execution エンジン起動スクリプト run_execution を追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine をスレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - デフォルトの RiskManager 設定値を含む（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10 等）。
    - 実行中の PID を data/execution.pid に保存する機構を想定（pid_file を渡す）。
  - SystemMonitor ポーリングループ起動スクリプト run_monitoring を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上でデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db がデフォルト）を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）でループを終了。例外発生時はログを出し次のポーリングで再試行する。

- ログ/プロセスユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリとログレベルの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX を吸収して set_process_priority(level)（high/normal/low）を提供。psutil による実装で失敗時は警告してスキップ。
    - set_cpu_affinity(cpu_count) によるコア固定機能を追加（必要に応じて無視されることを想定）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等金額・スコア加重）を提供する portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を提供する risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター不明 ("unknown") は上限適用除外の挙動を明記。
    - レジーム乗数: bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告の上 1.0 をフォールバック。
  - 発注株数決定（position sizing）を提供する position_sizing（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - lot_size 単位で丸め、1銘柄上限・合計投下資金上限・cost_buffer（スリッページ/手数料見積り）を考慮したスケーリング機構を実装。
    - aggregate cap が超える場合はスケーリングして残差を考慮した追加配分を行う。

- Paper Trading 検証レポート
  - Paper Trading 用の検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - DB（デフォルト data/paper_trading.db）から system_status, trade_logs, risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）を算出。
    - P95 計算、期間指定の --from / --to オプション、しきい値による PASS/FAIL 判定を実装。
    - デフォルトの基準値（例: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義。

- 研究用ファクター計算モジュール（部分実装）
  - ファクター計算（モメンタム等）を行う research/factor_research モジュールを追加（src/kabusys/research/factor_research.py）。（モジュールは設計方針と定数、関数シグネチャの骨組みを含む。calc_momentum の実装が途中まで含まれている。）

- パッケージ情報
  - パッケージの __version__ を 0.1.0 に設定（src/kabusys/__init__.py）。

### Changed
- なし（初回リリースのため既存コードの変更履歴はなし）。

### Fixed
- なし（初回リリース）。

### Documentation
- 各 CLI やユーティリティに docstring とコメントで使い方・設計意図を付与。
- config_setup と validate_config に CLI ヘルプと使用例を含む説明を追加。

### Notes / Implementation details
- データベース接続:
  - DuckDB と SQLite の両方を使用する設計。各起動スクリプトは duckdb_conn と sqlite_conn を開き、終了時に必ずクローズする。
  - 監視テーブルの初期化（init_monitoring_db）を冪等に実行して監視用テーブルの存在を保証する。
- ロギング:
  - コンソール出力は stdout を使用（cron などで stdout/stderr を一本化する運用を想定）。
- セキュリティ / 注意事項:
  - .env は決して Git にコミットしないことを明記（config_setup の生成ヘッダに注記）。
  - KABUSYS_ENV=live の場合は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値に関する注意喚起を行う（validate_config）。

### Breaking Changes
- なし

---

このリリースに関して不明点や changelog に追加してほしい箇所があれば教えてください。