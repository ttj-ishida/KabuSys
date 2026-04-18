# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  

テンプレート:
- Unreleased: 今後の変更
- 各リリース: 追加(Added) / 変更(Changed) / 修正(Fixed) / 削除(Removed) / 非推奨(Deprecated) / セキュリティ(Security)

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回公開リリース。自動売買システム KabuSys のコアユーティリティ、実行・監視ランチャ、設定管理、ポートフォリオ構築、検証ツール、ユーティリティ群を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数を読み込み、各種設定値（DB パス、API トークン、環境種別、閾値 等）を提供。
  - .env 自動読み込み機能を実装:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を読み込む。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - `.env` のパースを堅牢化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしでのコメント判定などに対応。
  - `Settings` に以下の便利プロパティを追加:
    - DB パス: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`
    - 実行モード判定: `is_live`, `is_paper`, `is_dev`
    - Paper trading の fill モード: `paper_fill_mode`（入力値検証あり）
    - 各種監視閾値: `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - PID / Kill flag 関連パス: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`

- 対話式設定ウィザード
  - `kabusys.config_setup` を追加。対話式に `.env` を作成 / 更新する CLI ウィザードを提供。
  - `.env` の読み込み / 書き込みユーティリティを実装（既存値の再利用、シークレットマスク表示、保存確認など）。
  - デフォルト値、選択肢、説明文を含む複数の設定項目を用意（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）。

- 設定検証ツール
  - `kabusys.validate_config` を追加。起動前に環境変数や config/*.yaml の検証を行う CLI。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 値検証、DB パスの親ディレクトリ確認、YAML ファイルの存在・パース検証（PyYAML の有無に応じてスキップ）を実施。
  - `--strict` オプション: 警告も失敗扱いにできる。

- 実行・監視ランチャ
  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を高（High）に設定。
    - `KABUSYS_ENV=paper_trading` の場合は `paper_sqlite_path`（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成のための Factory を使用（BrokerClientFactory）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。停止フラグ（data/stop_requested.flag）を検知して安全に停止する仕組みを提供。
    - PID ファイルパス管理（data/execution.pid）。
  - `kabusys.run_monitoring`:
    - SystemMonitor 起動スクリプトを追加。
    - 環境にかかわらず監視は「本番」用の sqlite_path を使用する設計（監視データの一元化目的）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。不正な値（0 以下や非整数）はデフォルトにフォールバックし警告を出力。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 監視ループ内で例外を拾ってログ出力し、次ポーリングへ継続する堅牢化。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト logs/。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - stdout を使用することで cron/task scheduler などのログ取り回しに配慮。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加:
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する `set_process_priority(level)` を実装（high/normal/low）。
    - `set_cpu_affinity(cpu_count)` を実装（指定された最初の N コアにプロセスを固定）。
    - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢化。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順・タイブレークロジック）を追加。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等配分へフォールバック）を追加。
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap`：既存ポジションのセクターエクスポージャを元に新規候補をセクター上限（max_sector_pct）で除外するロジックを実装。unknown セクターは適用除外。
    - `calc_regime_multiplier`：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（フォールバック値とログ警告あり）。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes`：allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
      - Risk-based: リスク許容率（risk_pct）とストップロス（stop_loss_pct）から単銘柄の目標株数を算出。
      - Equal/Score: ウェイトから割当額を計算、単元株（lot_size）で丸め。
      - Aggregate cap（available_cash を超える場合）のスケールダウン処理を実装。スケールダウン後は端数補正（lot_size 単位）を行い、残余キャッシュで再配分。
      - price がない銘柄はスキップし、ログ出力で通知。
      - cost_buffer を考慮して保守的なコスト見積りを行う。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポート出力。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を用いた PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB パス指定（--db または 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - DB 内のテーブル欠如や OperationalError に対して堅牢にデフォルト値を返す実装。

- 研究用ファクター計算（骨組み）
  - `kabusys.research.factor_research` を追加（モメンタム / MA / ATR / ボリューム系の計算設計、DuckDB 接続を想定）。（一部実装が途中）

- 監視 DB 初期化
  - `init_monitoring_db` を使用して監視テーブルの存在を保証（冪等に初期化）。

### Changed
（初回リリースのため「変更」はありません）

### Fixed
- 環境変数や設定周りの堅牢化:
  - `MONITOR_POLL_INTERVAL` の不正値（非整数や 0 以下）を検出してデフォルトにフォールバックし、time.sleep に渡して ValueError となることを防止。
  - `paper_fill_mode` の無効値に対して明示的な検証とエラー（ValueError）を追加。
- ログ/ファイルハンドラ作成時の失敗に対するフォールバック処理を強化（ログディレクトリ作成失敗時はコンソールのみで継続）。

### Removed
（なし）

### Security
（なし）

---

注記:
- 本リリースはコードベースからの仕様・実装意図を基に推測して作成した CHANGELOG です。実際のコミット履歴が存在する場合はコミットログに基づいて調整してください。