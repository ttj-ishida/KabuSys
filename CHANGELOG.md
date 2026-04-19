# Changelog

すべての変更は Keep a Changelog の形式に従います。  
本ドキュメントはコードベースから推測して作成しています（実装上の挙動・環境変数名・ファイルパス等に基づく記述）。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース。自動売買システム「KabuSys」の基礎的な実行・監視・設定・ポートフォリオ構築・ユーティリティ群を追加。

### Added
- 実行／監視ランチャースクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による paper_trading モードをサポート。paper_trading の場合は専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理（data/execution.pid）。
    - スレッド上で ExecutionEngine.run_session を起動し、停止フラグ検知で安全に停止する仕組みを実装。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、RiskManager に設定可能な各種パラメータ（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）を反映。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path（data/monitoring.db）を使用して監視データを永続化。
    - 起動時にプロセス優先度を "high" に設定、停止フラグの検知でループ終了、例外発生時はログに出力して次ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - .env および .env.local の読み込み順序（OS 環境変数を保護）。
    - .env パース機能の充実（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等をサポート）。
    - Settings クラスを導入し、アプリ全体で利用する設定プロパティを提供（J-Quants / kabuAPI / DB パス / PID / 監視しきい値 / 環境判定等）。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証ロジックを提供。
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。選択肢・デフォルト・シークレット表示・確認保存を実装。
    - 生成される .env にテンプレートコメントを付与し、誤ってコミットしないよう注意喚起。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスと親ディレクトリの存在確認、YAML パースチェック（PyYAML 未インストール時は警告）等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合のフォールバックロジックを含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャー計算、上限超過セクターの候補除外を行う。unknown セクターは上限適用除外。
    - 市場レジームに対する投下資金乗数 calc_regime_multiplier を実装（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 各配分方式（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。
    - スケールダウン時の再配分ロジック（端数の優先配分を残差で決定）を実装。
    - 価格欠損時のスキップやデバッグログを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を持つファイルハンドラをルートロガーに設定。既存ハンドラのクリア処理、ログディレクトリ自動作成、環境変数 LOG_LEVEL / LOG_DIR からの解決をサポート。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows の PriorityClass / POSIX の nice 値）を追加。アクセス権限不足等の失敗は警告してスキップ。
    - CPU affinity 設定（set_cpu_affinity）を追加。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を実行するコードを run_execution と run_monitoring に追加し、監視テーブル群の存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading 用 SQLite（デフォルト data/paper_trading.db）から検証指標を集計・表示するレポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）、リスク却下数、稼働総回数等。
    - 基準値（閾値）を定義し、PASS/FAIL 判定を行う（例: 稼働率 >= 99%、P95 <= 200ms など）。
    - --from / --to / --db オプションをサポート。

- データ分析（開発中）
  - research/factor_research.py
    - DuckDB を用いたファクター計算基盤を追加（Momentum / Value / Volatility / Liquidity を想定）。モメンタム計算の意図・定数等を定義（実装の一部が含まれる）。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Notes / Implementation details
- 設定の自動ロードはデフォルトで有効。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することでスキップ可能。
- .env の読み込み順は OS 環境 > .env.local > .env（.env.local は既存の OS 環境変数を上書きしない保護機構あり）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルト 60 秒にフォールバックする。
- run_execution は起動時に停止フラグが既に立っている場合、エンジンを起動せず終了する保護を持つ。
- ログは標準出力（stdout）に出力され、ファイル出力は logs/<app_name>.log に日次ローテーションで保持される（デフォルト 30 日）。
- process_priority や CPU affinity の設定は権限不足や未対応プラットフォーム時に安全にスキップされる。

---

今後の改善候補（推奨）
- research/factor_research の完全実装とユニットテスト追加。
- BrokerClientFactory / ExecutionEngine / SystemMonitor 等の外部依存コンポーネントに対するモックを用いた統合テストの整備。
- .env 値の暗号化や機密情報のより安全な取り扱い（Vault 等）検討。
- ポートフォリオ構築・発注ロジックのより詳細なテスト（境界条件、端数処理、スケーリングアルゴリズム）。
- logging_setup のファイルハンドラ作成失敗時の通知改善（運用時の可観測性向上）。

（以上）