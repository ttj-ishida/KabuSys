# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
リリース日: 2026-04-19

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 環境設定・読み込み
  - Settings クラスを追加（kabusys.config）。
    - 環境変数の取得と検証を提供（KABUSYS_ENV, LOG_LEVEL 等）。
    - データベースパス、LINE トークン、kabuAPI、J-Quants トークンなどのプロパティを定義。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH のデフォルト: `data/paper_trading.db`）。
  - .env 自動ロード機能を実装（プロジェクトルートに基づき `.env` → `.env.local` を読み込む、既存 OS 環境変数は保護）。
  - .env パーサーを堅牢化（コメント、export プレフィックス、シングル/ダブルクォート中のエスケープ処理に対応）。

- 環境設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話式に `.env` を作成・更新するウィザード。
  - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を扱う。
  - シークレット値はマスクして表示。生成された `.env` を保存する機能を提供。

- 設定検証 CLI を追加（kabusys.validate_config）
  - 実行前に .env および `config/*.yaml` の存在・基本妥当性をチェックするツール。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、YAML パース（PyYAML がない場合は警告）を実施。
  - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行スクリプト
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の設計（監視データは環境に依存しない）。
    - 停止フラグファイル（`data/stop_requested.flag`）を検知して安全にループを終了。
    - SystemMonitor のチェックを定期実行し、例外発生時はログに記録して継続。
  - Execution 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 DB（`data/paper_trading.db`）に記録して本番 DB と分離。
    - エンジンはスレッドで実行、停止フラグ（`data/stop_requested.flag`）を検知してエンジン停止を要求。
    - PID ファイル管理（`data/execution.pid`）に対応。

- Execution コンポーネントの組立て（スケルトン）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager などの使用と初期化フローを実装。

- 監視 DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）を起動時に呼び出すことで監視テーブルの存在を保証（冪等）。

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - ルートロガーを統一的に設定する `setup_logging(app_name, log_dir, level)` を追加。
  - コンソール出力は stdout を使用、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
  - LOG_DIR / LOG_LEVEL 環境変数を考慮して設定。ログディレクトリ作成に失敗した場合はファイルハンドラを無効化してコンソールのみで継続。

- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) で Windows / POSIX を吸収して優先度設定（"high"/"normal"/"low"）。
  - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定する機能。
  - psutil を用いるが権限不足や未対応環境では警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 銘柄候補選定（select_candidates: スコア降順、タイブレークに signal_rank を使用）。
  - 重み計算
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0.0 の場合は等金額にフォールバックし WARNING を出力）。
  - リスク調整
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合、新規候補をフィルタリング（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知レジームはフォールバックして 1.0）。
  - ポジションサイズ算出（calc_position_sizes）
    - allocation_method に応じた株数計算（"risk_based" / "equal"/"score"）。
    - 単元株（lot_size、デフォルト 100）に丸める処理、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮。
    - cost_buffer を使った保守的見積り、スケールダウンと端数処理（残余キャッシュで lot_size 単位の追加配分）を実装。

- 研究／ファクター計算モジュール（kabusys.research.factor_research）
  - Momentum 等のファクター計算用のスケルトンを追加（DuckDB を使った prices_daily / raw_financials 参照設計）。
  - 定数、計算期間、戻り値の仕様（(date, code) 単位の dict list）を定義。

- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
  - ペーパートレード DB（デフォルト: `data/paper_trading.db`）を読みレポートを生成。
  - 指標・閾値:
    - 稼働率 (uptime) 基準: >= 99.0%
    - 注文成立率 (fill rate) 基準: >= 90.0%
    - 送信率 (send rate) 基準: >= 95.0%
    - P95 レイテンシ基準: <= 200 ms
  - --from / --to / --db オプション対応。P95 はサンプルから計算。
  - テーブルが存在しない場合は個別に例外処理して N/A 扱いにし、判定を行う。

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### 既知の制限 (Known issues / Notes)
- factor_research モジュールの関数 calc_momentum 等は実装途中（ファイル末尾が未完の箇所あり）。実データ計算ロジックは今後完成予定。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML）の有無や権限に依存し、環境によって動作が制限される可能性がある（コード中で graceful fallback を実装）。
- price が欠損（0.0）の場合、apply_sector_cap / calc_position_sizes のエクスポージャー算出や発注数計算で過少見積りとなる旨の TODO コメントあり（将来的にフォールバック価格導入を検討）。

---

今後の予定:
- factor_research の完実装、Strategy/Execution のテスト追加、ドキュメント拡充、CI テスト・型チェックの導入。