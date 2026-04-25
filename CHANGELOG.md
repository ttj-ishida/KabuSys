# Changelog

すべての重要な変更点をこのファイルに記録します。  
この変更履歴は「Keep a Changelog」形式に準拠しています。  
安定版リリースごとにエントリを追加してください。

フォーマット:
- Unreleased: 現在開発中の変更点
- リリース: YYYY-MM-DD の日付を付与

## [Unreleased]

### Added
- run_monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループを起動する CLI スクリプトを追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - Monitoring 用 DB の初期化を起動時に行う（init_monitoring_db を呼び出し）。
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する挙動を明示。

- run_execution 起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine を起動する CLI スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てと ExecutionEngine の起動/停止制御を実装。
  - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル管理に対応。

- 環境設定・検証ツール
  - 設定管理モジュール（src/kabusys/config.py）
    - .env ファイルの自動読み込み（.env, .env.local）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パースの強化（export 構文、クォート、インラインコメント処理等）。
    - 各種設定値（DB パス、LINE トークン、KABUSYS_ENV 等）を Settings クラス経由で取得・バリデーション。
    - PAPER_FILL_MODE の検証など、いくつかの環境変数に対する整合チェックを追加。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env および config/*.yaml の存在・簡易パース検証を行うコマンドを追加。`--strict` で警告を FAIL 扱いにできる。
    - 本番向けガード（KABUSYS_ENV=live 時のチェックや LINE 通知設定未設定の警告など）を実装。
  - 環境設定ウィザード（src/kabusys/config_setup.py）
    - 対話式に .env を作成・更新するウィザードを追加。シークレット項目はマスク表示。生成テンプレートの書き込みを行う。

- ロギング・プロセスユーティリティ（src/kabusys/utils）
  - ロギングセットアップユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL など環境変数で制御可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を追加（psutil を利用、権限不足時は警告でスキップ）。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio）
  - 銘柄選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順で候補を選別。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等配分にフォールバック。
  - セクター制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し上限超過セクターの候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - 株数決定・単元丸め（position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の各配分方式をサポート。lot_size（単元）に基づく丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的な見積り。

- 研究・分析
  - factor_research の骨組み（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算用ユーティリティの設計・定数を追加（DuckDB を用いた prices_daily/raw_financials 参照を想定）。

- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite を読み込み、稼働率、注文成功率、送信率、レイテンシ（P95）等を計算してレポートを stdout に出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90% 等）を定義し PASS/FAIL 判定を行う。
    - コマンドライン引数で日付範囲や DB パスを指定可能。

### Changed
- 初期設計として、監視・実行エンジンは起動時にプロセス優先度を "high" に設定するように変更（setup_logging 実行後に呼び出し）。
- logging_setup: コンソールは stdout を使用する仕様に統一（cron/タスクスケジューラでの扱いを考慮）。

### Fixed
- .env パーサーの堅牢化（引用符内のエスケープ処理、export プレフィックス、インラインコメント取り扱いなど）により実運用でのパース誤りを低減。

### Notes
- 設定・データファイル（.env, data/*.db, logs/*）はデフォルトでプロジェクト下のパスに作成されるため、運用時は適切なパス設定やファイル管理（.env を Git にコミットしない等）を行ってください。

---

## [0.1.0] - 2026-04-25

初回公開リリース。上記 Unreleased の内容を含む最初の安定版です。

### Added
- パッケージ基本情報（src/kabusys/__init__.py）にバージョン 0.1.0 を設定。
- 次の主要機能を実装・公開:
  - 実行/監視起動スクリプト: run_execution, run_monitoring
  - 環境設定管理: config, config_setup ウィザード
  - 設定検証 CLI: validate_config
  - ロギングとプロセス管理ユーティリティ: logging_setup, process_priority
  - ポートフォリオ構築ライブラリ: portfolio_builder, risk_adjustment, position_sizing
  - 研究用のファクター計算スケルトン: research/factor_research
  - ペーパートレード検証ツール: tools/paper_verification_report

### Changed
- 主要コンポーネントは外部 DB（SQLite / DuckDB）を利用する設計。paper_trading 環境では paper_sqlite_path を使用して本番データと分離。
- ログの回転・保管は日次ローテーション（30 日保持）をデフォルトとした。

### Fixed
- .env 自動読み込みロジックをプロジェクトルート検出（.git または pyproject.toml）に基づく実装に改善。プロジェクト外での誤読を回避。

### Security
- 機密情報 (.env 内のシークレット) は config_setup でマスクされた状態で表示し、.env を Git にコミットしないようドキュメント化。

---

過去のリリースや個別のチケット参照が必要な場合は、ソース管理システム（Git）のコミット履歴および PR コメントを参照してください。