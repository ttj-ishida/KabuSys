Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての注目すべき変更を記録します。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-04-22
初期公開リリース。以下の主要機能とユーティリティを実装しました。

### Added
- 全般
  - パッケージ初期リリース (kabusys v0.1.0)。
  - Python モジュール構成とバージョン定義を追加（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数自動読み込み機能を追加（.env, .env.local の順で読み込み、既存の OS 環境変数は保護）。
  - .env パース実装: export 形式・クォート・エスケープ・インラインコメントの取り扱いに対応（src/kabusys/config.py）。
  - Settings クラスを実装し、アプリ設定（J-Quants、kabu API、DB パス、監視閾値、環境など）をプロパティ経由で提供。
  - 環境変数自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- 環境セットアップ / 検証 CLI
  - 対話式 .env 作成ウィザードを追加（python -m kabusys.config_setup）。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話形式で生成・更新。
    - 既存 .env 読み込み、シークレットのマスク表示、確認プロンプト、保存機能を実装。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML があれば内容検証）。
    - --strict オプションで警告もエラー扱いにできる。

- 実行スクリプト / デーモン
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）に記録し、本番 DB と分離。
    - ブローカー生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動ロジック（デーモン化スレッドで実行）。
    - data/stop_requested.flag による外部停止フラグ検出と安全停止処理、execution.pid 管理。
    - RiskManager のデフォルト設定値（max_position_pct 等）を含むサンプル設定を実装。
  - 監視（モニタリング）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番の sqlite_path を使用する仕様（監視データは一元化）。
    - stop flag 検出、例外時のログ出力、KeyboardInterrupt による終了、DB/duckdb 接続ライフサイクル管理を実装。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / log_dir 引数、LOG_LEVEL による解決、ディレクトリ作成失敗時はコンソール出力のみでフォールバック。
    - ログファイルを日次ローテーション、30 日分保持。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX (Linux, macOS, FreeBSD) 用に差分を吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(n) により最初の n コアにプロセスをピンニングする機能を提供。
    - 権限不足や未対応 OS では安全に警告を出してスキップ。

- データベース統合
  - DuckDB（分析用）と SQLite（監視/履歴用）の併用を前提にした接続パターンを導入。
  - 監視テーブル初期化ユーティリティ呼び出しにより起動時の DB 準備を担保（init_monitoring_db 呼び出し）。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定 / 重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順（タイブレークは signal_rank）で上位 N を選択。
    - calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに応じて当日新規候補を除外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を提供（bull/neutral/bear をサポート、未知値はフォールバック）。
  - 位置サイズ決定（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に基づく発注株数計算（risk_based / equal / score）。
    - 単元株丸め (lot_size)、max_position_pct、max_utilization、cost_buffer（スリッページ等）を考慮した aggregate cap とスケーリング処理を実装。

- 研究・ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - デフォルトの DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - P95 計算、日付フィルタ、SQL 実行での例外（テーブル未存在など）に対する耐性あり。
  - 研究用ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - Momentum 等のファクター算出を行う設計（DuckDB の prices_daily / raw_financials を参照）。モジュールは計算対象期間等の定数を定義。

- パッケージエクスポート
  - portfolio パッケージのトップレベルエクスポートを整備（select_candidates 等を公開）。

### Changed
- N/A（初期リリースのため該当なし）

### Fixed
- 環境変数読み込みの堅牢化
  - .env パーサでクォート内のエスケープ処理やコメント判定を改善し、実運用での多様な .env 記法に対応。
- ログディレクトリ作成失敗時のフォールバックを実装（ログ出力確保のため、ファイルハンドラ作成に失敗しても stdout ログを維持）。

### Security
- シークレット（API トークン、パスワード）は対話ウィザードでマスク表示。 .env ファイル生成時に注意書きを追加（.env を Git にコミットしない旨）。

注記・今後の課題（実装上の観察）
- risk_adjustment.apply_sector_cap は price_map に 0.0 が入るとエクスポージャーが過小見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO コメントで残しています。
- position_sizing は現状で全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size マスタの導入を想定した拡張ポイントあり。
- research/factor_research.py はファクター計算の骨組みを備えていますが、実装の続きを追加可能（ファクター正規化や DuckDB クエリ最適化など）。

以上。リリースに関する補足や変更点の追記を希望する場合は、どの領域（実行 / 監視 / 設定 / ポートフォリオ / ツール 等）について追記すべきか教えてください。