# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの現状（リポジトリ内のスクリプト・モジュール群）から推測して作成された変更履歴です。

なお、パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に基づいています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。本リリースでは日本株自動売買システム「KabuSys」のコアユーティリティ群、実行/監視ランナー、ポートフォリオ構築ロジック、設定管理ツール、解析用スクリプトなどの基盤機能を提供します。

### Added
- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカクライアント生成（paper_trading 時は MockBrokerClient を利用する想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止制御は data/stop_requested.flag により行い、実行 PID を data/execution.pid に出力。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用してデータを記録（環境に依存しない）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理・検証ツール
  - config.py
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - 複雑な .env のパース（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い）に対応。
    - Settings クラスで各種設定値（DB パス、API トークン、閾値など）をプロパティ経由で提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の検証ロジックを搭載。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - J-Quants トークン、kabu API パスワード、DB パス、ログレベル、Kill Switch の初期値を設定可能。
    - 既存 .env の読み込み・Enter による再利用、シークレット値のマスク表示、保存確認をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検査する CLI。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、YAML パーサ（PyYAML）存在チェック、KABUSYS_ENV=live 時の追加ガード等を実施。
    - --strict オプションで警告を失敗扱いにする機能を提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補銘柄選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を提供。
    - スコア全0時のフォールバック挙動をログ警告とともに実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - ポジションサイズ決定ロジック（calc_position_sizes）。
    - allocation_method=("risk_based"|"equal"|"score") をサポート。
    - 単元株数（lot_size）での丸め、per-position 上限・aggregate cap、cost_buffer を考慮したスケーリングと残差処理を実装。

- 分析 / レポートツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。
    - 日付レンジ指定（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し Pass/Fail 判定を行う（閾値はソース内定数）。
    - P95 算出、NULL / データ無し時の頑健な取り扱いを実装。

- 研究用モジュール（基盤）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組み（モメンタム等の定義、期間定数、calc_momentum の実装開始）。
    - prices_daily / raw_financials テーブル参照で処理する設計。

- ユーティリティ
  - utils/logging_setup.py
    - 全アプリ共通のログ初期化ユーティリティ。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler）でのファイル出力を設定。
    - ログディレクトリ自動作成、ローテーション期間（30 日）を設定。
    - LOG_LEVEL / LOG_DIR の環境変数を尊重。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（set_process_priority）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を提供。
    - Windows / POSIX(nice) の両対応とアクセス拒否時のフォールバックログを実装。

- DB / 分析基盤
  - DuckDB と SQLite の併用を前提に設計。主要ランナーで両接続を確立し、monitoring 用テーブルの初期化処理（init_monitoring_db）が呼ばれる。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（公開コードから推測できる変更点はなし）

---

注記:
- 実装の多くは「エンジン周辺の起動・設定・監視」「ポートフォリオ構築ロジック」「運用支援ツール（検証・ウィザード）」に集中しています。実際のブローカ接続、戦略のシグナル生成、ExecutionEngine の内部実装詳細、monitoring の各テーブル定義などは別モジュール（execution/*, monitoring/* 等）に依存しますが、本リリースではそれらの統合ポイントとユーティリティが整備されています。
- 本 CHANGELOG はソースコードの内容に基づき推測して作成したため、実際のリリースノートや企画意図と差異がある可能性があります。必要に応じて修正してください。