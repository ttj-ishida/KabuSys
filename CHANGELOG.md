# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
初回リリースとして v0.1.0 を追加しました。

全般的な方針:
- 安全なデフォルト、環境変数による上書き、CLI ツール群、モジュール単位での純粋関数設計を重視しています。
- SQLite / DuckDB をデータ永続化・解析に使用し、paper_trading 環境では本番 DB と分離するよう設計されています。

## [Unreleased]
- （次回リリース用の未確定変更や改善点をここに記載してください）

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 環境・設定管理
  - .env ファイル自動読み込み機能を追加（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env パーサの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ対応。
    - 行末のインラインコメント扱いの改善（クォート外、かつ直前が空白／タブのときにコメントと認識）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを追加し、環境変数の取得と型変換・バリデーションを一元化:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須値取得。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の有効値チェック。
    - デフォルトパス（DuckDB / SQLite / paper_trading DB 等）の提供。
    - 便利プロパティ: is_live / is_paper / is_dev。

- 設定支援・検証ツール
  - 対話式ウィザード: `kabusys.config_setup`（.env の初期作成・更新を対話形式で支援）。
  - 設定検証 CLI: `kabusys.validate_config`（.env と config/*.yaml の整合性、必須環境変数、パス存在チェック、Live 環境向けガードを実装）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ログ・プロセス管理ユーティリティ
  - logging_setup:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで継続。
    - 日次ログローテーションと 30 日バックアップを設定。
  - process_priority:
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows / POSIX に対応）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 設定に失敗した場合は警告を出して安全にスキップ。

- 実行用スクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行（スレッド）を実装。
    - 停止制御はプロジェクトルートの data/stop_requested.flag と execution.pid を使用。
    - RiskConfig に初期パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入し、初期 portfolio value を broker.get_available_cash() から取得。

  - run_monitoring:
    - SystemMonitor をポーリングで定期実行する監視スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止は data/stop_requested.flag による検出で優雅に終了。

- 監視 DB 初期化
  - monitoring_db への初期化呼び出し（init_monitoring_db）を run_execution / run_monitoring で呼ぶことで監視テーブル存在を保証（冪等）。

- Portfolio（銘柄選定・配分・リスク調整）
  - portfolio_builder:
    - select_candidates（スコア降順・signal_rank によるタイブレークで上位 N 抽出）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア正規化、全スコア 0.0 の場合は等金額配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap（既存保有のセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier（market regime に応じた資金乗数を返却。bull/neutral/bear のマッピング、未知値はフォールバックして警告）。
  - position_sizing:
    - calc_position_sizes（allocation_method による株数算出。risk_based / equal / score をサポート）。
    - 単元株丸め（lot_size、デフォルト 100）や per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を考慮した保守的な計算、残差分配ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を解析してレポートを出力する CLI を追加。
    - 指標: システム稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ 等。
    - PASS/FAIL 判定基準を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
    - 日付フィルタオプション --from / --to と --db オプションをサポート。
    - P95 の計算実装（サンプル数が少ない場合にも対応）。
    - DB の存在チェックと操作エラーに対するフォールバック処理を実装。

- research
  - research/factor_research: ファクター計算モジュールの骨組みを追加（モメンタム・ボラティリティ等の計算設計と定数を定義）。DuckDB 経由で prices_daily / raw_financials を参照する設計。

### Changed
- ログ出力
  - ログの StreamHandler を stdout に統一（stderr ではなく stdout を使用） — Task Scheduler/cron 等で stdout/stderr を一本化する運用を想定。

- 環境変数ロード順
  - OS 環境変数 > .env.local (上書き可) > .env（既存値は上書きしない）という優先順位を明確化。
  - .env ロード時に OS の既存環境変数は保護される（protected set により上書きを防止）。

- プロセス優先度の取り扱い
  - set_process_priority はプラットフォーム差異を吸収し、権限不足や未対応 OS の場合は警告を出して処理を継続するよう堅牢化。

### Fixed
- 不正な MONITOR_POLL_INTERVAL の安全ハンドリング:
  - 0 以下や非整数の値が指定された場合にタイムループで ValueError を発生させず、デフォルト値にフォールバックして警告を出すよう修正。

### Notes / Implementation details
- DB 分離:
  - 実行（ExecutionEngine）は paper_trading 環境で paper_trading 用 SQLite を使用し、本番の監視 DB と分離される設計。監視（monitoring）は本番 sqlite_path を参照する設計。
- Stop / Kill フラグ:
  - 複数スクリプトで data/stop_requested.flag, data/kill.flag, pid ファイル等による外部制御を想定している（起動・終了・強制停止のオペレーション想定）。
- エラー耐性:
  - 監視ループ内で monitor.check_once() が例外を投げてもループは継続し、例外はログに残す設計（壊滅的なエラー以外で監視停止しない）。
- 将来的な拡張点（コード内 TODO）
  - position_sizing: 銘柄別 lot_size の導入（stocks マスタへの拡張を想定）。
  - risk_adjustment: price が欠損した場合のフォールバック価格（前日終値や取得原価）導入検討。

### Removed
- なし

### Security
- なし（このリリースではセキュリティ修正の記載はありません）

---

参考: 実装ファイル一覧（主な追加/変更ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py (ファクターモジュール骨組み)

もし特定の変更点を詳細に明記したい、あるいは過去バージョンとの差分をより厳密に作成したい場合は、追加のコミット／差分情報（Git のコミットログ等）を提供してください。