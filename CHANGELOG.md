# CHANGELOG

すべての注目すべき変更をこのファイルに記載します。

フォーマットは Keep a Changelog に準拠します。バージョン番号はパッケージ内の __version__（現状 0.1.0）に合わせて記載しています。日付はこのリリースを推定した日付です。

## Unreleased

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 環境設定と自動ロード機構を実装（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 複数の設定プロパティ（J-Quants、kabuAPI、DB パス、Paper Trading モード、監視閾値など）を提供。
    - 環境変数の値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - settings = Settings() を提供し簡易アクセスを可能に。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - プロセス優先度を高（High）に設定して起動。
    - KABUSYS_ENV が paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを抽象化して取得。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と実行用 pid ファイル（data/execution.pid）をサポート。
    - 停止フラグ検知で安全に停止する挙動。
  - 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - SystemMonitor の check_once を定期呼び出し、例外はログ出力しループ継続。
    - 停止フラグ検知でループを終了。KeyboardInterrupt での終了もハンドル。

- 設定関連 CLI / ユーティリティ
  - 対話式 .env ウィザード（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。シークレット項目はマスク表示。
    - 値の確認後 .env を安全に書き込む機能を提供。
  - 設定検証ツール（src/kabusys/validate_config.py）。
    - 必須/任意環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス・config/*.yaml の存在/パース検査を実施。
    - --strict オプションで警告を失敗扱いにする機能。
    - PyYAML 未インストール時の graceful なスキップを実装。
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH 指定可）からレポートを生成。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（avg/max/P95）等を算出し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、存在しないテーブルへの耐性（OperationalError をキャッチして N/A 扱い）を実装。

- ポートフォリオ構築ライブラリ（純関数群、DB 非依存）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクターエクスポージャを元に候補から除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に基づく乗数を返却（未知値は 1.0 にフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method による差分処理（"risk_based", "equal", "score"）。
    - lot_size（単元）に基づく丸め、max_position_pct による per-stock 上限、available_cash による aggregate cap とスケーリング、cost_buffer を考慮した保守的見積り、残差配分ロジックを実装。
    - 価格未取得時のスキップとログ出力。

- ログ・プロセスユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた標準的な設定。
    - LOG_DIR / LOG_LEVEL 環境変数や関数引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能（設定失敗時は警告ログ）。
    - 権限不足や未対応 OS へのフォールバックハンドリング。

- リサーチ（骨組み）
  - factor_research モジュール開始（src/kabusys/research/factor_research.py）
    - Momentum / MA200 / ATR / ボリューム等を計算する設計方針と定数を定義。DuckDB 接続を使用する方針。
    - モメンタム計算 calc_momentum の実装を開始（未完の箇所あり）。

### Changed
- （新規メインリリースのため過去からの変更は無し、ただし設計上の注意点を以下に記載）

### Fixed
- （該当なし）

### Removed
- （該当なし）

### Notes / Breaking Changes / Important behaviors
- 監視（run_monitoring）は KABUSYS_ENV に関わらず production 用 sqlite_path を使用して監視データベースを初期化します（監視テーブルは常に本番 DB に作成される想定）。この挙動は意図的であり、監視データの分離を行っていません。必要であれば環境ごとの分離を検討してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離します。
- .env の読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local の override は OS 環境変数を上書きしません。
- PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかで、無効値は ValueError を送出します。
- MONITOR_POLL_INTERVAL の不正値（0 や負値、非整数）は警告を出してデフォルト（60 秒）にフォールバックします。
- process_priority や CPU affinity の設定は環境依存（権限や OS 固有機能）であり、失敗時は警告ログを出して処理を続行します。

### CLI / 実行例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース履歴や日付はリポジトリの実運用に合わせて適宜修正してください。）