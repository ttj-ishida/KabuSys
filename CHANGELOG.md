# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはコードベースから推測した変更点・機能説明を日本語でまとめたものです。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境設定/読み込み
  - .env ファイルの自動読み込み機構を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - .env パーサを実装:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート付き値、エスケープシーケンス、インラインコメントの扱いに対応。
    - `_load_env_file()` により `.env` と `.env.local` を適切な優先度で読み込む（OS 環境変数は保護）。
  - `Settings` クラスを導入し、環境変数の取得・バリデーションを提供:
    - J-Quants / kabu API トークン取得、DB パス（DuckDB/SQLite）、ログ設定、Kill Switch 関連、監視閾値、環境モード判定（development / paper_trading / live）など。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、`.env` の初期生成・更新を支援。
  - 必須/任意項目・シークレット項目の扱い、既存 `.env` 読み込み、保存前の確認プロンプトを実装。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証 CLI を実装。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在と（PyYAML があれば）パース検証、`live` 環境向けの追加警告等を提供。
  - `--strict` オプションにより警告を FAIL として扱うモードを追加。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging()` を実装。
  - stdout 出力用の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。
  - ログレベル/ログディレクトリの解決ルールを提供（引数 > 環境変数 > デフォルト）。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority()` を提供。
  - `set_cpu_affinity()` によりカレントプロセスを最初の N コアに固定する機能を実装（許可がない場合は警告を出してスキップ）。

- 実行コンポーネント起動スクリプト
  - `run_execution.py`:
    - `ExecutionEngine` 起動スクリプト（ログ設定・プロセス優先度設定・DB 接続・コンポーネント組み立て・スレッド実行・停止フラグ監視）。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用して本番 DB と分離する挙動を明示。
    - Broker クライアントは `BrokerClientFactory.create(settings)` で環境に応じた実装を生成。
    - エンジンの PID ファイル管理・停止フラグ（data/stop_requested.flag）による安全停止対応。
  - `run_monitoring.py`:
    - `SystemMonitor` ポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する仕様（監視データ集約先）。

- Monitoring / DB 初期化
  - 監視テーブルなどの冪等初期化を行う `init_monitoring_db()` を利用する起動フローを導入（monitoring 側の DB スキーマ初期化を保証）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から各種指標を集計して検証レポートを生成:
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数 などを計算。
    - 閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を定義し PASS/FAIL を判定。
    - コマンドライン引数 `--from/--to`（YYYY-MM-DD）で期間を指定可能、`--db` で DB パス上書き可能。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates()`（スコア降順、タイブレークに signal_rank）。
    - 等分配 `calc_equal_weights()`、スコア加重 `calc_score_weights()`（全スコアが 0 の場合は等分配にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap()`（既存ポジションを考慮し、max_sector_pct を超えるセクターの新規候補を除外。unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier()`（bull/neutral/bear のマップ、未知レジームはワーニングを出して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数計算 `calc_position_sizes()`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元丸め（lot_size）・1銘柄上限・aggregate cap（available_cash）・cost_buffer を考慮したスケーリングロジックを実装。

- リサーチ（ファクター算出）骨格
  - `kabusys.research.factor_research` にモメンタム等ファクター計算の骨格を追加（DuckDB 接続を受け、prices_daily/raw_financials を参照する設計）。
  - 定義済みファクター: Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR）、Value（PER/ROE）、Liquidity（出来高等）の計算方針と定数を定義。モジュールは DuckDB ベースでの実装を想定。

### Changed
- なし（初回リリース想定のため）。

### Fixed / Improved
- .env パーサの堅牢化:
  - クォート付き値のバックスラッシュエスケープやインラインコメントの扱いを実装して、様々な .env 表記に対応。
- ログ設定の堅牢化:
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続する旨を実装。
- process_priority の互換性処理:
  - Windows 固有の定数が存在しない環境でもモジュールをロードできるよう getattr を使用してフォールバック。
  - 権限不足や未実装メソッドに対しては警告を出し処理をスキップする安全設計。

### Notes / Migration
- 起動スクリプト（monitoring / execution）は起動時に高優先度へプロセス優先度を上げようとします。権限により失敗する場合は警告が表示されますが起動は継続されます。
- Paper Trading と本番の DB は分離されています。paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が使用され、本番 DB とは独立して動作します。
- 監視（run_monitoring）は常に `Settings.sqlite_path`（本番の monitoring DB）を参照します。監視 DB を別にしたい場合は環境変数でパスを上書きしてください。
- `.env` 自動読み込みはデフォルトで有効です。テストなどで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `MONITOR_POLL_INTERVAL` は正の整数で指定してください。不正な値を設定するとデフォルトの 60 秒にフォールバックします。

---

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートはリポジトリのコミット履歴・変更管理に基づいて正式に作成してください。）