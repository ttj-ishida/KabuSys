# CHANGELOG

すべての notable な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-18
最初の公開リリース。本バージョンは、日本株自動売買システム KabuSys の基盤モジュール群、起動スクリプト、設定ユーティリティ、ポートフォリオ構築ロジック、検証ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、ペーパートレード用の専用 SQLite（data/paper_trading.db）を使用する（本番 DB と分離）。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドでセッションを実行。停止フラグ（data/stop_requested.flag）を監視して優雅に終了。
    - エンジン用 PID ファイル管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データを統一して扱うため）。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。

- 設定管理・ウィザード・検証
  - config.py
    - 環境変数取得ラッパー `Settings` を追加。プロパティベースで設定値を取得・検証。
    - .env の自動読み込み機構（プロジェクトルート検出：.git または pyproject.toml）。OS 環境変数を保護して `.env.local` → `.env` をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - `paper_fill_mode` 等の値検証（有効値チェック）を実装。
    - デフォルトパスやしきい値（CPU/MEMORY/DISK）などをプロパティとして提供。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。各種設定項目の説明・デフォルト値・シークレット扱いに対応。
    - .env の読み書き機能を提供し、ユーザ確認後にファイルへ書き出す。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が利用可能な場合）や本番環境向けガードチェックを実装。
    - `--strict` オプションで警告も失敗扱いに可能。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共有できるロギング初期化関数 `setup_logging()` を追加。
    - stdout へ出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて、デフォルトで logs/<app_name>.log に出力（30 日保持）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで動作。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定 `set_process_priority()` を追加（Windows / POSIX 対応。失敗時は警告でスキップ）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity()` を追加。
    - 起動スクリプトは起動直後にプロセス優先度を "high" に設定する実装を含む。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates`（スコア降順、タイブレークは signal_rank）を追加。
    - 重み計算 `calc_equal_weights`（等分配）/ `calc_score_weights`（スコア正規化、全スコアが 0 の場合は等分配へフォールバック）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を追加（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear マッピング、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数算出 `calc_position_sizes` を追加。
    - 複数の allocation_method をサポート（risk_based / equal / score）。
    - 単元株（lot_size）に丸め、1 銘柄上限・全体の利用可能現金に対する aggregate cap を実装。資金超過時はスケーリングと端数処理（残余キャッシュで lot 単位追加）により調整。
    - cost_buffer（手数料・スリッページ見積り）を考慮。

- 研究・ファクター計算基盤
  - research/factor_research.py（骨格）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いたモメンタム／Value／Volatility／Liquidity ファクター群を計算する設計を実装（モジュールの大枠、定数、calc_momentum の導入を含む。計算実装は継続開発予定）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング結果の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を行う。
    - CLI から期間指定（--from, --to）と DB パス指定（--db）を受け付け、PAPER_TRADING_SQLITE_PATH 環境変数に対応。
    - 補助関数（P95 計算、日付フィルタ生成、フォーマット関数）を含む。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Deprecated
- （新規リリースのため該当なし）

### Security
- （新規リリースのため該当なし）

---

## 設定・運用メモ（重要）
- 自動 .env ロード:
  - デフォルトでプロジェクトルート（.git または pyproject.toml を検出）から .env を読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- 主要な環境変数（例とデフォルト）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - MONITOR_POLL_INTERVAL (run_monitoring 用、default: 60)
  - PAPER_FILL_MODE (paper_trading 用、default: "instant") — 有効値: instant, partial, never, reject
- 監視・停止フラグ:
  - run_monitoring/run_execution はプロジェクトの data/stop_requested.flag を監視して優雅に停止します。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で出力先を変更可能。ディレクトリ作成に失敗した場合はコンソール出力のみにフォールバックします。
- Paper Trading と本番データの分離:
  - paper_trading 実行時は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し、本番 SQLite（SQLITE_PATH）とは分離されます。

---

作者・コントリビューション: 初期実装。バグ報告／改善提案は Issue を通じてお願いします。