# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基本モジュールを実装。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を "high" に設定してから起動する。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作する（BrokerClientFactory により MockBrokerClient が選択される想定）。
    - PID ファイル管理、停止フラグ (data/stop_requested.flag) の検出による安全停止を実装。
    - ExecutionEngine の構成要素（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててスレッド実行する。RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き機能（デフォルト 60 秒）。無効値はデフォルトにフォールバックし、警告ログを出す。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨の設計（監視用 DB の独立性）。
    - 停止フラグ検出でループを安全に終了、KeyboardInterrupt のハンドリングを実装。

- 設定関連
  - config.py
    - Settings クラスを導入し、環境変数をプロパティとして安全に取得・検証する（J-Quants, kabu API, DB パス, PAPER_FILL_MODE 等）。
    - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。これにより CWD に依存しない .env 自動ロード処理を提供。
    - .env 自動読み込み機能: OS 環境変数 > .env.local > .env の優先順で読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env の値パースはクォート (シングル/ダブル)・エスケープ・インラインコメント等に対応。
    - 環境変数の必須チェック（_require）と各種型変換・検証（env 値の集合や LOG_LEVEL, PAPER_FILL_MODE の検証）を実装。
  - config_setup.py
    - 対話式ウィザードで .env の新規作成 / 更新を支援する CLI を追加。
    - 入力支援（選択肢、デフォルト、シークレットマスク）と既存 .env の読み込み／Enter で再利用機能を実装。
    - .env をテンプレート形式で書き出す機能を提供（Git にコミットしない旨の注意文つき）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する検証 CLI を追加。
    - 必須/任意環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML 未インストール時は警告）などを実装。
    - --strict オプションにより警告も FAIL として扱うモードを提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル上位選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が 0 の場合は等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック (apply_sector_cap) を実装。既存保有のセクター時価を計算し、上限超過セクターの新規候補を除外。unknown セクターは上限対象外。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバックして警告）。
  - portfolio/position_sizing.py
    - 発注株数計算ロジック (calc_position_sizes) を実装。allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 損切り率・リスク率に基づくリスクベースのサイズ算出、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮、余り分の分配ロジック等を実装。
  - portfolio パッケージのエクスポート一覧を定義。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的ログ設定ユーティリティを実装。StreamHandler を stdout に出力し、TimedRotatingFileHandler による日次ローテーション（デフォルト logs/<app_name>.log、30 日保持）を root ロガーに設定する。
    - 既存ハンドラのクリア、ログレベル / ログディレクトリの解決順（引数 > 環境変数 LOG_DIR > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを実装（Windows と POSIX を吸収）。set_process_priority("high"|"normal"|"low") を提供し、psutil に基づいて nice/priority を設定。アクセス権限不足などは警告を出して安全にスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（例外時は警告）。

- 監視・レポート
  - monitoring 側の DB 初期化関数 init_monitoring_db を呼び出す形で監視テーブルの整備を実施（冪等性を担保）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。SQLITE DB（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - PASS/FAIL の閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付範囲フィルタ (--from/--to) と --db オプションをサポート。DB が見つからない場合のエラーメッセージを実装。

- 研究 / ファクター算出（骨子）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨子を実装。モメンタム（1/3/6 か月）、MA200 乖離、ATR（ボラティリティ）、流動性指標などを計算する方針を記述。関数 calc_momentum のシグネチャと設計方針を実装（詳細計算ロジックの一部は継続実装予定）。

- パッケージメタ
  - __init__.py にてバージョン情報 __version__ = "0.1.0" を設定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし

### Notes / Implementation details
- .env 読み込み処理は OS 環境変数を保護する仕組み（protected keys）を採用しており、.env.local による上書きが可能。ただし OS 環境変数は上書かれない。
- ロギングはコンソール出力を stdout に統一しており、cron 等からの起動時にリダイレクトしやすい設計。
- run_monitoring と run_execution は停止フラグファイル（data/stop_requested.flag）を検出して安全に停止する仕組みを持つため、運用上の Kill Switch と連携できる。
- Paper Trading と本番 DB は分離しており、誤って本番 DB を上書きするリスクを低減する設計。

---

この CHANGELOG はコードベースから推測して作成したものであり、実装意図・詳細はソースコードおよびドキュメント（README / PortfolioConstruction.md / StrategyModel.md 等）を参照してください。