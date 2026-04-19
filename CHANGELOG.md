# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主要なコンポーネント、CLI、ユーティリティ、ポートフォリオ構築ロジック、監視・実行の起動スクリプトおよび検証ツール類を含みます。

### 追加 (Added)

- コアライブラリ
  - パッケージのバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - `kabusys.config.Settings` クラスを実装。
    - .env 自動読み込み機能（プロジェクトルートの検出を行い `.env` / `.env.local` を読み込む）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 必須/任意の環境変数・各種パス・閾値・フラグ等をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL、各種閾値など）。
    - `paper_trading` 用に `paper_sqlite_path` をサポートし、本番 DB と分離できる設計。
    - 入力値の検証（`PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` の許容値チェック）。
  - `kabusys.validate_config` CLI を追加:
    - .env と `config/*.yaml` の存在・基本的妥当性チェックを実行可能。
    - 必須環境変数の未設定検出、プレースホルダ検知、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ検証、PyYAML がある場合の YAML パースチェック、live 環境向けの追加ガード等を実行。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。
  - `kabusys.config_setup` 対話ウィザードを追加:
    - .env の初期作成・更新を対話的に行う CLI。
    - 各設定項目の説明、デフォルト、機密値マスキング、確認後の保存をサポート。

- 起動スクリプト / デーモン
  - `run_monitoring.py` を追加:
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - 監視は、KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計（監視 DB の一貫性確保）。
    - 停止ハンドリング: プロジェクトルート下 `data/stop_requested.flag` により正常終了。
    - プロセス優先度を起動時に "high" に設定。
  - `run_execution.py` を追加:
    - ExecutionEngine を起動するエントリポイント。
    - `KABUSYS_ENV=paper_trading` では MockBrokerClient を用い、paper_trading 専用 DB (`data/paper_trading.db` をデフォルト) に記録して本番 DB と分離。
    - Engine はスレッドで実行され、`data/stop_requested.flag` により停止指示を受け付ける。
    - PID ファイル (`data/execution.pid` など) の扱いに対応。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 / モニタリング
  - 監視 DB 初期化ヘルパー `monitoring_db.init_monitoring_db` を利用する起動フローを整備（冪等に監視テーブルを作成）。
  - SystemMonitor の check ループに例外耐性を持たせ、例外発生時はログを残してポーリングを継続する実装（例外キャッチによるリカバリ）。

- 実行 / 発注エンジン周辺（骨格）
  - ExecutionEngine, EngineConfig、OrderManager、OrderRepository、Reconciler、RiskManager、RiskConfig 等の起動・組み立てフローを実装（Factory を介した BrokerClient の生成）。
  - RiskManager に初期設定値を用意（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - ExecutionEngine にて duckdb 接続を受け取り分析・ログ保存に利用する設計。

- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定: `select_candidates`（スコア降順・タイブレーク処理）。
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア全0 の場合は等重フォールバックと警告）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限: `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合、新規候補を除外。unknown セクターは無視）。
    - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" のマッピング、未知値は警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数計算: `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - リスクベース算出、単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer の考慮、残余配分ロジック等を実装。

- ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティ `setup_logging` を実装。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - `kabusys.utils.process_priority`:
    - Windows / POSIX の差分を吸収してプロセス優先度設定（`set_process_priority`）および CPU affinity 設定（`set_cpu_affinity`）を提供。
    - アクセス拒否や未実装状況では警告を出して安全にスキップ。

- ツール / レポート
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成 CLI を実装。期間指定（--from/--to）や DB パス指定（--db）に対応。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）、リスク却下数 などを集計。
    - 判定閾値を定義（例: 稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 レイテンシ <= 200 ms）。
    - P95 計算、日付フィルタ生成、データ欠損時の N/A 処理を備える。

- 解析 / リサーチ
  - `kabusys.research.factor_research`（設計/初期実装）:
    - DuckDB を用いたファクター計算モジュールの骨格を実装（Momentum / Value / Volatility / Liquidity を計画）。
    - モメンタム計算 (`calc_momentum`) のインターフェースと計算方針（1M/3M/6M リターン、MA200 偏差）を記述（実装途中のファイルあり、スキャン範囲等の定数を定義）。

### 改善 (Changed)

- ログ出力の標準化:
  - すべての起動スクリプトから `setup_logging(app_name=...)` を呼び出すことでログ設定を統一。
  - コンソール出力に stdout を使用することで、cron 等からのリダイレクト操作を想定。

### 修正 (Fixed)

- 起動/終了ハンドリング:
  - 停止フラグファイル（data/stop_requested.flag）を用いた安全な停止制御を導入し、強制プロセス停止を避ける。

### ドキュメント (Documentation)

- 各モジュールに docstring を充実させ、設計意図・入力出力・制約・TODO を明記。
  - PortfolioConstruction.md、StrategyModel.md 等の参照を記載（外部ドキュメント参照箇所）。
  - config_setup と validate_config に使い方を README 的に記載。

### 既知の制約 / TODO

- research.factor_research の実装が途中（ファイル末尾が切れている/続き実装が必要）。
- position_sizing の価格フォールバック（price が欠損時の取り扱い）は TODO コメントとして残留。
- 将来的に銘柄別の lot_size 管理や、より柔軟なコスト推定（手数料/スリッページ）を導入予定。
- 一部の機能（例: BrokerClient の実装、ExecutionEngine の詳細ロジック、SystemMonitor の内部）はこのリリースでは骨格・統合点に重点を置いており、個別モジュールの拡充が必要。

---

配布・導入時の注意:
- .env は決してリポジトリにコミットしないでください（config_setup にも警告あり）。
- 本番運用時は KABUSYS_ENV=live の設定と LINE 通知設定等を必ず確認してください（validate_config の live ガード参照）。
- ログディレクトリや DB パスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、パーミッション等により作成に失敗する可能性があります。

以上。