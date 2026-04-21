# Changelog

すべての重要な変更をここに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

最新の変更は一番上に置かれます。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回公開リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 実行・監視系エントリポイント
  - run_execution: ExecutionEngine を起動するスクリプト。プロセス優先度設定、DB接続、ブローカークライアント生成、OrderManager/RiskManager/Reconciler の組み立て、エンジンのスレッド実行と停止フラグ対応を実装。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と完全に分離する挙動をサポート。
    - 起動時に停止フラグ（data/stop_requested.flag）を検知すると起動を中止。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視 DB は本番 PATH を使う）。
    - 停止フラグ検知、例外ハンドリング、DB接続のクリーンアップ処理を実装。

- 設定管理と支援ツール
  - config.Settings: 環境変数から各種設定を取得するクラスを実装。J-Quants / kabuAPI / DB パス / ペーパートレード設定 / 監視閾値 / ログレベル等を取得可能。
    - env 値の検証（KABUSYS_ENV, LOG_LEVEL など）と helper プロパティ（is_live, is_paper, is_dev）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH のサポート。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索し、.env/.env.local を自動読み込み（OS 環境変数は保護）する仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - シークレット項目はマスク表示、選択肢のバリデーション、保存前の確認を実装。
  - validate_config: .env と config/*.yaml の検証 CLI を提供。
    - 必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML の存在／パースチェック（PyYAML が無ければスキップ）、本番環境向けのガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）等を実装。
    - --strict オプションで警告をエラー扱いにする機能を提供。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベル・ログディレクトリ解決順をサポート。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリーンアップ処理を行い二重設定を防止。
  - utils.process_priority:
    - Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定する機能を提供（psutil 利用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告ログを出して安全にスキップする実装。

- ポートフォリオ構築とポジション決定（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコア 0 の場合は等配分へフォールバック）を提供。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、上限超過セクターの新規候補を除外（unknown セクターは対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（利用可能現金）を考慮してスケールダウン。cost_buffer を用いた保守的見積りと、比例スケーリング後の残差配分ロジックを実装。

- Execution / Risk / Order コンポーネント（起動スクリプトから組み立てられる）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（RiskConfig）といった実行系コンポーネントを統合して起動できる構成。

- 監視・レポート機能
  - monitoring 側インフラ（monitoring_db の初期化、SystemMonitor 呼び出し）を実装。
  - tools.paper_verification_report:
    - ペーパートレード用 DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して検証レポートを生成。
    - P95 計算ユーティリティ、期間フィルタ、閾値に基づく PASS/FAIL 判定を提供（稼働率/成功率/送信率/レイテンシの閾値を定義）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- robust .env パース機能を実装:
  - クォートされた値内のバックスラッシュエスケープ、閉じクォートの検出、インラインコメントの無視などを正しく扱うようにした。
  - export KEY=val 形式のサポート、コメント扱いの細かいルール（# の前の空白によるコメント識別）を実装。

### Removed
- （初回リリースのため該当なし）

### Notes / Known limitations / TODO
- research.factor_research モジュールは設計・定義済み（モメンタム等のファクター計算）だが、提供されたソースは途中で切れているため一部実装が未確認です。
- position_sizing の price フォールバック（price が欠損した場合の扱い）や銘柄別 lot_size の拡張は TODO コメントとして残しています。
- monitor/engine の細かい実行ロジック（SystemMonitor.check_once, ExecutionEngine.run_session など）はこの CHANGELOG の対象ファイルでは実装の組み立てが確認できるが、内部アルゴリズムの詳細や副作用は別ドキュメントでの確認を推奨します。

---

リリースに関する要望や、不足している変更点（例えばリファクタリングやバグ修正等）があれば、該当箇所のソースや差分を提示してください。提示に基づき CHANGELOG を更新します。