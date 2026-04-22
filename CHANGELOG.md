# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。

全般:
- このリポジトリはバージョン管理された日本株自動売買システム（KabuSys）の初期リリース相当の実装を含みます。
- バージョンはパッケージ定義から __version__ = "0.1.0" としています。

## [0.1.0] - 2026-04-22

### Added
- 一般
  - パッケージ初期リリース相当の機能群を追加。
  - バージョン情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 起動スクリプト・実行制御
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止制御: プロジェクトの data/stop_requested.flag を検知してループを終了。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 例外発生時のログ出力と再試行（次のポーリングまで待機）を実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル管理（data/execution.pid）をサポート。
    - 実行スレッドをデーモンで起動し、停止フラグ検知で安全に engine.stop() を呼び出す制御ループを実装。
    - RiskManager の初期設定に broker.get_available_cash() を使用して initial_portfolio_value を設定。

- 設定管理
  - config.py
    - .env ファイルの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - export KEY=val 形式、クォート付き値、インラインコメントなど現実的な .env フォーマットのパースを実装。
    - 必須環境変数チェック用の _require 関数を提供（未設定時は ValueError を送出）。
    - 設定アクセスラッパ（Settings クラス）を追加。J-Quants / kabuステーション / LINE / DB / 監視 / システム設定等のプロパティを提供。
    - Paper Trading 向け設定（paper_fill_mode、paper_sqlite_path）や閾値（CPU/MEM/DISK）等をプロパティとして実装。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）および LOG_LEVEL のバリデーションを実装。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - 必須項目（J-Quants トークン、kabu API パスワード等）を対話で設定可能。シークレットはマスク表示。
    - 既存 .env の読み込みと Enter による既存値再利用をサポート。
    - .env ファイルのテンプレート書き出し（コメント付き）を実装。
    - デフォルト値、選択肢、説明を含む設定項目群を用意。

  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数未設定をエラー、プレースホルダ値を警告として判定。
    - DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック（PyYAML がない場合は警告でスキップ）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。アプリ共通で StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"）とログディレクトリ解決順（引数 > LOG_DIR > "logs/"）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続する耐障害設計。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収する優先度設定を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（未指定時は何もしない）。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算（重み: 1/N）。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別時価を算出し、1 セクター上限を超えている場合に当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算。
      - risk_based: risk_pct, stop_loss_pct を用いた単銘柄ベースのリスク算出式に基づいて算出。
      - equal/score: 重みと max_utilization を考慮して per-position 上限を計算。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）考慮。
      - aggregate cap: 全銘柄の合計投資額が available_cash を超える場合にスケールダウンし、残差に基づいて lot 単位で追加割当を行うアルゴリズムを実装。
      - cost_buffer を導入してスリッページ・手数料想定を保守的に反映。

- モニタリング / マニフェスト
  - monitoring.monitoring_db.init_monitoring_db の呼び出しポイントを run_monitoring / run_execution に追加し、監視テーブルの存在を冪等に保証。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - デフォルト DB パスを環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能（デフォルト: data/paper_trading.db）。
    - 指標:
      - 稼働率（uptime_pct）閾値 99.0%、
      - 注文成功率（fill_rate）閾値 90.0%、
      - 送信率（send_rate）閾値 95.0%、
      - P95 レイテンシ閾値 200 ms。
    - system_status / trade_logs / risk_logs テーブルから集計し、PASS/FAIL を判定して標準出力にレポートを出力。
    - コマンドライン引数 --from / --to / --db をサポート。

- リサーチ（ファクター計算）
  - research/factor_research.py（骨組み）
    - DuckDB を使用したモメンタム / Value / Volatility / Liquidity 等のファクター計算モジュールの設計方針と初期実装（calc_momentum 等の関数群の骨子）を追加（関数は prices_daily / raw_financials の参照を想定）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Usage tips
- .env の自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV=live の設定に注意（validate_config のガードを利用して事前チェックを推奨）。
- run_execution は paper_trading（分離 DB）と live を切り替える設計なので、Paper Trading 実行時には本番 DB に書き込まれないことを確認できます。
- ログ出力はデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。
- プロセス優先度設定や CPU affinity の適用には管理者権限が必要な場合があります。権限不足時は警告を出してフォールバックします。

---

この CHANGELOG はコードベースの現在の状態からの推測に基づいて作成しています。実際のリリースノートやリリース日付はプロジェクトの運用ポリシーに従って調整してください。必要であれば各モジュールごとのより詳細な変更点（関数シグネチャ・引数・返り値の仕様や例）も追記します。