# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

### Added
- ドキュメント生成用スクリプト群および実行用エントリポイントを追加。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。プロセス優先度を高く設定し、ブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行・停止監視を行う。KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離する設計。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag により制御。監視では環境に関係なく本番の sqlite_path を使用する旨の挙動を明示。

- 設定・環境管理機能を追加。
  - `kabusys.config.Settings` クラス: 環境変数から各種設定を取得するユーティリティを提供（J-Quants / kabu API / DB パス / PID /閾値など）。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（OS 環境変数を優先して上書き保護）。テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup: 対話式ウィザードにより .env を初期作成・更新する CLI を追加。シークレット扱い、選択肢、デフォルト値、保存確認を備える。
  - validate_config: .env および config/*.yaml の簡易検証 CLI を追加。必須環境変数の欠如、パスの存在確認、YAML のパース検証（PyYAML があれば実施）、本番環境向けガードを実装。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ内計算）。
  - portfolio.portfolio_builder: シグナルのソート/候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア全0 の場合のフォールバック警告あり。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap と、市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。unknown セクターの扱いやフォールバックロジックを記載。
  - portfolio.position_sizing: 各銘柄の発注株数算出 calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応し、単元株丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer に基づく保守的見積り、残差の分配ロジック等を実装。

- ロギング・プロセス制御ユーティリティを追加。
  - utils.logging_setup.setup_logging: stdout ストリームハンドラと TimedRotatingFileHandler（日次、30世代保持）をルートロガーに設定する共通ユーティリティ。LOG_DIR / LOG_LEVEL の解決順・デフォルトを定義。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils.process_priority: プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。Windows/Linux/macOS に対応し、失敗時は警告でスキップ。CPU affinity 設定の補助関数も実装（最初の N コアに固定）。

- 監視・検証ツールを追加。
  - tools.paper_verification_report: Paper Trading 用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）などの検証レポートを生成する CLI を追加。複数閾値（稼働率 99% 等）に基づく PASS/FAIL 判定ロジックを実装。日付フィルタ (--from / --to) と DB パス指定 (--db / 環境変数) をサポート。

- 研究用ファクターモジュールを追加（骨子）。
  - research.factor_research: DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 等の計算を行う設計。モメンタム計算 calc_momentum のインターフェースや定数が整備（実装途中の箇所あり）。

- パッケージメタデータ
  - __version__ を "0.1.0" に設定。

### Changed
- デフォルトの挙動・配置に関する仕様を明確化。
  - run_monitoring は環境にかかわらず監視用 DB（sqlite_path）を本番パスとして使用することを明示。
  - run_execution は paper_trading モード時に paper_sqlite_path を用いることで本番データと完全に分離する設計。
  - logging_setup: 標準出力は stdout を使用（stderr ではない）。これはタスクスケジューラや cron でリダイレクトしたときの扱いを想定した仕様。

### Fixed
- 各種環境変数パースやフォールバックの堅牢化。
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出しデフォルト値（60 秒）を使用するようにした。
  - .env 解析ロジックで引用符・バックスラッシュエスケープ・インラインコメント等に対応して安定的に読み込めるように改善。
  - process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に例外を投げず警告でスキップするようにした。

### Security
- なし

---

## [0.1.0] - 2026-04-19

初期リリース。上記「Unreleased」に列挙された機能群を実装・公開。

- 実行スクリプト: run_execution, run_monitoring（プロセス優先度設定、PID/停止フラグ対応）
- 設定管理: Settings クラス、自動 .env ロード、config_setup 対話ウィザード、validate_config CLI
- ポートフォリオ構築: portfolio_builder, position_sizing, risk_adjustment（等金額・スコア重み・リスクベース、セクター上限、レジーム乗数）
- ユーティリティ: ロギング設定（TimedRotatingFileHandler）、プロセス優先度/CPU affinity 設定（psutil ベース）
- ツール: Paper Trading 検証レポート生成スクリプト
- 研究モジュールの骨子: factor_research（DuckDB ベースのファクター計算設計）
- パッケージバージョン: __version__ = "0.1.0"

注記:
- 実行時には JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等の必須環境変数を .env に設定してください（validate_config で事前検証可能）。
- .env はセキュリティ上 Git にコミットしないでください（config_setup のヘッダにも注意書きを追加）。

-- end of changelog --