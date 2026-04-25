# Changelog

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。  
このファイルは、コードベースから推測した初期リリースの機能と変更点をまとめたものです。

全体方針:
- バージョンはパッケージ定義 (kabusys.__version__ = "0.1.0") に合わせて最初の公開リリースを 0.1.0 としています。
- 日付はこの生成日を使用しています。

## [0.1.0] - 2026-04-25
### Added
- 基本アーキテクチャ / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用する分離を実装。
    - BrokerClientFactory を介して実際のブローカークライアント / モックを選択。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による外部停止シグナルをサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - PID ファイルへの記録と安全なシャットダウンのロジックを提供。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する仕様。
    - stop flag（data/stop_requested.flag）検出、例外捕捉、最終的な DB クローズ処理を含む堅牢なループ。

- 設定管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数を保護）。
    - 複雑な .env パーサを実装（export 形式、クォート・エスケープ、インラインコメント処理など）。
    - Settings クラスで各種設定値（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 設定等）を型付きで提供。
    - PAPER_FILL_MODE 等の値検証・バリデーションを実装。
  - config_setup.py: 対話式 .env 生成ウィザードを追加。
    - 複数項目の入力支援（シークレット入力の取り扱い、既存 .env の読み込み・再利用、保存）
    - .env のテンプレート書き込みを実装（Git にコミットしない旨の注記付き）。

- 設定検証ツール
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在チェックと（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加の注意喚起（LINE 通知、KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて、ログの一元管理を実現。
    - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
    - 環境変数 LOG_LEVEL / LOG_DIR の扱いをサポート。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差異を吸収（psutil を使用。権限不足時は警告してスキップ）。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコア全て 0 の場合のフォールバック挙動をログで通知。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の適用（既存ポジションを考慮、売却予定は除外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数の算出（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じて発注株数を算出（risk_based, equal, score）。
    - lot_size（単元）丸め、per-position と aggregate の上限調整、available_cash によるスケールダウン、cost_buffer の適用などを実装。
    - 不足データ（価格欠損等）に対するスキップとログ出力の扱い。

- 監視・モニタリング関連
  - monitoring パッケージ用の DB 初期化（init_monitoring_db の参照箇所が存在）。run_monitoring/run_execution から冪等に監視テーブルを初期化。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI を追加。
    - 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）を計算して判定（PASS/FAIL）。
    - P95 計算や日付フィルタ、DB 存在チェック等を実装。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム、ボラティリティ、流動性、バリュー等のファクターを DuckDB の prices_daily / raw_financials テーブルに基づき計算する設計。モメンタム計算関数の雛形（calc_momentum）を追加（未完部分あり）。

- パッケージ初期化
  - __init__.py にてパッケージ名とバージョン定義（__version__ = "0.1.0"）を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / ユーザー向け注意事項
- .env 自動読み込みはデフォルトで有効。テストや特殊環境で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します（デフォルトは 0）。
- run_execution / run_monitoring は外部ファイル（data/stop_requested.flag や data/*.pid）によるプロセス制御を行うため、適切なファイル操作権限とデータディレクトリの準備を行ってください。
- position_sizing 等のアルゴリズムは単元（lot_size）が固定であることを前提としているため、将来的に銘柄別単元対応が必要な場合は拡張を検討してください（コード内に TODO を記載）。
- research/factor_research の一部関数は実装途中（ファイル末尾が途中で切れている）が、設計方針と入出力仕様は明記済みです。実運用前に完全実装・テストが必要です。

---

今後のリリースでは以下を追加することが想定されます:
- research/factor_research の完全実装とテスト
- ExecutionEngine / BrokerClient 実装詳細の注記（API エラーハンドリング、リトライ、フェイルセーフ）
- 単体テストと CI 設定、ドキュメント（Usage, Configuration examples）
- 銘柄ごとの lot_size 対応、スリッページ／手数料モデルの拡張

（以上）