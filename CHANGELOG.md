# Changelog

すべての注目すべき変更点をこのファイルに記録します。本ファイルは Keep a Changelog に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19
初回公開リリース。本リリースでは自動売買システム KabuSys の基盤となる設定管理、起動スクリプト、ユーティリティ、ポートフォリオ構築ロジック、検証ツール群を実装しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するメインスクリプトを実装。
    - プロセス優先度を高に設定する処理を最初に実行。
    - 環境が `paper_trading` の場合はペーパートレード用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - ブローカークライアントの生成（BrokerClientFactory）および依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した起動/停止制御を実装。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔をオーバーライド可能（デフォルト: 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視テーブルを初期化。

- 設定管理 & ウィザード & 検証
  - `src/kabusys/config.py`
    - 環境変数 / .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env のパースロジック（クォート、エスケープ、インラインコメント処理対応）。
    - `Settings` クラスにより、各種設定（J-Quants トークン、kabu API、DB パス、Paper Trading 関連、監視しきい値、環境判定ロジック等）を型付きプロパティとして提供。入力値検証（列挙型や閾値チェック）を実装。
    - デフォルト値や環境変数名の定義を提供（例: DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
  - `src/kabusys/config_setup.py`
    - 対話式 .env 作成/更新ウィザードを実装。既存 .env の読み込み・表示、シークレット項目のマスク表示、ファイル保存機能を提供。
    - CLI から `python -m kabusys.config_setup` で利用可能。
  - `src/kabusys/validate_config.py`
    - 起動前に .env と config/*.yaml の不備を検出する検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス存在チェック（親ディレクトリ）、YAML のパース確認（PyYAML がインストールされている場合）、本番ガード（KABUSYS_ENV=live 時の追加警告）を実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（score 降順 + signal_rank タイブレーク）、等金額配分、スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバック。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限の適用（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。
    - 市場レジームに応じた投下資金乗数（regime_multiplier）を実装（bull/neutral/bear のマッピング）。未知レジームは警告を出して 1.0 にフォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - 複数の配分メソッド("risk_based", "equal", "score") に基づく株数算出を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）を実装。スケールダウン後の端数処理は lot 単位で再配分を行う。
    - cost_buffer（スリッページ/手数料の保守的見積り）を考慮。

- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 統一ログ設定ユーティリティを実装。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログを出力。既存ハンドラのクリアやログディレクトリの自動作成、環境変数（LOG_DIR, LOG_LEVEL）対応。
    - 失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 固定機能を提供（psutil を利用）。権限不足時は警告を出してスキップ。

- 監視・Monitoring 周り
  - run_monitoring / run_execution 内で監視テーブル初期化関数（monitoring.monitoring_db.init_monitoring_db）を呼び、監視テーブルの存在を保証（冪等）。
  - SystemMonitor（参照されるが本差分では別モジュールに実装）を用いたポーリングループを実装。

- ペーパートレード検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を読み、期間指定で検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill rate)、送信率(send rate)、リスク却下数、API レイテンシ（平均/最大/P95）などを集計。
    - PASS/FAIL 判定基準を実装（デフォルト閾値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms）。
    - コマンドライン引数で期間（--from / --to）や DB パス（--db）を指定可能。

- リサーチ（計算）モジュール
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続を受け取り、モメンタム等の定量ファクターを計算するための基盤を開始。モメンタム計算（1M/3M/6M、MA200 乖離）、ATR、出来高系などの設計方針・定数定義と calc_momentum の骨組み（注: ファイル末尾で一部未完の箇所あり）を含む。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Documentation
- 各モジュールに日本語ドキュメンテーションストリングを追加。CLI の使用方法や各プロパティ・関数の説明を明記。

### Environment / Configuration（主要な環境変数とデフォルト）
- 自動ロード対象ファイル: .env（および .env.local）
- 主要環境変数:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PAPER_FILL_MODE (デフォルト: instant; instant / partial / never / reject)
  - KABUSYS_ENV (development / paper_trading / live, デフォルト: development)
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔; デフォルト 60 秒)
  - KILL_FLAG_CLEAR_ON_START (本番の安全用フラグ)

### CLI
- python -m kabusys.config_setup  — .env 対話ウィザード
- python -m kabusys.validate_config [--strict] — 設定検証
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH] — ペーパートレード検証レポート

### Notes / Known limitations
- 一部モジュールは外部モジュール（ExecutionEngine, SystemMonitor, BrokerClientFactory など）への参照を含むが、それらの詳細実装は本差分に含まれません（本リリースはシステムの骨格・I/O/設定周りの実装が中心）。
- `research/factor_research.py` の末尾に未完のコード片（calc_momentum の実装途中）が見られます。将来的にファクター計算ロジックを完成させる予定です。
- position_sizing における価格欠損時のフォールバックや、銘柄ごとの lot_size を持たせる拡張は TODO として残されています。
- 一部機能（ファイル/ディレクトリ作成、プロセス優先度変更、CPU affinity 設定）は権限や環境に依存し、失敗時はログ警告を出して安全にスキップする設計です。

---

今後のリリースでは、ExecutionEngine / SystemMonitor / Broker クライアントの詳細実装、ファクター計算完成、テストカバレッジ拡充、ドキュメント整備を予定しています。