# Changelog

すべての重要な変更を Keep a Changelog の形式で記録します。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能・ユーティリティを実装しました。

### Added
- パッケージ情報
  - パッケージバージョンを追加: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / 実行系
  - run_execution 起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するエントリポイントを提供。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの管理に対応。
  - run_monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実行するエントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境に依らず本番用の sqlite_path を利用する設計。
    - 停止フラグ検知でループを安全に終了。

- 設定管理（環境変数・.env 周り）
  - Settings クラス（src/kabusys/config.py）
    - 環境変数からの設定取得を集約（DB パス、KABUSYS_ENV、ログレベル、各 API トークンなど）。
    - env 値・LOG_LEVEL・PAPER_FILL_MODE 等に対するバリデーションを実装。PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）の取得、PID / kill flag パス、しきい値（CPU/Memory/Disk）などをプロパティで提供。
  - .env 自動読み込み機能
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動で読み込む（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - パーサは `export KEY=val`、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントの扱い、コメント行の無視などに対応。
    - .env の読み込み時、OS 環境変数は保護（protected）され、overwrite の挙動を制御可能。

- 設定関連 CLI
  - 設定検証コマンド（src/kabusys/validate_config.py）
    - `.env` と config/*.yaml の基本的検証を行う CLI。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML のパース検査（PyYAML がある場合）を実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定のチェック、KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告も失敗として扱う。
  - 設定ウィザード（src/kabusys/config_setup.py）
    - 対話式で .env の初期作成・更新を支援するウィザード。
    - 入力補助（選択肢、デフォルト、シークレットマスク表示）、既存 .env の読み込み、確認後の .env 書き出し機能を提供。
    - 書式化されたテンプレートで .env を出力（Git にコミットしない旨のヘッダ付き）。

- ロギング・プロセスユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティ。
    - 既存ハンドラのクリア、ログレベル・ログディレクトリ解決（引数 > 環境変数 > デフォルト）、ファイルハンドラ作成失敗時のフォールバックなどを実装。
    - stdout を使用することで cron 等での stdout/stderr 集約に対応。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX 両対応でプロセス優先度を設定する機能を提供（"high" / "normal" / "low"）。
    - CPU affinity 固定の補助関数を提供。権限不足などで失敗した場合は警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定（select_candidates: スコア降順・tie-breaker: signal_rank）と配分重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分にフォールバックして警告。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター別エクスポージャを計算して上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外として扱う。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対する乗数を返却（未定義レジームは警告を出して 1.0 にフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - 株数算出ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - リスクベース算出（risk_pct, stop_loss_pct を考慮）や等分配/スコア加重に基づく算出、単元株（lot_size）丸め、1銘柄上限や aggregate cap（available_cash）に沿ったスケーリング、cost_buffer を考慮した保守的見積り等を実装。
    - スケールダウン後の再配分ロジック（残差を元に lot 単位で追加配分）を実装し再現性を確保。

- 分析 / レポートツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
    - paper_trading の SQLite DB（デフォルト: data/paper_trading.db）からレポートを生成する CLI。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg / max / P95）を算出し、閾値に基づき PASS/FAIL を出力。
    - P95 計算、日付フィルタ（--from/--to）、DB 存在チェックに対応。

- 研究用ファクター計算（部分実装）
  - research/factor_research（src/kabusys/research/factor_research.py）
    - DuckDB を利用したファクター計算基盤を準備。Momentum/Value/Volatility/Liquidity を計算する設計で、prices_daily / raw_financials テーブル参照の純粋関数として設計。

- DB 初期化ユーティリティ呼び出し
  - 監視用 DB のスキーマ確保に `init_monitoring_db` を起動スクリプトから呼び出してテーブル存在を保証（冪等）。

### Changed
- ログハンドラ設定の一貫化
  - 全エントリポイントで共通の setup_logging を呼び出すことでログ出力方式を統一。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサでクォート内のエスケープや inline コメント処理、`export` プレフィックス対応などを行い、より柔軟に .env を扱えるようにした。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring 内で環境変数が不正（0/負数/非数）の場合にログで警告を出し、デフォルトにフォールバックするように修正。

### Security
- .env 取り扱いに関する注意喚起
  - config_setup に .env を絶対に Git にコミットしない旨のヘッダを追加。

### Notes / Caveats
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML など）に依存します。環境により動作しない場合は該当ライブラリのインストールを確認してください。
- process priority / CPU affinity の設定は OS と権限に依存します。権限不足等で設定できない場合は警告を出してスキップします。
- position_sizing で price が欠損（0.0）だとエクスポージャが過少見積りされる可能性がある旨の TODO コメントあり。将来的に価格フォールバックを導入予定です。
- research/factor_research は計算ロジックの実装が続いており、一部未完または補完が必要な箇所があります（続き実装予定）。

---

変更点に不明点や補足が必要であれば、該当のファイル/機能に対してさらに詳細な説明や利用手順、リリースノートへの反映を作成します。