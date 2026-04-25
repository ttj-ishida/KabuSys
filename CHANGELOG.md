# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠します。  
主にソースコードから読み取れる変更点・機能を推測して記載しています。

全体方針:
- 重要な追加機能・CLI・ユーティリティを明確に記載
- 環境変数やファイルパス、挙動に関する注意点やデフォルト値を明示
- 互換性や移行時に注意すべき点（breaking changes）を明記

最新: Unreleased
----------------

### Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はリポジトリ直下の data/stop_requested.flag により行う。
  - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用する仕様。
  - DuckDB 連携（duckdb.connect）を行い、init_monitoring_db による監視テーブル初期化を実施。
  - プロセス優先度を起動時に "high" に設定（utils.process_priority 経由）。

- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てとデーモン Thread による実行。
  - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）対応。
  - 起動時にプロセス優先度を "high" に設定。

- config.py:
  - 環境変数自動読み込み実装（.env, .env.local）。OS 環境変数を保護する仕組みあり。
  - .env パースの細かい挙動（export 句対応、クォート内エスケープ処理、インラインコメントの扱い）を実装。
  - Settings クラスを導入し、J-Quants / kabu API / LINE / DB /監視/システム設定をプロパティで提供。
  - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
  - env 値（KABUSYS_ENV）の検証（development, paper_trading, live）と LOG_LEVEL の検証。
  - デフォルトファイルパス（DUCKDB_PATH, SQLITE_PATH 等）および便利プロパティ（is_live / is_paper / is_dev）を提供。

- config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。
  - 対話画面で各設定項目を入力可能（シークレット入力の扱い、選択肢、デフォルト値表示）。
  - 既存 .env の読み込み・再利用、確認プロンプト、.env ファイル書き出しを実装。
  - 出力される .env はコメント付きテンプレート形式。

- validate_config.py: 起動前の設定検証 CLI を追加。
  - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスと config/*.yaml の存在・パース検証（PyYAML 有無で挙動変化）、本番環境向けガード（LINE 設定や Kill Switch のクリア設定）を実装。
  - --strict オプションで警告も失敗扱いにできる。

- utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
  - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
  - ログレベル / ログディレクトリの解決優先順（引数 > 環境変数 > デフォルト）を実装。
  - ログディレクトリ作成失敗時のフォールバック（ファイル出力をスキップ）を安全に処理。

- utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - Windows / POSIX（Linux, Darwin, FreeBSD）に対応し差分を吸収。
  - set_process_priority(level) により nice 値や Windows の優先度を設定。失敗時は警告でスキップ。
  - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能を提供。

- portfolio モジュール:
  - portfolio_builder: 候補選定（select_candidates）、等金額（calc_equal_weights）／スコア加重（calc_score_weights）重み計算を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックを行い警告出力。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算を実装。lot_size（単元株）丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate スケーリング、端数処理ロジックを備える。
  - すべて純関数的（DB 非依存）で PortfolioConstruction.md 等に基づいている旨の設計注記あり。

- tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
  - system_status/trade_logs/risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計。
  - P95 計算、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定を実装。
  - --from / --to / --db オプションを提供し、環境変数 PAPER_TRADING_SQLITE_PATH に対応。

- research/factor_research.py（途中まで実装）: ファクター計算の骨組みを追加。
  - モメンタムや移動平均乖離、ATR 等の計算仕様と定数を定義。DuckDB 接続を受ける設計。

- パッケージ初期化:
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- ロギング: stdout を標準出力に用いる方針を明示（cron / Scheduler との併用を想定）。
- 環境設定自動ロード: .env/.env.local の読み込みロジックに保護キー（OS 環境）を導入し、安全性を高めた。

### Fixed
- 環境変数パースの堅牢化: クォート付き値のバックスラッシュエスケープ対応、インラインコメント取り扱い、不正値のフォールバックメッセージを追加。
- run_monitoring の MONITOR_POLL_INTERVAL の 0 以下や不正値をハンドリングしてデフォルトにフォールバック。

0.1.0 — 2026-04-25
------------------

初回リリース（推定） — 下記の主要機能を含む最初のリリース。

### Added
- コア起動スクリプト
  - run_execution.py（ExecutionEngine 起動）
  - run_monitoring.py（SystemMonitor ポーリング）

- 設定管理
  - Settings クラス（環境変数読み取り・検証）
  - .env 自動読み込み (.env, .env.local) と保護機構

- CLI / ユーティリティ
  - config_setup.py（対話式 .env ウィザード）
  - validate_config.py（設定検証 CLI）

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py（stdout + 日次ローテーションファイル）
  - utils/process_priority.py（優先度 / CPU affinity）

- ポートフォリオ構築ロジック
  - portfolio_builder, risk_adjustment, position_sizing（候補選定・重み・セクター制約・株数算出）

- 分析・検証ツール
  - tools/paper_verification_report.py（Paper Trading 検証レポート）

- 研究用モジュール（基礎）
  - research/factor_research.py（ファクター計算の設計と一部実装）

### Changed
- SQLite/DuckDB の使用方法とデフォルトパスを明文化（環境変数で上書き可能）。
- Paper Trading 実行時は本番 DB と完全に分離されるよう paper_sqlite_path を採用。

### Fixed
- 各種デフォルト値・検証の追加（LOG_LEVEL / KABUSYS_ENV / PAPER_FILL_MODE の検証など）。
- ログディレクトリ作成失敗時の安全なフォールバック。

注意事項（Migration / 運用上のポイント）
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。環境分離が必要な場合は設定を明示的に調整してください。
- Paper Trading を行う場合、PAPER_TRADING_SQLITE_PATH（または KABUSYS_ENV=paper_trading）により履歴が data/paper_trading.db に記録され、本番 DB と分離されます。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のテンプレートにも注意書きあり）。
- process_priority / cpu_affinity は権限や OS に依存します。権限不足や未サポート環境では警告が出て設定はスキップされます。
- logging_setup はログファイル出力に失敗した場合でもコンソール出力は継続します。LOG_DIR の書き込み権限を確認してください。
- validate_config の config/*.yaml 検査は PyYAML インストールに依存します（未インストール時は検証をスキップして警告）。

将来の改善案（コードから推測）
- research/factor_research.py の実装完了（各ファクター算出ロジックの SQL/DuckDB 実装）。
- position_sizing の lot_size を銘柄別にサポートする拡張（stocks マスタ導入）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価を使用する処理）。
- Paper Trading のレポートを CSV / JSON 出力、並びに自動通知機能（LINE）等の追加。

署名
----
本 CHANGELOG は与えられたソースコードから推測して作成しました。実際のリリースノートや履歴と差異がある場合があります。必要であれば、特定コミットや差分に基づくより厳密な CHANGELOG を作成します。