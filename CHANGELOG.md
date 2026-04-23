# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23

### Added
- 初回公開リリース。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - 停止制御用フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知時に安全に停止させるロジックを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックし、警告ログを出力。
    - 監視データは環境に関わらず本番用 sqlite_path を使用する仕様。
    - 停止フラグファイル検知でループを終了し、KeyboardInterrupt に対応。
- 設定・環境関連
  - config.py: 環境変数/.env の読み込み・管理を行う Settings クラスを追加。  
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）に基づく .env 自動ロード（.env → .env.local、OS 環境変数を保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の設定プロパティを提供（J-Quants / kabuAPI / LINE / データベースパス / 監視閾値 / 環境判定 etc.）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。  
    - 必須項目・秘密項目（マスク表示）・デフォルト・選択肢を定義し、.env を生成。
  - validate_config.py: 起動前設定検証 CLI を追加。  
    - 必須環境変数の有無、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在・パース（PyYAML が存在する場合）などをチェック。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルのソート・候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。既存保有のセクター別エクスポージャー計算、blocked sector の除外ロジック、未知レジーム時のフォールバックを提供。
  - portfolio/position_sizing.py: 株数決定ロジック（calc_position_sizes）を実装。  
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer による保守的見積り、残余キャッシュによる再配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一ログセットアップ関数 setup_logging を追加。  
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - LOG_LEVEL / LOG_DIR の優先順位と引数での上書き対応。
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。  
    - Windows/Linux/macOS（posix）を考慮し、失敗時は警告ログでスキップ。
- モニタリング DB 初期化
  - monitoring/monitoring_db.py（インポートから存在が推測）を初期化呼び出しで利用。init_monitoring_db が idempotent に監視テーブル存在を保証することで、複数プロセスからの安全な起動を想定。
- Execution 内部コンポーネント（呼び出し/組み立て）
  - BrokerClientFactory により環境に応じたブローカークライアントを作成（Mock / 実ブローカーの切替）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動方法を実装（EngineConfig により target_date を指定）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成 CLI を追加。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計してレポート出力。
    - 既定の合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションに対応。
- 研究用モジュール（下書き）
  - research/factor_research.py: DuckDB を使用したファクター計算基盤（モメンタム、MA200、ATR、ボリューム系など）の実装方針と関数 calc_momentum の雛形を追加（prices_daily / raw_financials テーブル参照想定）。※ファイルの一部は未完（切片あり）。

### Changed
- プロジェクト構成上の初期機能を提供（設定管理 / 起動スクリプト / ポートフォリオ構築 / 監視 / ロギング / プロセス制御 / ツール群）。（初版のため変更履歴はなし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数 .env の生成時に「.env を絶対にコミットしない」旨を README に明示するためのコメントを .env 生成ロジックに追加。

---

Notes / 既知の注意点・今後の改善予定
- portfolio/position_sizing.calc_position_sizes:
  - price が欠損した場合のフォールバック（前日終値や取得原価の利用）は TODO。現在は価格が無い銘柄をスキップする実装。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターはセクター上限判定の対象外として扱われるため注意。
- research/factor_research.py は一部未完（ファイル末尾が切れている）。ファクター計算ロジックの追加実装・テストが必要。
- logging_setup: ログディレクトリ作成失敗時はファイル出力を行わない設計になっているため、運用環境では logs/ ディレクトリの書き込み権限に注意してください。
- process_priority・set_cpu_affinity は権限依存（psutil による AccessDenied など）で失敗する可能性があり、その場合は警告を出して処理を継続します。

今後のリリースでは、テストカバレッジの追加、research モジュールの完成、ExecutionEngine の詳細実装・フェイルセーフ強化を予定しています。