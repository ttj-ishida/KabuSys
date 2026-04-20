# CHANGELOG

すべての notable な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

読み方の注意:
- 本リリースノートは、提供されたコードベースから機能・挙動を推測して作成しています。
- 環境変数やファイルパスのデフォルト値はソース中の記述に従っています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーションメタ情報を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`（src/kabusys/__init__.py）。

- 実行スクリプト（起動エントリ）を追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず production の `sqlite_path` を使用する設計。
    - 停止フラグファイル (data/stop_requested.flag) を検知してループを終了。
    - DuckDB 接続の利用と監視 DB 初期化処理を行う。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper trading SQLite DB を使用して本番 DB と完全分離（`PAPER_TRADING_SQLITE_PATH` または Settings.paper_sqlite_path）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止制御を実装。
    - 停止フラグおよび PID ファイル管理をサポート。

- 設定管理と自動 .env ロード機構を追加（src/kabusys/config.py）
  - プロジェクトルート判定: `.git` または `pyproject.toml` を上位ディレクトリから探索して自動的に特定。
  - .env ファイルの自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパースは `export KEY=val` 形式、クォートされた値、インラインコメント等に対応（エスケープ処理含む）。
  - Settings クラスで各種設定値をプロパティ化（J-Quants、kabu API、LINE、DB、監視しきい値、環境判定、ログレベル等）。
  - `PAPER_FILL_MODE` の値検証（有効値: "instant" | "partial" | "never" | "reject"）。
  - 各種閾値（CPU/Mem/Disk）の既定値を提供。

- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）
  - 対話式で .env の作成/更新を行うウィザードを実装。
  - J-Quants トークン・kabu API パスワード等の機密項目はマスク表示しつつ入力受付。
  - デフォルト値、選択肢、説明文を提示して .env を書き出す `_write_env` を提供。
  - 保存確認・中断時の安全な挙動を実装。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - .env や `config/*.yaml` の存在・妥当性を事前チェックするツール。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML がインストールされている場合）などを実行。
  - `--strict` オプションにより警告を FAIL 扱いにできる。

- ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - 共通関数 `setup_logging(app_name, log_dir, level)` を提供。
  - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
  - ログレベル・ログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
  - ログディレクトリ作成失敗時はファイルログをスキップして stdout のみで継続。

- プロセス優先度・CPU affinity 操作ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - OS 差分を吸収してカレントプロセスの優先度（high/normal/low）を設定する `set_process_priority` を実装（Windows, POSIX 系に対応）。
  - CPU コア固定用 `set_cpu_affinity(cpu_count)` を実装。権限不足や未サポート環境は警告を出してスキップ。

- ポートフォリオ構築関連モジュールを追加（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - 候補選択 (`select_candidates`)、等配分重み (`calc_equal_weights`)、スコア重み (`calc_score_weights`) を実装。
  - risk_adjustment.py
    - セクター集中制限適用 (`apply_sector_cap`)、市場レジームに応じた資金乗数計算 (`calc_regime_multiplier`) を実装。
  - position_sizing.py
    - 銘柄ごとの発注株数計算 (`calc_position_sizes`) を実装。risk_based / equal / score の allocation_method をサポートし、単元株（lot_size）丸め、aggregate cap（利用可能現金）に対するスケーリング、コストバッファ処理を行う。
  - これらは純粋関数で DB に依存しない設計。

- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
  - paper trading 用 SQLite (`data/paper_trading.db` デフォルト) から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を計算してレポートを出力。
  - 判定基準（しきい値）を定義し、PASS/FAIL を表示。
  - コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）に対応。

- 研究用ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）
  - Momentum / Value / Volatility / Liquidity 系ファクターの設計と計算方針の枠組みを実装（DuckDB の prices_daily / raw_financials を参照する設計）。（ファイル末尾は一部未完の箇所あり）

- 監視データベースの初期化ユーティリティを追加参照
  - run_* スクリプトから `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Notes / 実運用上の注意
- 自動で .env を読み込む機能は便利だが、本番での誤操作を避けるため `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して無効化可能。
- run_monitoring の監視 DB は環境にかかわらず Settings.sqlite_path（本番想定）を参照するため、テスト/開発環境で監視 DB を分離したい場合は sqlite_path を明示的に変更するか設計を調整してください。
- process priority / cpu affinity 設定は環境に依存し、権限不足時には警告が出力されます（挙動はスキップされます）。
- position_sizing の lot_size は現状グローバル共通の想定。将来の拡張で銘柄別ロットサイズを導入する旨の TODO コメントあり。
- research/factor_research.py は実装の大枠があるものの、ソース末尾で一部未完成の箇所が見受けられます。追加実装・テストが必要です。

---

作成: ソースコードから推測して自動生成。必要があれば各項目を詳細化・訂正します。