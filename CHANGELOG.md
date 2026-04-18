# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

現在のバージョン: 0.1.0

## [Unreleased]


## [0.1.0] - 2026-04-18
初回公開リリース

### Added
- 基本パッケージとバージョン定義
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を追加。

- 実行スクリプト
  - run_execution
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite（デフォルト: data/paper_trading.db）を使用するよう分離。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル (`data/execution.pid`) を扱う。
    - 停止制御用フラグファイル（data/stop_requested.flag）を監視し、安全に停止するループを実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行。

  - run_monitoring
    - SystemMonitor を定期ポーリングで実行する監視スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、負の値・0 は無効扱いでデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path（`SQLITE_PATH`、デフォルト: data/monitoring.db）を使用する設計。

- 設定管理
  - `kabusys.config.Settings`
    - 環境変数のラッパーを提供（J-Quants トークン、kabu API、DB パス、ログレベル、各種閾値やフラグ等）。
    - `.env` 自動読み込み機能を実装（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。`.env` → `.env.local` の順で読み込み、既存 OS 環境変数は保護。
    - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数をサポート。
    - `PAPER_FILL_MODE` の妥当性検査（"instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` の妥当性検査（"development" | "paper_trading" | "live"）。

  - config_setup
    - 対話式の .env 生成／更新ウィザードを追加（`python -m kabusys.config_setup`）。
    - デフォルト値、選択肢、シークレット表示マスクをサポート。`.env` 書き込み用ユーティリティを実装。

  - validate_config
    - 起動前に .env と config/*.yaml の不足・誤設定を検出する CLI を追加（`python -m kabusys.validate_config`）。
    - `--strict` オプションで警告を失敗として扱う。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）や本番環境向けガード（LINE トークン未設定や Kill Switch の自動クリア設定等）を実装。

- ロギング周り
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保存）を設定。
    - ログディレクトリの自動作成、失敗時はファイル出力を無効化してコンソール出力のみで継続。
    - ログレベルやログ保存先は引数／環境変数で制御可能。

- プロセス優先度 & CPU affinity
  - `kabusys.utils.process_priority`
    - Windows / POSIX の差分を吸収してプロセス優先度を設定 (`set_process_priority`)。
    - プロセスを最初の N コアに固定する `set_cpu_affinity` を実装（許可がない場合は警告を出してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を提供。

  - `kabusys.portfolio.risk_adjustment`
    - セクター集中を防ぐ `apply_sector_cap` を実装（売却予定銘柄を除外、"unknown" セクターは上限を適用しない）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（bull/neutral/bear → 1.0/0.7/0.3、未知は 1.0 にフォールバック）。

  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック `calc_position_sizes` を実装（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）への丸め、per-position 上限、aggregate cap のスケールダウン、cost_buffer を用いた保守的コスト見積りを実装。
    - スケーリング時の残差処理（lot 単位での配分）を実装。

  - ポートフォリオ関連のモジュールをまとめてエクスポートする `kabusys.portfolio.__init__` を追加。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite DB を解析して検証レポートを出力する CLI を追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などの指標を算出し、閾値判定で PASS/FAIL を出す。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- リサーチ / ファクター計算（初期実装開始）
  - `kabusys.research.factor_research`
    - Momentum/Value/Volatility/Liquidity 等のファクター計算方針と一部定数・関数（モメンタム計算のための定義）を追加（DuckDB 接続を受ける設計）。（実装途中のファイルあり）

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Notes / Known limitations
- 監視スクリプト（run_monitoring）は KABUSYS_ENV にかかわらず本番用 `SQLITE_PATH` を使用する設計です。テスト時は注意してください。
- `.env` の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。ライブラリ配布後など検出できない場合は自動ロードがスキップされます。
- `process_priority.set_process_priority` や CPU affinity の設定は OS 権限やプラットフォームの差異により失敗することがあり、その場合は警告を出してスキップします。
- ログディレクトリ作成やファイルハンドラ作成が失敗した場合はコンソール出力のみで継続します。
- `kabusys.portfolio.position_sizing` の将来の拡張点:
  - TODO: 銘柄毎の lot_size を持つマスタ（lot_map）への対応を検討中。
- `kabusys.portfolio.risk_adjustment.apply_sector_cap` では価格が 0.0 の場合にエクスポージャー過少見積りとなる可能性があり、将来的に前日終値や取得原価などのフォールバック価格を導入することが想定されています。
- `kabusys.research.factor_research` は一部未完の実装があります（ファイル末尾が途中で終わっています）。今後のリリースで完了予定。

---

今後のリリースでは、Execution/Monitoring の詳細挙動検証、テスト拡充、リサーチモジュールの完成、ブローカーインターフェースの安定化や運用向けの監視・アラート強化を予定しています。