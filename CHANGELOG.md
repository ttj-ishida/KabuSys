# CHANGELOG

すべての重要な変更をここに記録します。形式は「Keep a Changelog」に準拠します。  

- リリースノートは semver を想定しています（このリポジトリの __version__ は 0.1.0）。
- 日付はリリース日を示します。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-21

初回公開リリース。日本株自動売買システム "KabuSys" の基盤機能を実装します。主な追加点、設計方針、既知の制約を以下にまとめます。

### Added
- 基本パッケージ骨格
  - パッケージ情報を定義: `kabusys.__version__ = "0.1.0"`。
  - モジュールエクスポートを整理（portfolio, execution, monitoring 等）。

- 環境設定・ロード
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml を基準に探索）。
  - .env ファイルの柔軟なパーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いに対応）。
  - OS 環境変数を保護するオプション（自動ロード時に既存の環境変数を上書きしない仕組み）。
  - Settings クラスを導入し、アプリ共通の設定をプロパティ経由で取得可能に（例: DB パス、KABUSYS_ENV、PAPER_FILL_MODE、各種しきい値など）。

- 設定支援ツール / 検証
  - 環境設定ウィザード CLI: `kabusys.config_setup`（対話式で .env を作成 / 更新、秘密値のマスク表示）。
  - 起動前構成検証 CLI: `kabusys.validate_config`（必須環境変数チェック、DB パスや YAML ファイルの存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性検証、--strict オプションで警告を FAIL 扱いにできる）。
  - validate_config は PyYAML の有無を考慮し、インストールされていない場合は YAML 検証をスキップして警告。

- ロギング基盤
  - 共通ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を実装。
  - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を組み合わせて統一ログ管理を提供。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

- プロセス優先度 / CPU 固定
  - `kabusys.utils.process_priority` により Windows / POSIX（Linux, macOS 等）を吸収したプロセス優先度設定を提供。psutil の権限制約や未対応 OS でも安全にフォールバック。
  - CPU affinity を最初 N コアに固定するユーティリティも実装（例外時は警告でスキップ）。

- 実行エンジン / 監視
  - 実行エンジン起動スクリプト `run_execution.py`
    - KABUSYS_ENV=paper_trading の場合、paper 用専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper_trading では MockBrokerClient を使用する想定）。
    - ExecutionEngine をスレッドで起動し、プロセス停止フラグ（data/stop_requested.flag）や pid ファイル管理を行う。
    - RiskManager, OrderManager, Reconciler 等の組み立てと初期設定を行う。RiskConfig の既定値を採用。
  - 監視プロセス起動スクリプト `run_monitoring.py`
    - SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視 DB は環境にかかわらず本番用 sqlite_path を使用する設計（監視は本番 DB に記録する想定）。
    - stop フラグを検出して安全にループを終了。

- 監視 DB 初期化
  - `init_monitoring_db`（monitoring_db モジュール）を呼び出して、監視テーブルの存在を保証（冪等性を想定）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定: `select_candidates`（スコア降順、タイブレークは signal_rank）。
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア合計がゼロの場合は等金額にフォールバックし警告）。
  - セクター集中制限: `apply_sector_cap`（既存保有のセクター比率が上限を超える場合、当該セクターの新規候補を除外。unknown セクターは除外対象外）。
  - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマッピング、未知レジームは警告して 1.0 でフォールバック）。
  - ポジションサイジング: `calc_position_sizes`
    - allocation_method に応じた株数算出（"risk_based" / "equal" / "score"）。
    - 損切り率、リスク割合、単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮。
    - aggregate cap（利用可能現金を超える場合のスケールダウンと端数処理）を実装。

- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加。
  - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算し、PASS/FAIL 判定を出力。
  - デフォルト DB パスは `data/paper_trading.db`。--from / --to / --db オプション対応。
  - P95 算出補助関数、欠損（テーブルなし）時の堅牢なフォールバック実装あり。

- リサーチ（ファクター計算）骨格
  - `kabusys.research.factor_research` にモメンタム等の計算ロジック（関数シグネチャと定数）を用意（DuckDB を経由した prices_daily / raw_financials を想定した設計）。
  - 長期 MA / ATR / ボリュームなど、複数のファクターを想定した定義を追加（実装は継続中、一部未完の箇所あり）。

### Changed
- なし（初回リリース）

### Fixed
- 設定・起動時に起こりうるエラーを多くハンドリング:
  - .env ファイル読み込み失敗時は警告を出してスキップ（例外を直接投げない）。
  - ログディレクトリ作成やファイルハンドラの作成に失敗した場合はコンソール出力にフォールバック。
  - psutil を使った優先度設定・CPU affinity の失敗は警告でスキップ。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## 注意事項 / マイグレーション / 実装上の注釈

- .env の自動ロードは既定で有効。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境変数の保護: OS 環境変数は自動ロード時に上書きされません（ただし .env.local を明示的に override するときは protected を考慮）。
- KABUSYS_ENV の有効値は `development`, `paper_trading`, `live` のみ。無効値はエラーになります。
- PAPER_TRADING（ペーパートレード）は本番 DB と分離されます。paper_trading モードでは `PAPER_TRADING_SQLITE_PATH` を利用してください（デフォルト: data/paper_trading.db）。
- `PAPER_FILL_MODE` の有効値は `"instant" | "partial" | "never" | "reject"` のみ。無効値は ValueError を送出します。
- 監視ループのポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可能。0 以下や非整数文字列はデフォルト（60 秒）にフォールバックして警告を出します。
- ポートフォリオ構成で price が欠損（0.0）だとエクスポージャーが過少見積りされる可能性あり（注釈と TODO を残しています）。将来的に価格フォールバック（前日終値等）を導入予定。
- `kabusys.research.factor_research` は設計方針と定数を整備済みですが、関数実装の一部（ファクター計算の続き）は未完です。使用前に実装完了が必要です。

---

この CHANGELOG は、コードベースから推測して記載しています。実際の開発履歴（コミットメッセージ等）に合わせて適宜更新してください。