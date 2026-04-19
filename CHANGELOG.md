CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 実行用スクリプトを追加
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に依存せず本番用の sqlite_path を使用（Settings.sqlite_path）。
    - 停止はプロジェクト直下の data/stop_requested.flag（停止フラグ）で制御。
    - プロセス優先度を "high" に設定して起動（utils.process_priority）。
    - SQLite / DuckDB のコネクション確立とクリーンなクローズ処理を実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用することで本番 DB と分離。
    - 起動前に停止フラグをチェックし、実行中も停止フラグでセッション停止を行う。
    - ExecutionEngine をデーモンスレッドで起動し、PID ファイル管理と安全な終了処理を実装。
    - プロセス優先度を "high" に設定して起動。

- 設定管理と初期化ツールを追加
  - kabusys.config.Settings: 環境変数 / .env(.local) からの設定読み込みと検証を行うクラスを追加。
    - 自動 .env ロード（プロジェクトルートが見つかった場合）を行う。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env パースは export 形式・クォート・インラインコメントを考慮した堅牢な実装。
    - 各種設定項目（J-Quants、kabu API、DuckDB/SQLite パス、Paper Trading 設定、監視閾値、ログレベル等）のプロパティを提供。
    - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - config_setup: 対話式ウィザードにより .env ファイルの初期作成・更新を支援する CLI を追加。
    - 各設定項目の説明、シークレットマスク表示、デフォルトの取り扱い、保存確認を提供。
  - validate_config: .env と config/*.yaml の設定チェック CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML 必須。未インストール時はスキップして警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）を追加
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同点時に signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化による重み計算。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限（デフォルト 30%）を超えるセクターの新規候補を除外。
      - unknown セクターは上限チェック対象外。
      - 当日売却予定の銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下比率乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告を出力。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 許容リスク率・損切り率に基づくポジションサイズ算出。
      - equal/score: 重みと利用可能現金に基づく算出。
      - 単元株（lot_size: デフォルト 100）に丸め、1銘柄上限・全体利用上限（max_utilization）などを適用。
      - aggregate cap（全銘柄の合計投資が available_cash を超える場合）のスケーリング処理を実装。端数処理で再配分するロジックあり。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

- ユーティリティを追加 / 拡張
  - utils.logging_setup.setup_logging: stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定するユーティリティを追加。
    - ログレベルは引数→環境変数→デフォルトの順で解決。ログディレクトリは引数→LOG_DIR 環境変数→"logs/" の順で解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority
    - set_process_priority(level): psutil を用いて Windows/Linux/macOS の差分を吸収しプロセス優先度を設定。アクセス不可時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定（未対応環境は警告でスキップ）。

- 監視・監査系
  - monitoring 側の初期化を保証する関数 init_monitoring_db の呼び出しを run_monitoring/run_execution に組み込み（冪等）。
  - SystemMonitor.check_once() の呼び出しで例外を捕捉し、ログに例外情報を出力して次回ポーリングに備える堅牢化を実装。

- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成するスクリプトを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - 判定基準（デフォルト）を定義して PASS/FAIL を出力（閾値: uptime>=99.0%, fill_rate>=90%, send_rate>=95%, P95<=200ms）。
    - CLI オプション: --from, --to（YYYY-MM-DD）, --db（DBパス）。環境変数 PAPER_TRADING_SQLITE_PATH に対応。

- リサーチ
  - research.factor_research: DuckDB 接続を用いたファクター計算基盤を追加（モメンタム、MA200乖離、ATR 等を想定）。calc_momentum の実装開始（DuckDB/prices_daily を前提）。（ソースは途中まで実装）

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Notes / Known limitations
- portfolio.position_sizing:
  - price の欠損（0.0）がある場合にエクスポージャーやサイズ算出が過小推定される旨の TODO コメントあり。将来的には前日終値や取得原価でのフォールバックを検討。
  - lot_size は現状グローバル固定（将来的に銘柄別対応を検討）。
- .env パーサは多くのケースに対応するが、特殊な複雑なシェル展開（変数展開など）はサポートしていない。
- research.factor_research は未完（calc_momentum の実装が途中）であり、リサーチ機能は今後拡張予定。

How to run / 主要コマンド
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

リンク・参照
- 環境変数の詳細は kabusys.config.Settings のプロパティ定義を参照してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, など）。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース運用やバージョン管理ポリシーに合わせて適宜編集してください。）