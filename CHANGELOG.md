# Changelog

すべての変更は Keep a Changelog の慣習に準拠しています。  
セマンティックバージョニングを使用します: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。主な機能・実装は以下の通りです。

### Added
- 全体
  - パッケージ初期実装を追加。バージョンは `__version__ = "0.1.0"`。
  - 共通設定管理、起動スクリプト、ユーティリティ、ポートフォリオ構築、リサーチ、運用ツール群を含む。
- 設定・起動関連
  - Settings クラス実装（`kabusys.config`）
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - 環境変数の優先度: OS 環境変数 > .env.local > .env。
    - 必須/選択的設定プロパティ（J-Quants, kabu API, DB パス, LOG_LEVEL, KABUSYS_ENV 等）。
    - `paper_fill_mode` のバリデーション（instant/partial/never/reject）。
    - `env`, `log_level` などの値検証ロジック。
  - 設定ウィザード CLI（`kabusys.config_setup`）
    - 対話的に .env を生成・更新するウィザード。
    - シークレット項目はマスク表示。生成後に確認して保存。
  - 設定検証 CLI（`kabusys.validate_config`）
    - .env と config/*.yaml の存在・基本整合性をチェックするツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パース検証（PyYAML がある場合）。
    - `--strict` オプションで警告を失敗扱いにする機能。
- 起動スクリプト
  - 実行エンジンスクリプト（`kabusys.run_execution`）
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合、本番 DB と完全に分離した paper_trading 用 SQLite を使用（`PAPER_TRADING_SQLITE_PATH`、デフォルト: `data/paper_trading.db`）。
    - BrokerClientFactory によるブローカークライアント生成（paper/live に依存した実装分離を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine` を起動。エンジンはスレッドで実行され、`data/stop_requested.flag` による外部停止をサポート。
    - エンジン用 PID ファイルを `data/execution.pid` に保存（設定経由で変更可）。
    - RiskManager のデフォルト設定値を実装（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - 監視スクリプト（`kabusys.run_monitoring`）
    - SystemMonitor のポーリングループを起動。デフォルトポーリング間隔 60 秒で、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。
    - 監視は KABUSYS_ENV に関係なく本番用の sqlite_path を使用（監視 DB を共通で参照）。
    - 外部停止は `data/stop_requested.flag` を検知して安全終了。
    - check_once() 内の例外は捕捉してログ出力し、ループを継続する設計。
- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（`kabusys.utils.logging_setup`）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。
    - ログディレクトリは引数 > LOG_DIR 環境変数 > デフォルト `logs/` の順で解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみ行う。
    - 既存ハンドラは一旦 flush/close の上でクリアして再設定（重複設定防止）。
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収して `set_process_priority(level)` を提供（high/normal/low）。
    - `set_cpu_affinity(cpu_count)` による CPU 固定も実装。権限不足や未対応環境では警告を出してフォールバック。
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定・重み計算（`portfolio_builder`）
    - シグナルのスコア順ソート、上位 N 選定（タイブレークは signal_rank）。
    - 等配分（calc_equal_weights）とスコア加重（calc_score_weights）。全スコアが 0 の場合に等配分へフォールバック。
  - セクター集中制限・レジーム乗数（`risk_adjustment`）
    - apply_sector_cap: 既存保有をセクター別に集計し、指定上限を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market_regime（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは警告後 1.0 でフォールバック）。
  - 株数決定・リスク制限・単元丸め（`position_sizing`）
    - allocation_method に応じた発注株数決定:
      - "risk_based": risk_pct / (price * stop_loss_pct) に基づき株数を計算
      - "equal"/"score": weight に基づく配分
    - 1 銘柄上限（max_position_pct）、lot_size（単元）丸め、コストバッファ(cost_buffer) を考慮した aggregate cap（利用可能現金を超える場合のスケーリングと再配分アルゴリズム）を実装。
- リサーチ
  - ファクター計算モジュール（`kabusys.research.factor_research`）
    - モメンタム・ボラティリティ・流動性等のファクターを DuckDB 経由で計算するための骨子（モメンタム計算関数の実装開始）。
- 運用ツール
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）
    - paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）から統計を抽出してレポートを生成。
    - 稼働率（uptime）、注文成立率（fill rate）、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する閾値を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200ms など）。
    - `--from` / `--to` / `--db` オプションをサポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- 環境変数・ファイルパス
  - .env を使用する場合、プロジェクトルートが .git または pyproject.toml で検出される必要があります（検出できない場合は自動ロードをスキップします）。
  - OS 環境変数が優先されます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- paper_trading
  - ペーパートレード時は paper_trading 用の SQLite を使用するようになっており、本番 DB とは明確に分離されます。運用時に誤って本番 DB を上書きしないよう注意してください。
- ログ
  - ログはデフォルトで stdout と `logs/<app_name>.log` に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合でもサービスは継続します（ファイル出力のみ無効化される）。
- 権限
  - プロセス優先度や CPU affinity の設定は OS 権限に依存します。権限不足時は warn を出して処理を継続します。

---

開発・運用中に追加の変更があれば、この CHANGELOG に追記してください。