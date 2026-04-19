# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はソースコードの最新更新日を基にしています。

※ 本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートは開発履歴に合わせて調整してください。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-19

初回公開リリース。本リポジトリは日本株自動売買システム "KabuSys" のコアユーティリティ群と起動スクリプトを含みます。

### Added
- 基本設定・環境変数管理
  - .env ファイルの自動読み込み機能を追加（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env 行パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
  - Settings クラスを導入し、アプリケーション設定（DBパス、API トークン、環境種別、各閾値等）をプロパティ経由で提供。
  - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）、KABUSYS_ENV の有効値検証、LOG_LEVEL の検証などを実装。

- 起動 / デプロイ支援ツール
  - config_setup: .env を対話式に作成・更新するウィザード CLI を追加（python -m kabusys.config_setup）。
  - validate_config: .env や config/*.yaml の事前検証 CLI を追加（python -m kabusys.validate_config）。--strict オプションで警告を FAIL 扱い可能。
  - ログ出力の一貫化ユーティリティ setup_logging を追加。stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに統一的に設定。LOG_DIR / LOG_LEVEL の優先解決を実装。

- 実行系・監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定するフローを採用。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を利用する（本番 DB と分離）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用する点に注意。

- 実行補助ユーティリティ
  - process_priority: Windows/Linux/Mac を透過するプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）設定ユーティリティを追加。CPU affinity 設定関数も提供（p.cpu_affinity）。
  - ログ・PID・停止フラグ連携: data ディレクトリ内の stop_requested.flag / execution.pid などによる外部停止制御を標準的に使用。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等配分へフォールバックして WARNING を出力。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。regime による投下資金比率調整（bull/neutral/bear）を提供。
  - position_sizing: 株数計算ロジック calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）での丸め、コストバッファ（cost_buffer）を考慮した aggregate cap、利用可能現金に応じたスケーリング処理を含む。

- リサーチ / ファクター計算
  - research/factor_research モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials テーブルを参照してファクターを算出する設計）。モメンタムやMA200乖離、ATR、出来高指標等を想定した関数群の土台を用意（実装はファイル末尾に続く想定）。

- Paper Trading 検証ツール
  - tools/paper_verification_report: Paper Trading 用 SQLite を解析し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を行うレポートスクリプトを追加。閾値はソース内で定義（例: uptime >= 99%, fill_rate >= 90% 等）。コマンドライン引数で期間指定および DB パス上書きが可能。

- DB 統合
  - DuckDB と SQLite の両方を利用する設計を採用。監視用・履歴用の SQLite、分析用の DuckDB を並列で使用。

### Changed
- ロギングの既存ハンドラ再設定
  - setup_logging は既に存在するルートハンドラを一旦 flush/close/削除してから新たに設定する実装となり、二重ハンドラ登録を防止。

### Fixed
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメント処理などを正しく扱うよう改善。これにより .env の柔軟な記述がサポートされる。

### Security
- .env 取り扱い注意のドキュメント化
  - config_setup が生成する .env に対して「.env は絶対に Git にコミットしないこと」と明示。

### Notes / その他重要事項
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用監視 DB）を使用します。監視データを分離したい場合は設定に注意してください。
- Execution は paper_trading モードの際、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全に分離されます。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとしますが、権限不足や未対応プラットフォームでは警告を出してスキップします。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップします（警告）。
- calc_position_sizes 等の数値ロジックは lot_size 固定（現状 100）を前提としており、将来的に銘柄別単元対応を検討する旨の TODO コメントあり。

---

このリリースではシステムの起動／設定・監視・発注に関わる基盤機能と、ポートフォリオ構築・検証ツールのコアを実装しています。今後のリリースでは ExecutionEngine 本体・ブローカー実装・Strategy 実装・DuckDB の集計クエリ整備・追加テスト・ドキュメント強化などが想定されます。