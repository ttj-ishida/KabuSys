# CHANGELOG

すべての notable な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
この CHANGELOG は、与えられたコードベースのソースから推測して作成しています。

全般的な注意
- 各項目では該当する主要なモジュール / スクリプト名を併記しています。
- 実装の詳細はソースコードの docstring と挙動に基づき推測しています。

## [Unreleased]

## [0.1.0] - 2026-04-21
初期リリース。システム全体のコアコンポーネント、ユーティリティ、CLI、ポートフォリオ構築ロジック、監視・実行の起動スクリプト、ペーパートレード検証ツールなどを提供。

### Added
- 基本パッケージ定義
  - パッケージメタデータ（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 実行系ランチャー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する仕組みを実装。
    - BrokerClientFactory を利用して実際のブローカーまたは MockBrokerClient（paper_trading）を選択。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）検出時に安全に停止するループ制御を実装。
    - PID ファイル管理（data/execution.pid）を行うエントリポイントを提供。

  - 監視（モニタ）起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を定期ポーリングで起動するランナー。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止フラグ検知でループを終了し、例外発生時はログを残して次ポーリングまで待機する堅牢化。

- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数のラッパー（DB パス、API トークン、監視閾値、実行環境判定など）。
    - KABUSYS_ENV や LOG_LEVEL の妥当性チェック、paper_trading 用の paper_sqlite_path、paper_fill_mode の検証を実装。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。OS 環境変数は保護される（上書き制御）。

  - .env 初期設定ウィザード（src/kabusys/config_setup.py）
    - 対話式で .env を作成・更新する CLI。シークレット項目はマスク表示、デフォルト値・選択肢を提示。
    - 保存前に設定確認を行い、ファイルへ書き出す。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml ファイルの存在・パース（PyYAML が未インストールの場合は警告）をチェック。
    - --strict モードで警告をエラー扱いにできる。

- ユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーへ設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップし stdout のみで継続するフォールバック実装。
    - ログレベル解決順や log_dir 解決順を明示。

  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 許可エラーや未対応環境は警告ロギングでフォールバック。

- ポートフォリオ構築ライブラリ（純関数群、DB非依存）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、signal_rank でのタイブレーク。
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等分配にフォールバック）。

  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーから上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告の上 1.0 にフォールバック。

  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数決定（risk_based, equal, score をサポート）。
    - risk_based: risk_pct, stop_loss_pct を使ったベースシェア計算、単元株（lot_size）で丸め。
    - aggregate cap（利用可能現金 available_cash を超える場合）のスケーリング実装（ロット単位で残差考慮して再配分）。

  - パッケージエクスポート（src/kabusys/portfolio/__init__.py）

- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH）から各種指標を集計してレポートを標準出力に出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算ユーティリティ、期間フィルタ（--from/--to）、DB 存在チェック、しきい値による PASS/FAIL 判定を実装。
    - データが不足する場合は N/A を出力するなどの堅牢化。

- 研究用ファクター計算（初期実装の一部）  
  - (src/kabusys/research/factor_research.py) モメンタム等のファクター計算基盤の骨組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（実装は一部で継続中）

- DB 初期化ユーティリティ参照
  - init_monitoring_db が監視テーブルの存在を保証するために使用されている（run_monitoring/run_execution）。

- その他
  - stop_requested.flag / execution.pid 等のファイルによるプロセス制御（停止フラグ、PID 管理）を導入。
  - 環境変数のパースロジック（_parse_env_line）でクォートや export 形式、コメントの扱いを工夫して安全に .env をロード。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 秘密情報（J-Quants トークンや KABU_API_PASSWORD）は Settings 経由で環境変数を参照し、config_setup ウィザードではシークレット項目をマスクして扱う旨をドキュメントに明示。

---

注: 本 CHANGELOG は与えられたソースコードの内容からの推測に基づいて作成しています。内部実装のさらに細かな変更点や外部モジュール（ExecutionEngine 内部、BrokerClient 実装など）の履歴は、該当ソースが与えられていないため記載していません。必要であれば、個別ファイルごとのより詳細な変更履歴（関数レベルの差分や TODO/制約事項）も生成します。