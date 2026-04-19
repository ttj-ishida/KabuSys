# Changelog

すべての変更は Keep a Changelog の形式に従います。  
慣例: 変更内容は日本語で要約しています。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期リリース。KabuSys 自動売買フレームワークのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツールを追加。
  - DuckDB / SQLite を用いたデータ処理基盤を導入（分析用に DuckDB、監視・履歴用に SQLite を想定）。

- 起動スクリプト / 実行系
  - run_execution: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV による動作切替対応（paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ完全分離して記録）。
    - プロセス優先度を起動時に設定（高優先度）。
    - 実行中の停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御を実装。
    - duckdb 接続を ExecutionEngine に渡して分析データ処理と併用可能。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計（監視 DB を環境で分離しない意図的仕様）。
    - 停止フラグ（data/stop_requested.flag）検知でループを安全に終了。
    - check_once() 実行時の例外を捕捉してログ出力し、次ポーリングへ継続。

- 設定関連
  - config.Settings: 環境変数管理クラスを実装。各種設定（API トークン、DB パス、監視閾値、環境フラグ等）を lazily に取得するプロパティ群を提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を探索）を検出し、OS 環境変数 > .env.local > .env の優先順位で自動読み込みを行う機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーの強化: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いなどを考慮して安全にパース。

- 設定補助 CLI
  - config_setup: 対話式ウィザードで .env を新規作成・更新する CLI を追加。シークレット項目はマスク表示、既存値の再利用、保存前の確認ダイアログを提供。
  - validate_config: 起動前チェック用 CLI を追加。必須環境変数やパス、config/*.yaml の存在と YAML パース（PyYAML がある場合）を検証。--strict で警告を失敗扱いにできる。

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定と等分／スコア加重の重み計算を追加（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing: 複数の配分方式（risk_based, equal, score）に対応した株数計算ロジックを追加。  
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（スリッページ/手数料考慮）、残余キャッシュを用いた再配分ロジックを実装。

- 監視・検証ツール
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を追加（冪等にテーブルを保証）。
  - tools/paper_verification_report: ペーパートレード履歴から検証レポートを生成する CLI を追加。期間指定（--from/--to）、DB 指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。以下の指標を出力:
    - システム稼働率（uptime）
    - 注文成功率（fill_rate）・送信率（send_rate）
    - リスク却下数
    - API レイテンシ（avg, max, P95）
    - PASS/FAIL 判定（定義済み閾値による）

- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。既存ハンドラはクリアすることで二重登録を回避。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足や未対応環境時は警告を出してフォールバック。

- 研究・計算
  - research.factor_research: モメンタム・ボラティリティ・バリュー等ファクター計算の基礎を追加（DuckDB を介した prices_daily / raw_financials 参照を想定）。（ファイルは実装継続中、設計ドキュメントに沿った関数群を準備）

### Changed
- ログ
  - ログのデフォルト出力先として stdout を採用（StreamHandler）。cron/Task Scheduler など外部環境での標準出力リダイレクトを想定。
  - ログレベル解決を関数引数・環境変数・デフォルトの順で行うよう統一。

- データベースの取り扱い
  - run_execution は paper_trading 環境時に paper_sqlite_path を使いデータを完全分離（本番 sqlite_path と分離）。一方、run_monitoring は環境に依存せず監視用 sqlite_path を使用する仕様とした（監視データを一元化する意図）。

- .env 読み込み
  - OS 環境変数は保護（protected）され、自動ロード時の上書きを制御。`.env.local` は `.env` の設定を上書き可能だが OS 変数は上書かない。

### Fixed
- 環境変数パースの堅牢化
  - MONITOR_POLL_INTERVAL が不正な値（非整数・0以下など）の場合は警告を出しデフォルト（60秒）にフォールバックするように修正。time.sleep に不正値が渡らないよう保護。

- 例外処理強化
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもループ全体が停止しないように捕捉してログに出力、次ポーリングへ継続するようにした。
  - run_execution/run_monitoring 共に最終的に DB 接続（SQLite / DuckDB）を確実にクローズする finally ブロックを追加。

- validate_config の堅牢性
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出すように変更。config/*.yaml が存在しない場合は警告を出す（生成スクリプトの案内メッセージ付き）。

### Notes / その他
- 現在のバージョンは 0.1.0（初期機能セット）。以下は今後の改善候補:
  - research.factor_research の完成（ファクター計算関数の実装完了）。
  - 銘柄別の lot_size マスタ化、取引コストモデル強化、価格フォールバック戦略（前日終値等）。
  - テストカバレッジの追加（特に資金配分・スケーリングロジック、.env パーサーの境界ケース）。
  - 実行環境（特に権限周り）での process_priority / cpu_affinity の挙動確認とドキュメント化。

---

当 CHANGELOG はコードベースの内容から推測して作成しています。詳細な設計意図や将来の変更はリポジトリの README / ドキュメントを参照してください。