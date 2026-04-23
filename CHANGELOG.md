# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した変更履歴です。

フォーマット:
- Unreleased — 開発中の変更
- 0.1.0 — 初回リリース（推定）

## [Unreleased]
### Changed
- 環境変数の読み込みやログ設定の堅牢化（.env 読み込み失敗時の警告、ログディレクトリ作成失敗時にコンソール出力で継続する挙動など）。
- process_priority / CPU affinity のエラー処理を強化し、未対応 OS や権限不足時に警告を出して処理をスキップするように変更。

### Fixed
- .env パーサーのクォート・エスケープ処理およびインラインコメント扱いの微調整（複雑な .env 値の取り扱い改善）。

> 注: Unreleased はコードから推測される継続的改善項目を含みます。

---

## [0.1.0] - 2026-04-23
初回公開リリース（コードベースから推測）。以下はこのリリースで導入された主要機能・修正点です。

### Added
- 基本アプリケーション構造
  - パッケージ `kabusys` とサブパッケージ（execution, monitoring, portfolio, research, tools, utils 等）を追加。
  - バージョン情報: `__version__ = "0.1.0"` を設定。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を使って稼動環境に応じたブローカークライアントを生成（モック/本番の切替）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による外部停止検知を実装。
    - 起動時に process priority を "high" に設定する処理を実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する（監視テーブルの初期化処理含む）。
    - 停止フラグ（data/stop_requested.flag）検知でループを停止。

- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - よく使う設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を対話的に入力可能。
    - 保存前に確認プロンプトを表示し、.env を上書き保存。
  - validate_config.py
    - .env と config/*.yaml（存在する場合）の事前検証ツール。
    - 必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML がインストールされている場合）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- 環境設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - .env / .env.local の読み込み順序（OS 環境変数を保護しつつ上書き制御）。
    - .env のパーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - Settings クラスで各種設定値（DB パス、各 API トークン、監視閾値、env 判定ユーティリティ等）をプロパティとして提供。
    - PAPER_FILL_MODE 等の値検証（有効値チェック）を実施。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デイリーローテーション）を設定するユーティリティ。
    - LOG_DIR/LOG_LEVEL の解決ルールを実装、既存ハンドラのクリーンアップを含む。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX 系を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。
    - CPU affinity 設定関数 set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコア合計が 0 の場合のフォールバック（等配分）やタイブレークのロジックを含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - "unknown" セクターの扱いやレジーム別乗数（bull/neutral/bear）の仕様を明記。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（risk_based / equal / score の allocation_method をサポート）。
    - 1銘柄上限、lot_size（単元株）丸め、aggregate cap（利用可能現金でスケールダウン）や cost_buffer（手数料/スリッページ見積）を実装。
    - スケーリング時の残差処理（fractional_remainder に基づく追加配分）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity などのファクターを計算する設計（prices_daily / raw_financials を参照する仕様を明記）。
    - 計算ウィンドウやパラメータ（例: MA200、ATR 期間、モメンタム期間等）を定数として定義。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite データベース（デフォルト: data/paper_trading.db）からレポートを出力する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、しきい値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションをサポート。

- DuckDB / SQLite 連携
  - 実行系・監視系は SQLite（監視 / paper_trading）および DuckDB（分析用）に接続する実装を追加。

### Changed
- 主要起動スクリプト（execution, monitoring）は起動直後にプロセス優先度を High に設定するよう標準化。
- run_execution は paper_trading モード時に専用 DB を使用して本番 DB とデータを完全分離する挙動を採用。

### Fixed
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能とし、0 以下の不正値に対してデフォルトへフォールバックする安全処理を追加。
- 各種 DB 初期化（監視テーブルの作成）は冪等に実行されるよう init_monitoring_db を呼び出す。

### Security
- .env ファイル生成ウィザードの出力で「.env は絶対に Git にコミットしないこと」を明記。

### Documentation / UX
- 各モジュールに日本語の docstring を充実させ、設計意図や使用例、引数仕様・戻り値仕様を明記。
- CLI ツール（validate_config, config_setup, paper_verification_report 等）に使い方コメントと引数説明を追加。

---

注: 上記は提供されたソースコードから推測してまとめた CHANGELOG です。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて差し替えてください。