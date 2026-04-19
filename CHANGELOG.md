# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般方針:
- バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。
- 日付はこのリリースの作成日です。

--------------------------------------------------------------------------------

## [Unreleased]

## [0.1.0] - 2026-04-19
### Added
- 初期リリースを追加。以下の主要機能・モジュールを実装。
- CLI / 起動スクリプト
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）の検知でループ終了。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine の起動・停止処理を実装。
    - 停止フラグと PID ファイル管理、別スレッドでのエンジン実行をサポート。
  - kabusys.validate_config: 設定検証 CLI を追加。
    - .env と config/*.yaml の存在・基本整合性チェック（YAML パーサが無ければパースチェックをスキップ）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等の妥当性検証、live 環境向けガード（LINE 通知設定や Kill Switch 設定の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - kabusys.config_setup: .env 作成・更新の対話式ウィザードを追加。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）。
    - 既存 .env の読み込み、入力プロンプト、確認後に .env を生成・上書き。
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出し PASS/FAIL を判定。
    - 各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）を実装。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。

- 設定管理 (kabusys.config)
  - .env 自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env / .env.local の読み込みルール（OS 環境変数を保護、.env.local は override=True）。
  - .env の行パーサを強化: export プレフィックス、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを実装し、多数のプロパティを提供:
    - J-Quants / kabu API / LINE / DB パス（duckdb/sqlite/paper）/ PID/KILL フラグ /閾値等
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - env 値の妥当性チェック（development/paper_trading/live）
    - ヘルパー: is_live / is_paper / is_dev

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: スコア降順選択（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価比率に基づき新規候補を除外）。unknown セクターは制約対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、未知時は 1.0 フォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、1 銘柄上限・aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、残余の再配分ロジックを実装。

- ユーティリティ
  - logging_setup: 統一的なロギング設定ユーティリティを追加。
    - stdout (StreamHandler) と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_DIR / LOG_LEVEL の環境変数対応、ログディレクトリ自動作成（失敗時はファイル出力をスキップ）。
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - set_process_priority(level): Windows / POSIX に対応（psutil を使用）。アクセス拒否等は警告にフォールバック。
    - set_cpu_affinity(cpu_count): 指定コア数へのピンニング（失敗時は警告）。

- monitoring DB 初期化ヘルパーの呼び出しを追加（起動スクリプト内で冪等に監視テーブルを保証）。

- research.factor_research: ファクター計算モジュールの骨組みを追加（Momentum 等の計算方針・定数、calc_momentum の導入開始）。※ファイル末尾で計算ロジックが途中で切れているが、設計としてファクター計算の方針を実装。

### Changed
- ロギング設定:
  - 既存ハンドラを明示的に flush/close してから削除するように変更（再起動時の重複ログ防止）。
  - StreamHandler を stdout に固定（cron/Task Scheduler との相性を考慮）。
- .env 自動ロードの挙動:
  - OS 環境変数を保護するため protected セットを導入し、.env.local の override 時も OS 環境変数は上書きされないようにした。
  - プロジェクトルートが検出できない場合は自動ロードをスキップ。

### Fixed
- .env パーサの不正な行処理や引用符・エスケープ処理の不備を改善し、一般的な .env の記述に耐性を強化。
- process_priority が存在しない OS 定数にアクセスしてモジュールロードで失敗する問題を getattr フォールバックで回避。

### Security / Safety
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定するための呼び出しを行う（set_process_priority）。権限不足時は警告を出してスキップする。
- run_execution では paper_trading 時に DB を完全分離（paper_sqlite_path）することで、本番データと分離された検証環境を保証。

### Documentation / UX
- config_setup による .env ウィザードと validate_config による事前検証を提供することで、誤設定による本番事故のリスク低減を図る。
- paper_verification_report によりペーパートレード結果の定量的検証が可能。

--------------------------------------------------------------------------------

注意:
- 初期リリースであるため、内部 API（特に research モジュールや ExecutionEngine 周り）は今後変更される可能性があります。
- config_setup が生成する .env は機密情報を含むため、絶対にリポジトリにコミットしないでください（README / ファイルヘッダにも注記あり）。
- 今後のリリースでは tests、ドキュメント、さらに詳細な監視指標・アラート連携（LINE 通知等）の追加を予定しています。

--------------------------------------------------------------------------------

(CHANGELOG は手動でメンテナンスしてください。)