# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは後続のリリースで適宜更新してください。

全般的な注記
- 本リポジトリは日本株自動売買システム「KabuSys」の初期実装（v0.1.0）相当の機能群を含みます。
- 動作に必要な環境変数は .env から読み込まれ、自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

## [0.1.0] - 2026-04-25

### Added
- 共通
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。
  - プロジェクト全体で利用する Settings クラスを `kabusys.config` に実装。
    - 多数の環境変数（J-Quants / kabuAPI / DB パス / ログ設定 / 監視閾値など）をプロパティ経由で取得可能。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - Paper Trading 用の設定（`paper_sqlite_path`、`paper_fill_mode`）をサポート。
    - PID / kill flag / 各種閾値の取得メソッドを提供。

- 実行スクリプト / サービス
  - `run_execution.py`
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は Paper Trading 用の SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory を使ったブローカークライアントの生成と、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止はプロジェクトの data/stop_requested.flag を検知して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中の PID を data/execution.pid に管理（ExecutionEngine 側で使用）。
  - `run_monitoring.py`
    - SystemMonitor をポーリングで定期実行する監視スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効な値は警告を出してデフォルトにフォールバック。
    - 監視側は環境に関わらず本番用の sqlite_path を使用して監視テーブルを初期化。
    - 停止は data/stop_requested.flag の存在で検知。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / CLI
  - `.env` の読み込みロジックを `kabusys.config` に実装。
    - 自動読み込みの優先順位: OS 環境 > .env.local > .env。
    - `.env` の1行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等をサポート。
    - ファイル読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。
  - `kabusys.config_setup`
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch オプションなど主要設定を対話形式で入力可能。
    - 既存 .env の読み込み・既存値の再利用・秘密値のマスク表示に対応。
  - `kabusys.validate_config`
    - 起動前に環境変数および config/*.yaml の基本的な妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がインストールされている場合）を実施。
    - `--strict` オプションで警告を FAIL として扱うモードを提供。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - Root ロガーに Console(StreamHandler -> stdout) と 日次ローテートの FileHandler を設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決ルールを実装。
  - `kabusys.utils.process_priority`
    - Windows・POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を追加（権限不足時は警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: BUY シグナルをスコアでソートして上位を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算を実装。全銘柄スコアが 0 の場合はフォールバックで等配分。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中上限に基づき新規候補を除外するロジックを追加。unknown セクターは上限適用外。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。単元株（lot_size）で丸め、per-stock / aggregate の上限や cost_buffer による保守的見積りを考慮。
    - aggregate cap 超過時はスケーリング＆残差分の lot 単位で再配分するロジックを提供。

- Paper Trading / 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間指定で検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算して PASS/FAIL を判定する閾値を定義（デフォルト閾値はコード内に明記）。
    - 日付フィルタ、DB パス指定オプションをサポート。

- 研究用モジュール（着手）
  - `kabusys.research.factor_research`
    - ファクター計算モジュールの枠組みを追加（momentum / value / volatility / liquidity の記述と定数群）。DuckDB を用いた prices_daily / raw_financials の参照を想定。モジュールは未完（途中実装）。

### Changed
- 環境ファイル読み込み
  - 自動読み込みの挙動を明文化（.env.local が .env を上書きする挙動、既存 OS 環境変数は保護される挙動）。
- ロギング
  - 標準出力は stderr ではなく stdout を使用（cron 等で stdout/stderr をリダイレクトする運用を想定）。

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数やシークレット値（J-Quants / Kabu API パスワードなど）は .env に明記しないことを README 等で強く推奨（config_setup のヘッダに注意書きあり）。

---

今後の予定（提案）
- factor_research の完全実装（各ファクター計算と Z スコア正規化の統合）
- ExecutionEngine / SystemMonitor のユニットテスト強化
- 設定検証の CI 統合（validate_config を CI 前処理として利用）
- BrokerClient の抽象化と Mock の拡張によるシミュレーション精度向上

貢献・バグ報告は issue を通じてお願いします。