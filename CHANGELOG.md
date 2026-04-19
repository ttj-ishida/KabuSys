# Changelog

すべての変更は「Keep a Changelog」形式で記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

初回リリース。KabuSys の基盤機能を実装しました（構成・起動スクリプト・ユーティリティ・ポートフォリオ構築ロジック・解析ツール等）。

### Added
- 全体
  - パッケージ初期バージョンを設定（__version__ = "0.1.0"）。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。これにより .env 自動ロードが CWD に依存せずに動作。
  - .env ファイルの自動読み込み実装（.env および .env.local）。OS 環境変数を保護するための上書き制御を導入。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。

- 設定管理（kabusys.config）
  - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供（J-Quants / kabu API / LINE / DB / 監視・システム設定等）。
  - 各種バリデーションを実装：
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）。
    - LOG_LEVEL の有効値チェック。
    - PAPER_FILL_MODE の有効値チェック（instant / partial / never / reject）。
  - paper_trading 用の DB パス（PAPER_TRADING_SQLITE_PATH）と本番用 sqlite_path を分離。

- 設定ウィザード CLI（kabusys.config_setup）
  - .env ファイルを対話式に作成・更新するウィザードを実装。
  - JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等の必須項目に対応。シークレット項目はマスク表示。
  - 生成される .env のテンプレートと保存処理を実装（.env を Git にコミットしない旨の注意書き含む）。

- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の設定不備を事前検出する CLI を実装。
  - 必須環境変数チェック・KABUSYS_ENV チェック・LOG_LEVEL チェック・DB パスの親ディレクトリ存在チェック・YAML ファイルの存在およびパース検証（PyYAML が存在する場合）を実装。
  - --strict オプションで警告を失敗扱いにする挙動を追加。

- ログ設定ユーティリティ（kabusys.utils.logging_setup）
  - アプリケーション共通のログ設定ヘルパーを実装。
  - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。
  - ログレベル・ログディレクトリの解決ロジック（引数 > 環境変数 > デフォルト）を実装。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォームでプロセス優先度を設定する set_process_priority を実装（Windows と POSIX を吸収）。
  - CPU コア固定用の set_cpu_affinity を実装（psutil を利用）。アクセス拒否などは警告でスキップされる安全設計。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実行。
    - RiskManager のデフォルト RiskConfig を設定（max_position_pct 等）。initial_portfolio_value を broker.get_available_cash() で初期化。
    - ExecutionEngine.run_session を別スレッドで起動し、停止フラグを監視して安全に停止。
    - PID ファイル（data/execution.pid）指定と停止フラグ存在時の起動抑止。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - 候補選定（select_candidates）: スコア降順・タイブレークの実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコア 0 の場合は等分へフォールバックし警告を出す。
  - risk_adjustment
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に応じた乗数を返す（未知レジームは 1.0 にフォールバック、警告）。
  - position_sizing
    - 発注株数計算（calc_position_sizes）: allocation_method ("risk_based"/"equal"/"score") に対応。
    - 単元丸め（lot_size）、1銘柄上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。
    - 価格欠損時のスキップやログ出力によるトレースを考慮。

- リサーチ / ファクター（kabusys.research.factor_research）
  - DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算するモジュールを追加。設計方針や定数、calc_momentum の実装（部分）が含まれる（prices_daily / raw_financials を参照）。

- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
    - Paper Trading 用 SQLite のデータからシステム安定性・注文成功率・シグナル精度・API レイテンシ（平均/最大/P95）を集計して標準出力に整形したレポートを生成する CLI を実装。
    - デフォルトの DB パスは data/paper_trading.db。コマンドライン引数 --from/--to/--db に対応。
    - P95 計算、各種比率（稼働率・成功率・送信率）やしきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- （初回リリースにつき該当なし）

Notes / 注意事項
- .env に機密情報（API トークン等）を保存する実装があるため、.env を VCS にコミットしないことを強く推奨します（config_setup の出力にも注意書きあり）。
- process_priority / cpu_affinity はプラットフォーム依存の権限に依存します。権限不足時は警告を出して処理をスキップします。
- run_monitoring は「監視 DB として常に本番 sqlite_path を使用する」仕様です。運用上の分離が必要な場合は設定を見直してください。
- research.factor_research の calc_momentum 等は大枠を実装していますが、さらなるファクター実装やエッジケース対応は今後の開発で追加予定です。

もしリリースノートに追加したい変更点や注記（例: 既知の不具合、今後追加予定の機能など）があれば教えてください。必要に応じて追記します。