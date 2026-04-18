# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴（要約）です。

※ バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせて v0.1.0 を初期リリースとしています。

## [Unreleased]

（現在のスナップショットに基づく新機能・改善案や今後の注記をここに記載できます）

---

## [0.1.0] - 初期リリース
リリース日: 未設定（初版）

概要: KabuSys の基本的な実行基盤、設定管理ツール、ポートフォリオ構築ロジック、ユーティリティ群および検証ツールを含む初期実装。

### Added
- 全体
  - パッケージ化された日本株自動売買システム「KabuSys」の初期実装を追加。
  - パッケージメタ情報にバージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合にはペーパートレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient による分離動作をサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - stop フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid）に対応。
    - ExecutionEngine をスレッドで実行し、停止フラグ検知で安全に停止できる制御ループを実装。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てを行う。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は常に production 用 sqlite_path を使用する設計（環境にかかわらず本番の監視 DB を参照）。
    - stop フラグ検知でループを終了し、例外時にもログを出力して次回ポーリングで継続。

- 設定管理
  - src/kabusys/config.py: 設定取得モジュールを追加。
    - .env 自動読み込み（プロジェクトルートが検出できる場合のみ）: .env → .env.local の順でロード。OS 環境変数は保護して上書きされない。
    - .env のパース機能を強化（export PREFIX、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等に対応）。
    - Settings クラスを提供し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）をプロパティとして取得。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実施。
    - settings インスタンスをデフォルトでエクスポート。

  - src/kabusys/config_setup.py: 対話式 .env 作成／更新ウィザードを追加。
    - 各種設定項目（実行環境、API トークン、DB パス、ログレベル、Kill Switch 設定など）を対話的に入力し .env を生成。
    - 既存 .env の読み込み・再利用、秘密項目のマスク表示、保存確認をサポート。

  - src/kabusys/validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL のチェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML があれば）パース検証、本番環境向けの追加ガード（LINE 通知設定・Kill Switch の注意喚起）などを実行。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - シグナルの候補選択（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
    - スコア合計がゼロの場合は等金額配分へフォールバック。

  - src/kabusys/portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャーに基づき、新規候補をフィルタリング。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート、未知のレジームは 1.0 でフォールバック）。

  - src/kabusys/portfolio/position_sizing.py:
    - position size（発注株数）計算を実装。allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）を実装。
    - cost_buffer による手数料・スリッページ想定、残余キャッシュによる端数配分ロジックを実装。

  - src/kabusys/portfolio/__init__.py: 上記関数群のエクスポートを提供。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py:
    - 統一的なロギングセットアップ関数 setup_logging を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーへ設定。
    - LOG_DIR・LOG_LEVEL の解決順、ファイルハンドラ作成失敗時のフォールバックを実装。

  - src/kabusys/utils/process_priority.py:
    - プロセス優先度設定（set_process_priority）を追加。Windows（psutil の priority class）と POSIX（nice 値）に対応し、アクセス権限例外をハンドル。
    - CPU affinity 設定（set_cpu_affinity）を追加（最初の N コアに固定、例外は警告）。

- モニタリング DB 初期化
  - src/kabusys/monitoring/monitoring_db.py (参照されているがファイル本体はこのスナップショットに含まれない): 起動スクリプトから監視テーブルの初期化を行う init_monitoring_db を呼び出し、冪等的に監視テーブルを保証。

- 分析・検証ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計し PASS/FAIL を判定（閾値はソース内定数で定義）。
    - 日付範囲フィルタ、SQLite DB パスの引数/環境変数対応をサポート。

- リサーチ（部分実装）
  - src/kabusys/research/factor_research.py: ファクター計算モジュールを追加（モメンタム／ボラティリティ等の計算方針と定数を定義、calc_momentum の実装開始）。DuckDB を用いた prices_daily 参照を想定。

### Changed
- ロギング
  - すべての起動スクリプト・主要コンポーネントから共通の setup_logging を呼ぶことでログ設定を統一。

- DB の取り扱い
  - Execution は paper_trading 環境時に専用の SQLite を使用して完全に本番 DB と分離する設計に変更（Settings.paper_sqlite_path を使用）。
  - 監視（monitoring）は環境にかかわらず production 用 sqlite_path を使用する方針を明示。

### Fixed / Improved
- .env パーサーの堅牢化
  - exports の扱い、シングル／ダブルクォート値のエスケープ処理、インラインコメントの取り扱いを改善して .env の柔軟な記述に対応。
  - OS 環境変数を保護する protected パラメータを導入し、意図せぬ上書きを防止。

- 設定バリデーションの改善
  - Settings のプロパティで KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の妥当性チェックを導入。無効な値は ValueError を投げるようにして早期検出を可能にした。
  - validate_config CLI による起動前チェックを整備し、config/*.yaml の存在・パースチェック（PyYAML 利用時）や本番向けの注意喚起を追加。

- プロセス管理の堅牢性
  - process_priority の例外（AccessDenied 等）を捕捉して警告を出し、起動失敗を防止。
  - run_execution/run_monitoring の停止制御（stop flag と KeyboardInterrupt 処理）を堅牢化。

- ポジションサイズ計算の安全弁
  - price が欠損・ゼロのケースでのスキップ処理、aggregate cap 時のスケーリングと残差配分ロジックを実装し、極端なケースでの過剰オーダーを防止。

### Known issues / Notes
- src/kabusys/research/factor_research.py はこのスナップショットで途中までの実装（calc_momentum の実装継続が示唆）であり、完全実装は未完。
- monitoring_db.py の本体はこの一覧に含まれていないが、起動スクリプトから init_monitoring_db を呼び出しているため、監視テーブル定義が別ファイルに存在すると推測される。
- 一部コメントに TODO（価格フォールバック、lot_size の銘柄個別対応等）が残っているため、将来的な改善が想定される。

---

保持方針、付記:
- CHANGELOG は意図的に機能単位で要点を抜粋しています。実際のコミット履歴がある場合はコミットメッセージに基づく詳細な差分を併記することを推奨します。
- 今後のリリースでは Breaking Changes / Deprecated / Removed セクションが必要になった場合、Keep a Changelog のガイドラインに従って追加してください。