# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このリポジトリの現状のコードベース（__version__ = 0.1.0）から推測して、初回リリースの変更履歴を作成しました。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21
初回リリース。システムの起動スクリプト、設定管理、検証・ウィザード、ポートフォリオ構築ロジック、実行/監視用ユーティリティ、および検証ツールを含む日本株自動売買システムの基盤を提供します。

### Added
- 全体
  - パッケージ初期化: バージョン情報を設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db など）に記録して本番 DB と分離。
    - プロセス優先度設定、高優先度で起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポートし、デーモンスレッドで ExecutionEngine を実行・停止可能。
    - 依存コンポーネント（BrokerClient、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てと既定値を実装。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env 自動ロード（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 必須・任意の環境変数取得、型チェック、列挙型チェック（KABUSYS_ENV、LOG_LEVEL 等）。
    - DB パス、PID/kill flag パス、閾値（CPU/MEM/DISK）、paper_trading 関連設定（PAPER_FILL_MODE の検証等）を提供。
    - settings = Settings() のグローバルオブジェクトを提供。

  - 設定ウィザード / 検証 CLI
    - config_setup: .env の対話式ウィザードを追加（src/kabusys/config_setup.py）。
      - 標準項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 等）を対話的に作成・更新し .env を出力。
      - シークレットのマスク表示、入力キャンセル対応、既存 .env の読み込みと再利用をサポート。
    - validate_config: 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）。
      - KABUSYS_ENV=live 時のガードチェック（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告等）。
      - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルをスコア降順に選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア総和が 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限適用（既存保有と当日売却予定を考慮）。unknown セクター扱いは除外しない。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear + 未知はフォールバック）を提供。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算、lot_size（単元）丸め、per-position と aggregate のキャップ、cost_buffer による保守的推定、スケールダウンと残差補正ロジックを実装。

- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 接続を利用したファクター計算の枠組みを追加（モメンタム、MA200乖離、ATR、出来高系、Value 指標等を想定）。（prices_daily / raw_financials テーブル参照）

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等を集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値（稼働率 99%、成功率 90% 等）を採用し、日付レンジフィルタと --db オプションをサポート。

- 監視 DB 初期化
  - monitoring.monitoring_db モジュール経由で監視用テーブルの初期化を保証する呼び出しを追加（run_execution/run_monitoring で init_monitoring_db を呼称）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリ共通のログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時にはファイル出力をスキップして継続。
    - LOG_LEVEL / LOG_DIR の解決順序、重複ハンドラ防止、30日分バックアップなどを実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）向けの既定値、権限不足時の警告ハンドリングを実装。

### Changed
- （初回リリースのため差分履歴なし）  
  - 将来のリリースで config/ YAML や DB スキーマ変更時は validate_config と init_monitoring_db を更新する想定。

### Fixed
- （初回リリース）  
  - サンプル実装における堅牢性考慮:
    - MONITOR_POLL_INTERVAL の不正値時に警告してデフォルトを使う処理を実装（run_monitoring）。
    - .env パースロジックで引用符やエスケープ、コメントの扱いを細かく処理（config._parse_env_line）。
    - ログディレクトリの作成失敗やファイルハンドラ生成失敗を許容するフォールバック処理を実装。

### Security
- 環境変数の取り扱い:
  - シークレット値（J-Quants トークン、KABU API パスワード等）は .env に保存する設計。config_setup は .env を生成するが、ファイルの Git コミット禁止（ヘッダに注意喚起）を明記。
  - settings._require により必須環境変数の未設定を起動時に検出して明示的にエラーにする。

### Notes / Implementation Details
- Paper Trading と Live の DB は完全分離する設計（Settings.paper_sqlite_path を使用）。
- ExecutionEngine はスレッドで稼働し、停止フラグの検知で安全に停止する（run_execution）。
- Portfolio モジュールは純粋関数（副作用なし）で設計され、単体テストが容易。
- DuckDB は分析用に使用。prices_daily / raw_financials 等のテーブルを前提としている。
- 一部モジュール（例: research.calc_momentum）は長文の計算ロジックを含むため、将来的に追加的検証・最適化が望まれる。

---

今後のリリースでは、以下の要素が想定されます:
- ExecutionEngine / BrokerClient の具象実装（実発注ロジック、Mock と Live の切替テスト）
- モニタリング・アラート（LINE 通知）連携の実装
- config/*.yaml のテンプレートとデフォルトコンテンツの追加
- 単体テスト・CI 設定の追加

（この CHANGELOG はコードから推測して作成したものであり、実際の開発履歴とは差異がある可能性があります。）