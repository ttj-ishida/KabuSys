# KEEP A CHANGELOG — KabuSys

すべての注記は Keep a Changelog の形式に準拠して記載しています。  
この CHANGELOG はコードベース（src/ 配下の実装）から推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。システムの起動スクリプト、設定管理、ログ・プロセスユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツール、およびデータ処理（DuckDB/SQLite 統合）を収録。

### Added
- 全体
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - 実行用エントリ:
    - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、Broker クライアント生成、ExecutionEngine の起動と停止フラグ監視を実装。
      - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）に分離して記録。
      - 実行中の PID 管理用の pid ファイル（data/execution.pid）をサポート。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
      - 監視用途の DB は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視データの一元化）。
      - 停止フラグ（data/stop_requested.flag）の存在検知で安全にループを終了。
- 設定管理
  - Settings クラス（kabusys.config）を追加：
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を読み込む）。
    - OS 環境変数を保護して .env.local の上書きを制御する仕組みを実装。
    - 多数の設定プロパティを提供（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、paper_trading パス、監視閾値、ログレベル、実行環境判定 helper 等）。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
  - .env 対話式ウィザード（kabusys.config_setup）を追加：
    - 初期 .env の作成・更新を支援する対話式 CLI（secret マスク表示、選択肢・デフォルト管理、.env 出力）。
  - 設定検証 CLI（kabusys.validate_config）を追加：
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL のチェック、DB パスの親ディレクトリ検査、config/*.yaml の有無と（PyYAML がある場合は）パースチェック、本番環境向けの追加ガード等。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。
- ロギング / プロセスユーティリティ
  - logging_setup: 統一的なログ初期化ユーティリティを追加。
    - stdout への StreamHandler を使用（cron 等で stdout を一本化しやすくするため）。
    - 日次ローテーションの TimedRotatingFileHandler を用いて logs/<app_name>.log を出力（30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの解決順（引数 > 環境変数 > デフォルト）。
  - process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加（psutil ベース）。
    - Windows / POSIX（Linux, macOS, FreeBSD）差を吸収。設定失敗時は警告ログでスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment:
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター比率を計算し、上限超過セクターの当日新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マップと未知レジームのフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes を実装。allocation_method に応じて発注株数を算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超過する場合のスケールダウン）を実装。
    - cost_buffer を考慮した保守的見積り、残余キャッシュによる lot 単位での追加配分ロジックを含む。
    - TODO: 将来的な銘柄別 lot_size 拡張のための注記あり。
- データ処理 / 解析
  - research.factor_research: DuckDB を使ったファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、流動性・バリュー系ファクターを想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH を受け取り、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定する（閾値をコード内に定義）。
    - 日付フィルタ（--from, --to）に対応。DB 存在チェック、各テーブルが無い場合のフォールバックを実装。

### Changed
- 設計上の決定
  - 監視（monitoring）は KABUSYS_ENV に関わらず監視用 DB（デフォルト: data/monitoring.db）を使用することで、環境分離が明確になるようにした（意図的な動作）。

### Fixed / Hardened behaviors
- 環境変数 / .env パーサ
  - export KEY=val 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの取り扱いを考慮した .env パーサを実装。無効行やコメント行を無視。
  - .env ロード時に OS 環境変数を保護（protected set）して意図しない上書きを防止。
- 起動ループ / 環境
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）に対してデフォルトへフォールバックし、警告ログを出力することで time.sleep 例外を回避。
  - run_execution / run_monitoring の停止フラグ（data/stop_requested.flag）検知により安全なシャットダウンを保証。
- ロギング
  - ログディレクトリ作成失敗時はファイルハンドラ生成をスキップしてコンソール出力のみで継続するフェイルセーフを実装。
- プロセス管理
  - psutil による優先度設定や CPU affinity 設定で AccessDenied / NotImplementedError 等をキャッチして警告しプロセス継続を保証。

### Known issues / Notes / TODO
- position_sizing: price が欠損（0.0）時のエクスポージャー過少見積りに関する注記あり。前日終値や取得原価をフォールバックする拡張が必要（TODO）。
- research.factor_research: ファイル末尾で実装が途中で切れている（calc_momentum の続きが未収録）。実際のファクター計算ロジックの完成が必要。
- 一部の機能は外部依存（psutil, duckdb, PyYAML など）あり、環境によっては機能が限定される。validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出す実装。
- paper_trading 用 DB と本番 DB の完全分離を設計しているが、運用上の注意（適切な環境変数設定、.env の管理）が必要。

### Security
- 本リリースではセキュリティ関連の修正は特になし。環境変数にシークレット（トークン・パスワード）を格納するため、.env の取り扱いや Git へのコミット禁止を README 等で明確にすることを推奨。

---

生成した CHANGELOG はコードベースの現在の状態から推測して作成しています。実運用での正確な差分履歴が必要な場合は Git のコミット履歴に基づく正式な CHANGELOG の作成を推奨します。必要であれば、コミット履歴から自動生成するテンプレートの案内や、各ファイルの実装に紐づくより詳細なリリースノート（変更点ごとのリスク・マイグレーション手順等）も作成できます。どの形式がよいか教えてください。