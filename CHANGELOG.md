# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはリポジトリの現在のコードベースから推測して作成した初期リリース向けの変更履歴です。

注意: バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に合わせて v0.1.0 としています。

## [Unreleased]

## [0.1.0] - 2026-04-22
初回公開リリース — コア機能とユーティリティ群を実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 実行エントリ / ランタイム
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバック。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - 監視は環境設定に関わらず本番 sqlite_path を使用して監視データベースを初期化。
    - duckdb 接続も確立して SystemMonitor に渡す。
  - run_execution: ExecutionEngine 起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用（data/paper_trading.db がデフォルト）して本番 DB と分離。
    - BrokerClientFactory を利用して実行時に適切なブローカークライアントを作成（MockBrokerClient を想定）。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止。実行 PID を data/execution.pid に記録（設定参照）。
    - RiskManager のデフォルト設定を明示（max_position_pct, max_utilization, rate_limit_per_sec 等）。

- 環境設定・検証・ウィザード
  - Settings クラス（src/kabusys/config.py）で環境変数の取得・検証を集中管理。
    - J-Quants / kabu API / LINE / DB パス / 監視・しきい値などのプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値検証を実施（有効値チェック）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml ベース）。必要に応じて自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスや config/*.yaml の存在/パースチェック、KABUSYS_ENV=live 向けのガードなどを実装。
    - --strict オプションで警告も失敗として扱う。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式で .env を初期作成/更新できるウィザード。シークレット項目はマスク表示。生成テンプレートは .env に保存される。

- 監視・モニタリング補助
  - init_monitoring_db を利用して監視用テーブルの初期化を行う仕組み（監視スクリプトから呼び出し）。
  - monitoring 用 SystemMonitor（モジュール本体は別ファイル想定）との連携。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルのスコアで上位 N を選定（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は警告ログを出して等分配にフォールバック。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中を抑制するフィルタ。既存保有のセクター比率が上限を超える場合、同セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。単元株（lot_size）丸め、per-position / aggregate キャップ、コストバッファの考慮、スケーリングによる再配分ロジックを実装。

- 解析・レポートツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH）から複数指標（稼働率・注文成功率・送信率・API レイテンシ等）を集計してレポートを出力。
    - P95 計算、期間フィルタ（--from / --to）、閾値（稼働率 99%、成立率 90% 等）と PASS/FAIL 判定を実装。

- 研究用ファクター計算（初期実装）
  - research/factor_research.py: momentum 等のファクターを計算するための下地を追加（DuckDB 経由で prices_daily 等のテーブル参照を想定）。（実装は途中まで含む）

- ロギング・プロセス制御ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。既存ハンドラはクリアしてから再設定。
    - LOG_DIR / LOG_LEVEL の優先解決と、ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を実装。
  - process_priority（src/kabusys/utils/process_priority.py）
    - クロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 設定を実装。アクセス権限不足等で失敗した場合はログ警告でスキップ。

### Changed
- （初回リリースのため履歴上の差分は無し）

### Fixed
- （初回リリースのため履歴上の差分は無し）

### Removed
- （該当無し）

### Deprecated
- （該当無し）

### Security
- （該当無し）

---

## 注記 / 実装上の留意点（既知事項）
- run_monitoring は「監視用の DB 初期化を行うが、監視自体は本番 sqlite_path を使用する」設計になっており、環境にかかわらず監視 DB が共有される点に注意が必要です。
- .env ファイルの自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では自動ロードがスキップされる可能性があります。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を利用できます。
- portfolio/position_sizing の aggregate スケーリングや lot_size 丸めのロジックは多くのエッジケースを扱いますが、将来的に銘柄別 lot_size をサポートする拡張が想定されています。
- research/factor_research.py はファクター計算の方針と一部実装を含みますが、完全実装は未完（ファイル末尾が途中で切れている形跡あり）。利用する際は追加実装が必要です。
- ファイル/ディレクトリ作成の失敗（ログディレクトリ等）はシステムの動作を阻害しないようフォールバック処理（コンソールのみ）を行いますが、実稼働では適切なパーミッション設定を推奨します。

もし CHANGELOG に特定のリリース日付や追加で強調したい変更点（例えば Broker の実装詳細や SystemMonitor の仕様）を反映したい場合は、該当箇所を教えてください。追記して更新します。