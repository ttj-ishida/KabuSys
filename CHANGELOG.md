# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
バージョン番号はパッケージの `kabusys.__version__` に合わせています。

※この CHANGELOG はコードベースの内容から機能・振る舞いを推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース。以下の主要機能とユーティリティを含みます。

### Added
- 基本構成・起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。  
    - 起動時にプロセス優先度を「high」に設定。  
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と完全分離。  
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。  
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。停止フラグ検知で安全にループ終了。

- 設定・環境管理
  - config: 環境変数／.env 読み込み・設定管理モジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml）。  
    - `.env` / `.env.local` の自動ロード（OS 環境変数を保護する保護キー機構）。  
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、env/log_level 判定、paper_trading 関連設定等）を提供。  
    - `PAPER_FILL_MODE` の検証（有効値チェック）や `KABUSYS_ENV` の検証を実装。  
  - config_setup: .env を対話式で生成／更新するウィザード CLI を追加。  
    - 秘匿項目は入力時にマスク。既存 .env の読み込み、デフォルト提示、確認後ファイル保存。  
  - validate_config: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および YAML パース検証（PyYAML が無ければスキップ）。  
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。  
    - スコア全てが 0 の場合は等金額配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。  
    - apply_sector_cap は既存保有を考慮して過剰セクターの新規候補を除外。`unknown` セクターは除外対象外。  
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対応し、未知レジームはログ警告のうえ 1.0 でフォールバック。
  - portfolio.position_sizing: ポジションサイズ計算（calc_position_sizes）を実装。  
    - allocation_method に `risk_based` / `equal` / `score` をサポート。  
    - 損切り率・リスク許容率に基づくリスクベース配置、単元株（lot_size）での丸め、1 銘柄上限とアグリゲートキャップ（available_cash）に応じたスケーリング、コストバッファの考慮などを実装。  
    - 価格欠損時のスキップやログ出力など実用上の保護処理を含む。

- 監視・検証ツール
  - monitoring DB 初期化用ユーティリティ（init_monitoring_db を参照する起動処理に組み込み）。  
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。  
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定を出力。  
    - デフォルト DB パスは `data/paper_trading.db`。期間フィルタ（--from / --to）対応。閾値はソース中に定義（稼働率 >= 99% 等）。

- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。  
    - stdout への StreamHandler（stdout を使用）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラのクリアを行い二重設定を防止。LOG_DIR / LOG_LEVEL の上書き順を明確に実装。  
    - ログディレクトリ作成失敗時はファイル出力をスキップする冗長性を追加。
  - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）に対応。アクセス権限不足や未対応 OS は警告でスキップ。  
    - set_cpu_affinity で最初の N コアに固定する機能を提供。

- リサーチ基盤（骨格）
  - research.factor_research: モメンタム等のファクター計算モジュールの骨格を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する方針）。  
    - 設計として、モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性などを計算予定。現時点では calc_momentum の実装開始の痕跡あり（未完）。  

### Changed
- 初期リリースのため履歴なし。

### Fixed
- 初期リリースのため履歴なし。

### Security
- 初版のため既知のセキュリティ修正なし。

---

開発者向け補足（コードベースから推測）
- モジュール設計は「本番環境とペーパートレードの明確な分離」「外部 API（発注系）に影響を与えないリサーチ領域の分離」を意図している。  
- .env の自動ロードは OS 環境変数を保護する仕組み（protected set）を持ち、テスト用に自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグが存在する。  
- ログは stdout を標準出力に出す設計（cron/Task Scheduler からの起動を意識）。  
- Execution/Risk 周りのデフォルトパラメータ（max_position_pct、max_utilization、circuit_breaker 等）はコード中に設定済みで、起動時に broker.get_available_cash() を使って初期資金を反映する設計。

もしもっと詳細な変更点や各モジュールごとの実装ノート（例: API、設定キー一覧、CLI 使用例）を CHANGELOG に含めたい場合は指示してください。