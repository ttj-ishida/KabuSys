# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-18
初期リリース

### 追加
- 基本アプリケーションパッケージを追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`
  - エクスポート: `kabusys` に `data`, `strategy`, `execution`, `monitoring` を想定

- 実行系・監視関連スクリプト
  - run_execution: `python -m kabusys.run_execution` により ExecutionEngine を起動するスクリプトを追加
    - 起動時にプロセス優先度を "high" に設定
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して paper 専用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止
    - 実行用 PID ファイルのサポート（data/execution.pid）
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててスレッドで実行
    - リスク管理のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み

  - run_monitoring: `python -m kabusys.run_monitoring` により SystemMonitor のポーリングループを起動するスクリプトを追加
    - 起動時にプロセス優先度を "high" に設定
    - 監視は環境にかかわらず本番用の sqlite_path（Settings.sqlite_path）を使用
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了
    - `monitoring_db.init_monitoring_db` を呼んでテーブル存在を担保（冪等）

- 設定・環境管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env 自動ロード（`.env` → `.env.local`、OS 環境変数を保護）
    - 強力な .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応）
    - Settings クラスを提供し、環境変数をプロパティ経由で型変換・検証付きで取得
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PID / Kill flag 等のパス
      - 各種しきい値（CPU/MEM/DISK）
      - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）
      - KABUSYS_ENV / LOG_LEVEL の値検証と bool 判定プロパティ（is_live / is_paper / is_dev）

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援
    - シークレット項目は表示時にマスク化、デフォルト/既存値の再利用、保存前の確認を実装
    - `.env` 書き込みテンプレートを提供（Git にコミットしない旨の注意含む）
    - CLI 例: `python -m kabusys.config_setup`

  - validate_config.py
    - 起動前チェック CLI を追加
    - 必須環境変数の有無、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けのガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）などを報告
    - `--strict` オプションで警告を失敗扱いにできる
    - CLI 例: `python -m kabusys.validate_config`

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログセットアップ関数 `setup_logging(app_name, log_dir, level)` を実装
    - StreamHandler（stdout）と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続
    - stdout を使用することでタスクスケジューラや cron の出力統合を想定

  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定 `set_process_priority(level)` を実装（Windows / POSIX をサポート）
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を提供
    - 認可エラーや未対応プラットフォームでは警告を出して安全にフォールバック

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - buy シグナルから候補選定 `select_candidates`
    - 等金額配分 `calc_equal_weights`
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）

  - portfolio/risk_adjustment.py
    - セクター集中排除 `apply_sector_cap`（既存保有と価格マップを元にセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外）
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 にフォールバック）

  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 `calc_position_sizes`
      - allocation_method: "risk_based" / "equal" / "score" に対応
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）を考慮
      - cost_buffer による保守的なコスト見積もりとスケーリング・残差配分ロジック実装
      - 価格欠損時のスキップやログ出力を実装

  - portfolio パッケージのトップレベル export を実装（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py を追加（DuckDB 接続を受けてモメンタム、ボラティリティ、バリュー等のファクターを計算する設計）
    - モメンタム計算（期間: 1M/3M/6M, MA200乖離）等を想定
    - DuckDB の `prices_daily` / `raw_financials` を参照する方針
    - （ファイルは途中で終端している箇所あり — 実装の継続が必要）

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果を SQLite（デフォルト data/paper_trading.db）から集計して検証レポートを生成
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg/max/P95）など
    - デフォルト基準（閾値）を定義し、PASS/FAIL を判定
    - CLI 例: `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

### 変更
- 監視・実行プロセスの起動手順を統一
  - どちらのスクリプトも最初に `setup_logging(...); set_process_priority("high")` を呼び、ログ・プロセス優先度の初期化を共通化

- .env の自動読み込み方針
  - 自動ロードはデフォルトで有効（プロジェクトルート検出に成功した場合）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化可能

### 既知の注意点 / TODO
- research/factor_research.py は一部未完（先頭で処理が途中終了している）。完全な実装が必要。
- position_sizing の価格欠損 (price == 0.0) によるエクスポージャー過少見積りについてはコメントで将来的なフォールバック（前日終値など）が言及されているが現状未実装。
- run_monitoring は監視 DB に Settings.sqlite_path を環境にかかわらず使用する仕様（意図的）。運用時の DB 分離に注意。
- file/directory を作成する操作（ログディレクトリ、data ディレクトリ等）が実行環境で権限不足だとファイル出力が無効化される場合がある。ログ設定および validate_config の警告を参照のこと。

### 互換性（重要な環境変数・ファイルパス）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。1 未満や非数はデフォルトへフォールバック。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（run_execution / tools で使用）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（不正値は例外）
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（不正値は例外）
- LOG_DIR / LOG_LEVEL: ログ出力先・レベルの設定
- KILL_FLAG_CLEAR_ON_START: 本番ではデフォルト 0 を推奨（validate_config で警告）

---

今後の予定:
- research/factor_research の完成
- ExecutionEngine / SystemMonitor 周りの統合テスト強化
- 銘柄別 lot_size や手数料モデルの適用拡張

-----  
注: 本 CHANGELOG は与えられたソースコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある可能性があります。