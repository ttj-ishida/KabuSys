# Keep a Changelog
すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-20

### 追加
- 初回リリース（ベース機能の実装）。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動用エントリポイントを追加。環境に応じて paper_trading 用 DB を分離し、MockBrokerClient を使用する（KABUSYS_ENV=paper_trading）（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能、停止フラグ（data/stop_requested.flag）による終了処理を実装（src/kabusys/run_monitoring.py）。
- 設定管理
  - Settings クラスを実装し、環境変数／.env ファイルから各種設定を取得（データベースパス・API トークン・監視閾値など）（src/kabusys/config.py）。
  - .env の自動読み込み機能を実装（プロジェクトルートが見つかった場合に .env/.env.local を読み込み）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（src/kabusys/config.py）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証とデフォルトを実装。
- 設定サポート CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する機能を提供（src/kabusys/config_setup.py）。
  - validate_config: .env や config/*.yaml の簡易検証 CLI を追加（--strict オプションで警告を FAIL 扱いにできる）（src/kabusys/validate_config.py）。
- ロギング／プロセス制御ユーティリティ
  - setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通関数を追加（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows/Linux/macOS を透過するプロセス優先度設定と CPU affinity 設定を追加（psutil 利用）（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder: シグナル選別（select_candidates）・等重配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター上限フィルタ（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。リスクベース・等分配・スコア配分対応、単元株（lot_size）対応、コストバッファ・aggregate cap によるスケーリングロジックを実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- 研究モジュール（骨組み）
  - factor_research: DuckDB を用いたファクター計算モジュールの骨組みを実装（モメンタム・ATR・出来高等の計算方針を記述）。DuckDB 接続を受ける設計（src/kabusys/research/factor_research.py）。
- Paper Trading 検証ツール
  - paper_verification_report: Paper Trading 用 SQLite DB から稼働率・注文成功率・レイテンシ等を集計し、PASS/FAIL 判定を出力するレポート生成スクリプトを追加（P95 計算、閾値定義、日付フィルタ対応）（src/kabusys/tools/paper_verification_report.py）。
- DB 初期化連携
  - 監視用 SQLite テーブル存在を保証する init_monitoring_db の呼び出しを各起動スクリプトで実施（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- パッケージ情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

### 変更（設計決定）
- ログハンドラのデフォルトは stdout（cron等との相性を考慮）としている（src/kabusys/utils/logging_setup.py）。
- run_monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計とした（監視データは本番 DB を参照）（src/kabusys/run_monitoring.py）。
- run_execution は paper_trading 環境で paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と完全分離する設計（src/kabusys/run_execution.py）。
- .env ファイルの読み込み順は OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護）とした（src/kabusys/config.py）。

### 修正（バグ回避・堅牢化）
- .env パーサーはクォート済み値のエスケープやインラインコメント処理を考慮した堅牢な実装を導入（src/kabusys/config.py）。
- process_priority / set_cpu_affinity は psutil の権限エラーや未対応 OS を安全にハンドリング（警告ログを出してスキップ）（src/kabusys/utils/process_priority.py）。
- logging_setup はログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力のみで継続する実装（src/kabusys/utils/logging_setup.py）。
- calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし、警告を出力するようにした（src/kabusys/portfolio/portfolio_builder.py）。
- calc_position_sizes の aggregate cap スケーリングは端数処理（lot_size 単位）と残余配分を考慮した実装で、投下資金が available_cash を超える場合に安全に縮小するよう改善（src/kabusys/portfolio/position_sizing.py）。

### ドキュメント（コメント・使用例）
- 各モジュールに使用例・設計方針・注意点をコメントで明記（各 src/... ファイル）。特に PortfolioConstruction/StrategyModel の該当セクション参照や将来の拡張点（lot_size マスタ化等）を示唆。

### 互換性 / マイグレーション
- 初回リリースのため互換性の過去版はなし。既存の運用環境へ導入する際は以下点に注意:
  - .env を作成し必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください（config_setup を推奨）。
  - Paper Trading を利用する場合は KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に記録され、本番 DB と分離されます。
  - LOG_DIR 指定がない場合はデフォルトで logs/ に日次ローテーションログが出力されます。ログディレクトリ作成権限に注意してください。

### 既知の制限・TODO
- factor_research の実装は骨組み中心で、一部関数（例: calc_momentum の実装途中）や詳細なファクター処理は今後実装予定（src/kabusys/research/factor_research.py）。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価利用）は TODO コメントとして残している（src/kabusys/portfolio/risk_adjustment.py）。
- ブローカークライアント周り（BrokerClientFactory の具体実装）は外部依存のため環境に応じたモック/本番実装の管理が必要（src/kabusys/run_execution.py）。

---

（このファイルはコードベースの現状から推測して作成した CHANGELOG です。必要に応じて項目の移動・詳細化を行ってください。）