# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
リリース日はソースツリーのバージョンに合わせて記載しています。

## [0.1.0] - 2026-04-25

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎モジュールを追加。
  - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` に設定。
- 起動スクリプト / CLI を追加:
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル（data/stop_requested.flag）を検知してループを終了。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用する設計。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=`paper_trading` の場合は専用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 実行中は PID ファイル（data/execution.pid）を使用し、停止フラグでエンジンを停止。
  - `src/kabusys/validate_config.py`
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI（`python -m kabusys.validate_config`）。
    - `--strict` オプションで警告を失敗扱いにできる。
  - `src/kabusys/config_setup.py`
    - 対話式 .env 作成ウィザード（`python -m kabusys.config_setup`）。
    - .env の読み書き、既存値の再利用、シークレットのマスク表示などをサポート。
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード結果の検証レポート生成スクリプト（期間指定可）。
    - 稼働率・注文成功率・送信率・API レイテンシ（P95 など）を集計して PASS/FAIL 判定を出力。
- 設定・環境変数関連:
  - `src/kabusys/config.py`
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と上書きルール（OS 環境変数を保護）。
    - 複雑な .env 行（export 形式、クォート、エスケープ、インラインコメント）に対応したパーサを実装。
    - 設定アクセス用 Settings クラスを提供（各種パス、閾値、フラグ、env 判定など）。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode` 等を追加。
    - 自動ロードを無効にするための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
- ロギング / プロセス管理ユーティリティ:
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーへ StreamHandler (stdout) と 日次ローテートファイルハンドラを設定する共通関数 `setup_logging()` を追加。
    - ログディレクトリの自動作成、LOG_LEVEL/LOG_DIR の解決順をサポート。
    - stdout を使用することで cron 等からのリダイレクトに対応。
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX に対応）と CPU affinity 設定を追加。
    - `set_process_priority()` / `set_cpu_affinity()` を提供。
- ポートフォリオ構築関連（純粋関数群）:
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選別（select_candidates）、等金額・スコア重み（calc_equal_weights, calc_score_weights）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方式に対応。
    - 単元株 (lot_size)、cost_buffer、aggregate cap のスケーリングや再配分ロジックを実装。
- リサーチ用骨格:
  - `src/kabusys/research/factor_research.py`（ファクター計算の基礎定義、モメンタム等の設計方針と一部定義を追加）

### Changed
- ログの出力先・方式の統一:
  - すべての起動スクリプトで `setup_logging(app_name=...)` を呼ぶようにし、ログ管理を統一。
  - StreamHandler は stderr ではなく stdout を利用するように変更（cron / systemd などでの取り扱いを考慮）。
- DB パスの取扱い:
  - run_monitoring は環境に関係なく Settings.sqlite_path（本番監視 DB）を使用する仕様に明示。
  - run_execution は paper_trading 環境時は専用 paper_sqlite_path を使用するように明確化し、本番 DB と分離。
- .env ロードの挙動:
  - OS 環境変数を保護するため、.env/.env.local 読み込み時に既存キーを上書きしない（デフォルト）。`.env.local` は override=True で上書き可（ただし OS 環境変数は保護）。
- プロセス起動時の優先度:
  - run_monitoring / run_execution の起動直後に `set_process_priority("high")` を呼び出してプロセス優先度を上げるように変更。

### Fixed
- .env パーサの堅牢化:
  - single/double quote 内のバックスラッシュエスケープ、対応する閉じクォートの検出、インラインコメントの無視など複雑なケースに対応。
  - export プレフィックスの扱い、空行・コメント行の無視を改善。
- 環境変数のバリデーション強化:
  - `Settings.paper_fill_mode` で有効値チェックを追加（instant / partial / never / reject）。無効値は ValueError を投げる。
  - `Settings.env` / `Settings.log_level` の許容値チェックを追加して誤設定時に早期検出可能に。
- run_monitoring のポーリング間隔扱い:
  - `MONITOR_POLL_INTERVAL` の負値・0・非数の扱いを修正し、不正値の場合はデフォルト（60 秒）へフォールバックして警告ログを出力するようにした。
- logging_setup のファイルハンドラ作成失敗時のフォールバック:
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソールログのみで継続し、詳細な警告を出力するように改善。
- process_priority / cpu_affinity の例外ハンドリング:
  - 権限不足やプラットフォーム未対応時に警告して安全にスキップするようにした。

### Notes / Migration
- 重要: 監視 (run_monitoring) は KABUSYS_ENV にかかわらず Settings.sqlite_path を用いるため、監視 DB を分離したい場合は Settings.sqlite_path を適切に設定してください。
- ペーパートレード用 DB は `PAPER_TRADING_SQLITE_PATH` もしくは Settings の `paper_sqlite_path` を利用します（デフォルト: data/paper_trading.db）。
- .env の自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。
- MONITOR_POLL_INTERVAL は正の整数のみ有効です。0/負値/非数を与えるとデフォルト 60 秒へフォールバックします。
- `KILL_FLAG_CLEAR_ON_START` は本番環境では `0` を推奨します。validate_config にて `KABUSYS_ENV=live` の場合の警告を追加しています。

もし特定ファイルの変更差分（追加・差分）をより詳細に記録したい、あるいは各モジュールに対する利用例・使い方の短いドキュメントを CHANGELOG に付けたい場合はその旨を教えてください。