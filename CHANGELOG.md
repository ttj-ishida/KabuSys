CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 基本アーキテクチャと各種ユーティリティを含む初期リリースを追加。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 に設定。
- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) によるグレースフルシャットダウンに対応。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite を使用（data/paper_trading.db、環境変数で上書き可）。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine を別スレッドで実行し停止フラグで停止可能。
    - 実行用 PID ファイル（data/execution.pid）をサポート。
- 設定管理・セットアップ
  - src/kabusys/config.py
    - 環境変数読み込みと Settings クラスを実装。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 各種設定プロパティ（DB パス、KABU/J-Quants トークン、ログレベル、Paper Trading 設定、監視しきい値など）を提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - src/kabusys/config_setup.py
    - .env を対話式に作成・更新するウィザード CLI を追加。
    - デフォルト値、シークレットマスキング、既存 .env の読み込み・再利用をサポート。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の存在・基本整合性を起動前にチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや YAML パース確認、live 環境向けガード（LINE 設定や Kill Switch の注意）を実装。
    - --strict フラグで警告も失敗扱いにできる。
- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額・スコア加重配分の純粋関数を実装。
    - スコア全てが 0.0 の場合は等分配にフォールバックし警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - unknown セクターの扱い、レジームのフォールバックロジックを含む。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリングを実装。
    - 単元（lot_size）・手数料/スリッページ見積り（cost_buffer）を考慮。
  - src/kabusys/portfolio/__init__.py にて主要関数をエクスポート。
- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加：コンソール(stdout) と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）を設定。
    - LOG_DIR / LOG_LEVEL の解決順、ハンドラ重複防止の実装、ファイルハンドラ失敗時のフォールバック処理を含む。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分吸収、権限不足時のワーニング処理を実装。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出してレポート出力する CLI を追加。
    - デフォルト DB パスは data/paper_trading.db、コマンドラインで期間指定可能（--from / --to）。
    - 基準値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を実装。
- 研究用ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / ボリューム等の計算を想定）。DuckDB 接続を受ける設計。
    - （実装途中、関数シグネチャや定数が定義済み。）
- パッケージ化・公開準備
  - src/kabusys/tools/__init__.py, src/kabusys/utils/__init__.py など、パッケージ初期化ファイルを追加。

Fixed
- （初期リリースのため過去の不具合修正はなし。ただし各モジュールでエラー時の安全なフォールバックやワーニング出力を積極的に実装。）

Changed
- （初回リリースのため過去の変更は無し）

Deprecated
- （なし）

Removed
- （なし）

Security
- 機密情報は .env に格納する設計。config_setup の README にも .env を Git にコミットしない旨を明記。
- 実行中に .env のシークレット値をマスク表示するなどの配慮あり。

Notes / Known issues / TODO
- config.py:
  - .env 自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml）。配布環境では自動ロードがスキップされる可能性があるため注意。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格の導入を要検討（TODO コメントあり）。
- portfolio/position_sizing.calc_position_sizes:
  - lot_size をグローバル固定（デフォルト 100）としている。将来的には銘柄別単元対応を想定する TODO コメントあり。
- research/factor_research.py:
  - 実装途中の箇所あり（ファイル末尾で未完の局所的な実装が見られます）。使用時は注意。
- run_monitoring.py / run_execution.py:
  - 停止フラグや PID ファイルによる制御を実装しているが、運用時はファイルパーミッションや外部プロセスとの整合性に注意してください。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールのみで継続する挙動です。

開発者向けメモ
- 環境変数の主要キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, PAPER_FILL_MODE
- デフォルトファイルパス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log
  - 停止フラグ: data/stop_requested.flag
  - 実行 PID: data/execution.pid

お問い合わせ・貢献
- バグ報告、改善提案、プルリクエストはリポジトリの Issue/PR をご利用ください。