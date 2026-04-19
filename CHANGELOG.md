CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 現時点ではなし

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ群、起動スクリプト、ポートフォリオ構築ロジック、検証ツール類を収録。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定・読み込み
  - src/kabusys/config.py
    - .env の自動読み込み機能をプロジェクトルート（.git または pyproject.toml を起点）から実行。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - シンプルかつ堅牢な .env パーサを実装（export 句、クォート、インラインコメント、エスケープ対応）。
    - Settings クラスを導入し、アプリケーション設定をプロパティとして提供（J-Quants / kabuAPI / DB パス / PID / Kill Switch / 閾値 / 環境判定など）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の環境変数処理を実装し、無効値チェックを行う。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の作成／更新を支援。
    - 既存 .env 読み取り、シークレット項目のマスク表示、選択肢チェック、最終確認後のファイル書き出しを実装。
    - デフォルト値や説明文を含む複数項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE_* / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START）。

- 設定検証ツール CLI
  - src/kabusys/validate_config.py
    - .env や config/*.yaml の設定不備を起動前に検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在および (PyYAML があれば) パース検証、本番環境向けの追加警告を実装。
    - --strict オプションで警告を失敗扱いにするモードを提供。

- ロギング設定ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 全起動スクリプトで共通利用する setup_logging を実装。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバック動作を考慮。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分吸収を行う set_process_priority(level) を実装。呼び出し側は "high"/"normal"/"low" を指定するだけでよい。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（プラットフォーム制約や権限不足時は警告でスキップ）。

- 起動スクリプト（デーモン風のループ / セッション）
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag による検知。
    - 監視では常に production 相当の sqlite_path を使用する（KABUSYS_ENV に関わらず）。
    - 起動直後にプロセス優先度を "high" に設定し、duckdb/ sqlite の接続初期化を行う。
    - check_once() 呼び出しの例外を捕捉してループ継続する堅牢化。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて paper_trading 用 DB (data/paper_trading.db) を使用し、本番 DB と分離。
    - PID ファイル / stop flag (data/stop_requested.flag) を用いた起動/停止制御、ExecutionEngine を別スレッドで実行し終了監視を行う。
    - 初期化時に RiskManager, OrderManager, OrderRepository, Reconciler を組み立て、EngineConfig(target_date) を渡す。

- ブローカーファクトリ / 実行関連インターフェース（参照）
  - src/kabusys/execution/*（参照されるがコードは本差分では含まれていない）：BrokerClientFactory を経由した BrokerClient の生成を想定。

- 監視 DB 初期化フック
  - src/kabusys/monitoring/monitoring_db.py の init_monitoring_db を起動時に呼び出して監視用テーブルの存在を保証（冪等）。（起動スクリプトから利用）

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を提供。
    - calc_score_weights は全スコアが 0 の場合に等金額へフォールバックし警告ログを出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull:1.0 / neutral:0.7 / bear:0.3）。未知レジームはフォールバックで 1.0。

  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数決定アルゴリズムを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based: リスク（risk_pct）、損切り幅（stop_loss_pct）からベース株数を算出、単元株（lot_size）丸め処理を実施。
    - aggregate cap のスケーリングロジックを実装し、利用可能現金を超える場合はスケールダウン、その後残余キャッシュで残差配分を行う。
    - lot_size と cost_buffer（手数料/スリッページ見積り）に対応。

- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率・注文成功率・送信率・レイテンシ等の指標を集計してレポート出力。
    - P95 計算、基準値（稼働率 99%, 成立率 90%, 送信率 95%, P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプション対応。

- リサーチ / ファクター計算（骨格）
  - src/kabusys/research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity 記載）。関数のインターフェース設計と定数定義を含む。

### Changed
- 初期リリースのため、後方互換性や API 変更はなし（今後の変更で Section を追加予定）。

### Fixed
- 初期リリース。ファイル単位での堅牢化（例: .env 読み込み失敗時の警告、ログディレクトリ作成失敗時のフォールバック、psutil の未実装定数ハンドリング）を実装して既知の環境差異に対処。

### Notes / TODO（ドキュメント上の注意）
- portfolio.position_sizing.calc_position_sizes:
  - 価格が 0.0 の場合の取り扱いに注記（コメントで将来的に前日終値等のフォールバックを示唆）。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターの取り扱いは現在除外しない設計。
- run_monitoring / run_execution:
  - 実環境での運用に際しては .env と config/*.yaml の検証を推奨（python -m kabusys.validate_config）。

---

今後の予定:
- research/factor_research の実装完了（SQL クエリと正規化ユーティリティ連携）。
- execution モジュールの詳細実装（Broker 実装、ExecutionEngine のより細かいテレメトリ）。
- 単体テスト・CI の追加、ドキュメント整備（API 仕様書、運用手順書）。

以上。