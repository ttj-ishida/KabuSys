CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).

## [0.1.0] - 2026-04-19

初回リリース。以下の主要機能・ユーティリティ群を追加しました。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告出力。
    - 停止用フラグファイル（data/stop_requested.flag）の検知で安全にループ終了。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して初期化。
    - SQLite / DuckDB 接続の確立とクローズを保証。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時には専用のペーパートレード用 DB（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - プロセス優先度設定、PID ファイル（data/execution.pid）管理、停止フラグ検知による安全停止をサポート。
    - ExecutionEngine を別スレッドで起動し、停止フラグにより engine.stop() を呼ぶ制御。

- 設定関連
  - config.py
    - Settings クラスを導入。環境変数から各種設定値を取得・検証（env / log_level 等のバリデーション、PAPER_FILL_MODE の許容値チェックなど）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。既存 OS 環境変数を保護しつつ .env/.env.local を取り込む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - DuckDB / SQLite / PID パス等の既定値を提供。
  - config_setup.py
    - 対話式ウィザードを実装し .env の初期作成・更新を支援。既存値の再利用、シークレットマスク、保存確認などの UX を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時はスキップ）、本番向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。
    - LOG_DIR 環境変数や関数引数でログ出力先を変更可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの二重登録を防ぐために一度クリアしてから再設定。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows: priority class、POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - psutil の権限不足や未対応 OS の場合は安全にスキップして警告出力。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates: スコア降順、タイブレークに signal_rank）と配分重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights。全スコアが 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（既存ポジションのセクター別エクスポージャ計算、超過セクターの候補除外）。unknown セクターは上限適用対象外。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、合計投資キャップ（available_cash）に応じたスケーリング、cost_buffer による保守的なコスト見積り、余剰キャッシュに対する端数配分ロジックを備える。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、閾値に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB を指定可能。P95 計算ユーティリティ _p95 を実装。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
  - research/factor_research.py
    - ファクター計算モジュールの骨組みと定数を追加（momentum, value, volatility, liquidity を想定）。DuckDB 経由で prices_daily / raw_financials を参照する設計。モメンタム計算関数（calc_momentum）の実装を開始。

### Changed
- 環境ファイル読み込みの優先順位を明確化
  - OS 環境 > .env.local > .env の順で取り込む仕組みを導入。OS 環境は protected として上書きされない。
- ロギング出力を stdout に統一（StreamHandler）し、cron/Task Scheduler などからのリダイレクト運用に配慮。
- run_monitoring と run_execution の起動時にプロセス優先度を "high" に設定するように統一（起動直後に実行）。

### Fixed
- .env 読み込みの堅牢化
  - export 形式の行、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いに対応。無効行は無視して安全にパース。
- ログディレクトリ作成失敗時にファイルハンドラ作成でクラッシュしないようにフォールバック処理を追加。
- 設定検証（validate_config）で PyYAML 未インストール時に YAML パース検証をスキップし、警告を出力するように変更。

### Notes
- デフォルト値・バリデーション
  - MONITOR_POLL_INTERVAL のデフォルトは 60 秒。0 以下や非整数入力はデフォルトにフォールバックして警告を出力。
  - PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。無効な値は ValueError を発生させる。
  - KABUSYS_ENV は development / paper_trading / live のいずれかでなければならない（Settings でバリデーション）。
  - KILL_FLAG_CLEAR_ON_START は既定で 0（自動クリア無効）。本番環境で 1 にする場合は注意喚起を表示。

### Known limitations / TODO
- research/factor_research.calc_momentum の実装は途中（ファイル末尾が切れている／実装継続の余地あり）。
- position_sizing の lot_size は現状全銘柄共通の固定値（将来的に銘柄別 lot_map を導入することを想定）。
- apply_sector_cap の価格欠損（price が 0.0）の取り扱いについて注記（将来的にフォールバック価格を導入予定）。

---

今後のリリースでは、factor_research の完成、ExecutionEngine 周りのさらなる堅牢化、テストカバレッジ強化などを予定しています。