# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

全体方針:
- 日付はリリース相当の日付を使用しています（推測）。
- 各項目は実装された機能・改善・修正点をソースコードから推測して記載しています。

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン定義: src/kabusys/__init__.py に `__version__ = "0.1.0"` を設定。

- 環境設定・管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - os 環境変数 > .env.local > .env の優先順位で読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - 実装: src/kabusys/config.py
  - .env の行パーサを実装。クォート（シングル／ダブル）とバックスラッシュエスケープ、`export KEY=val` 形式、インラインコメント処理に対応。
    - 実装: src/kabusys/config.py
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 実行環境判定（development/paper_trading/live）などを提供。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などの Paper Trading 設定をサポート。

- 対話式環境設定ウィザードを追加
  - CLI: python -m kabusys.config_setup
  - .env の初期作成・更新を支援するウィザード。シークレット項目はマスク表示。
  - 実装: src/kabusys/config_setup.py

- 設定検証ツールを追加
  - CLI: python -m kabusys.validate_config
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの追加警告などを行う。
  - --strict オプションで警告を FAIL 扱いにできる。
  - 実装: src/kabusys/validate_config.py

- 実行エンジン起動スクリプトを追加
  - CLI スタイル起動スクリプト: src/kabusys/run_execution.py
  - Paper Trading 環境では MockBrokerClient を利用し、Paper 専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - プロセス優先度を最初に High に設定し、PID ファイル・停止フラグ（data/stop_requested.flag）をチェックして安全に停止可能。
  - ExecutionEngine のコンポーネント組み立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を行う。

- 監視（Monitoring）起動スクリプトを追加
  - CLI スタイル起動スクリプト: src/kabusys/run_monitoring.py
  - ポーリング間隔の上書き: 環境変数 MONITOR_POLL_INTERVAL（デフォルト: 60秒）。不正値に対するフォールバック処理を実装。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - 停止フラグファイル検知でループを退出する。

- 監視 DB 初期化ユーティリティを導入
  - 起動スクリプトから監視テーブルの初期化（冪等）を行う呼び出しを追加（init_monitoring_db を呼ぶ）。
  - ファイル: src/kabusys/monitoring/* （コードから参照）

- ロギングユーティリティを追加
  - setup_logging(app_name, log_dir, level) を実装。
  - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/, 30 日保持）をルートロガーに設定。既存ハンドラのクリア機能あり。
  - ファイル作成失敗時にファイルハンドラをスキップして stdout のみで継続する安全設計。
  - 実装: src/kabusys/utils/logging_setup.py

- プロセス優先度 / CPU affinity ユーティリティを追加
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows / POSIX の差分を吸収し psutil を利用。
  - 権限不足や未対応 OS の場合は警告を出してフォールバック。
  - 実装: src/kabusys/utils/process_priority.py

- ポートフォリオ構築モジュールを追加（純粋関数群）
  - 候補選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights
    - 実装: src/kabusys/portfolio/portfolio_builder.py
    - score が全て 0 の場合は等金額配分へフォールバック（警告あり）。
  - セクター集中制限とレジーム乗数: apply_sector_cap, calc_regime_multiplier
    - 実装: src/kabusys/portfolio/risk_adjustment.py
    - セクター不明 (unknown) の扱い、既存ポジションの除外（売却予定の除外）等をサポート。
    - レジーム乗数は bull/neutral/bear に対応し、未知値はフォールバックで 1.0（警告）。
  - 株数決定・リスク制限: calc_position_sizes
    - 実装: src/kabusys/portfolio/position_sizing.py
    - allocation_method による "risk_based" / "equal" / "score" の処理、単元（lot_size）丸め、ポートフォリオ合計の aggregate cap（利用可能現金に基づくスケーリング）や cost_buffer を考慮した保守的計算、端数取り扱いアルゴリズムを実装。

- Paper Trading 検証レポート生成ツールを追加
  - CLI: python -m kabusys.tools.paper_verification_report
  - 指定期間（--from / --to）や DB パス（--db）に対して、稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数などを集計して PASS/FAIL を判定するレポートを標準出力に出力。
  - 閾値（稼働率 99%、成立率 90% 等）を設定し、P95 はサンプルから計算する実装。
  - 実装: src/kabusys/tools/paper_verification_report.py

- ファクター計算（研究）モジュールの導入（部分実装）
  - DuckDB を使って prices_daily / raw_financials を参照しモメンタム等のファクター算出を行う設計。
  - 実装（冒頭部分）: src/kabusys/research/factor_research.py
  - （NOTE: ソースは途中で切れており、一部未完の可能性あり）

- DuckDB と SQLite の併用設計を導入
  - 分析用に DuckDB（kabusys.duckdb）、運用/監視用に SQLite（monitoring.db / paper_trading.db）をそれぞれ使用する構成を反映。

### Changed
- 実行・監視スクリプトの挙動強化
  - 実行開始時にプロセス優先度を "high" に設定する処理を共通して実行。
  - run_execution/run_monitoring が起動時に監視 DB テーブルの存在を保証するため init_monitoring_db を呼び出す。
  - run_execution は Paper Trading 時に別 DB を使用して本番 DB と分離するように設計。

- ログ出力の一貫化
  - 全スクリプトは setup_logging() を呼び出して統一されたログ設定を使用するよう変更。

- .env 書込みフォーマットの標準化
  - config_setup の _write_env() により .env の項目と順序が固定化され、README 等と整合しやすくした。

### Fixed
- MONITOR_POLL_INTERVAL の不正値対処
  - 環境変数 MONITOR_POLL_INTERVAL に不適切な値（非整数や 0 以下）が設定された場合、警告ログを出してデフォルト（60秒）にフォールバックするように修正。
  - 実装: src/kabusys/run_monitoring.py::_get_poll_interval

- 停止フラグ / PID の扱いの安全化
  - 起動時およびループ内で data/stop_requested.flag（および data/execution.pid など）をチェックし、既に停止フラグが立っている場合は起動を取りやめる・早期終了する挙動を追加。
  - 実装: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py

- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合、ファイルハンドラを作らず stdout のみで動作を継続するように修正（例外耐性の向上）。
  - 実装: src/kabusys/utils/logging_setup.py

- プロセス優先度設定時の例外ハンドリング強化
  - psutil の権限不足や未実装例外を捕捉し警告を出して処理を継続するようにした。
  - 実装: src/kabusys/utils/process_priority.py

### Security
- シークレット値の取り扱い改善
  - config_setup のウィザードでシークレット項目はマスク表示して表示漏洩を防止（ターミナル表示上）。
  - Settings クラスは必須環境変数未設定時に ValueError を投げて明示的に失敗させるため、起動ミスによる認証情報漏れや欠落を早期に検出。

### Notes / Known limitations
- research/factor_research.py は一部未完の箇所（ファイル終端で切れている）を含む。ファクター計算ロジックは引き続き実装・テストが必要。
- portfolio の価格フォールバックについて注記あり（price が欠損時の見積り欠落による誤ったブロック回避）。将来的に前日終値や取得原価でのフォールバックを検討する旨がコメントで残されている。
- set_cpu_affinity は引数が利用可能コア数を超える場合の動作や OS 非対応時のフォールバックを実装しているものの、環境によっては効果が限定される。
- Paper Trading の MockBrokerClient 実装自体はこの差分から参照されているが、詳細な API レベルの仕様・動作確認が別途必要。

---

今後の改善提案（コードからの推測）
- factor_research の完全実装とユニットテスト整備
- portfolio モジュール（position sizing / risk adjustment）の追加テストと edge-case のカバー（価格欠落、lot_size 銘柄別対応等）
- run_* スクリプト類の systemd / container 向けのユニットファイル・Docker サポート整備
- 監視・レポート機能の自動化（メール/LINE 通知との連動）とテスト

もし実際のリポジトリ履歴（コミットメッセージ）や意図したリリース日・バージョニング方針があれば、それに合わせて CHANGELOG を正確に調整できます。必要であれば修正・拡張します。