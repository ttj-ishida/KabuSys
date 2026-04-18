# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、このリポジトリのパッケージバージョンは `src/kabusys/__init__.py` の `__version__` に合わせています。

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワークの基本コンポーネントを実装しました。

### 追加（Added）
- 基本設定・環境読み込み
  - Settings クラス（src/kabusys/config.py）を実装し、環境変数から各種設定を取得するプロパティ群を提供。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。
  - .env のパースはクォート、エスケープ、`export KEY=val` 形式、行末コメント処理などに対応。

- 設定ウィザード & 検証ツール（CLI）
  - 対話式 .env ウィザード（src/kabusys/config_setup.py）を追加。初期 .env の作成・更新を支援。シークレットはマスク表示。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML があれば）などをチェック。`--strict` で警告も失敗扱いにできる。

- 実行系 / 監視スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合、専用のペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - ブローカークライアントのファクトリ経由生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。実行中は `data/stop_requested.flag` を監視して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル (`data/execution.pid`) を利用。
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。負の値や不正値はデフォルトにフォールバックし警告出力。
    - 監視用 DB 初期化（init_monitoring_db）を確実に行い、SystemMonitor を定期実行して状態を記録。停止は `data/stop_requested.flag` で制御。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログ出力先ディレクトリは引数 / 環境変数 `LOG_DIR` / デフォルト `logs/` の順で決定。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 出力は stdout（cron 等で stdout/stderr をまとめて扱いやすくするため）。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, macOS, FreeBSD）に対する差分吸収実装。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(N)` を提供。権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - `select_candidates`, `calc_equal_weights`, `calc_score_weights` を提供。スコアが全て 0 の場合は等金額配分にフォールバックして警告。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - `apply_sector_cap` により、既存ポジションのセクターエクスポージャが上限を超える場合は同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは警告のうえ 1.0 にフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - `calc_position_sizes` を実装。`risk_based` と `equal`/`score` の両方式をサポート。単元株（lot_size）で丸め、1銘柄上限、投下合計の aggregate cap、コストバッファを考慮したスケーリングと端数配分ロジックを実装。

- リサーチ / ファクター計算（下地）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨格を実装。DuckDB 接続を受け取り、モメンタム / ボラティリティ / 流動性 / バリュー等の計算を行う設計（prices_daily / raw_financials を前提）。（注意: ファイル末尾が途中で切れている箇所が見受けられます。実装継続を想定。）

- ペーパー検証レポート（ツール）
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）など。
    - 基準値（閾値）を定義し、PASS/FAIL を判定。コマンドライン引数で期間（--from/--to）と DB パス（--db）を指定可能。
    - DB テーブル不在やデータ不足時に安全に N/A を出力。

- パッケージ初期化
  - パッケージの __version__ を "0.1.0" に設定（src/kabusys/__init__.py）。
  - portfolio / tools / utils などのパッケージ構成を整理してエクスポートを設定。

### 変更（Changed）
- ログ出力の一元化
  - 各起動スクリプトから共通の `setup_logging` を呼び出すことでログ設定を統一。

- DB ハンドリング
  - 監視系と分析系で sqlite / duckdb を明確に使い分ける設計（Monitoring は本番 sqlite を使用、Execution は paper_trading 時に専用 sqlite を使用）。

### 仕様（Notes）
- 環境変数の重要なデフォルト値:
  - KABUSYS_ENV: "development"
  - DUCKDB_PATH: "data/kabusys.duckdb"
  - SQLITE_PATH: "data/monitoring.db"
  - PAPER_TRADING_SQLITE_PATH: "data/paper_trading.db"
  - LOG_LEVEL: "INFO"
  - MONITOR_POLL_INTERVAL: 60（秒）
- `KILL_FLAG_CLEAR_ON_START`、`PID_FILE_PATH`、`KILL_FLAG_PATH` 等により運用用の Kill Switch / PID 管理をサポート。
- 一部モジュールは外部ライブラリ (psutil, duckdb, PyYAML など) に依存。インストールされていない場合は機能制限や警告が出ます（例: PyYAML がない場合は YAML 検証をスキップ）。

### 既知の問題（Known issues）
- src/kabusys/research/factor_research.py の末尾が途中で切れているため、ファクター計算の完全実装が未完です。実装継続が必要です。
- position_sizing の価格フォールバック（価格が 0.0 / 欠損時の扱い）は TODO コメントがあり、現状では価格不明銘柄をスキップする挙動です。
- ファイル操作やシステム優先度設定は環境に依存するため、権限不足や未対応環境では機能をスキップし警告を出す設計になっていますが、運用環境での検証を推奨します。

---

今後のリリースでは以下のような改善を予定しています（例）:
- factor_research の完成とユニットテスト追加
- ExecutionEngine / BrokerClient の詳細実装と統合テスト
- ログ保管ポリシーや監視アラート（LINE 通知等）の強化
- 単体テスト・CI パイプラインの整備

（この CHANGELOG はコードベースからの推測に基づき作成しています。実際の変更履歴やコミットログと差異がある可能性があります。）