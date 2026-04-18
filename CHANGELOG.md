# Changelog

すべての重要な変更点はここに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  

現在のリリース履歴:

- [Unreleased] は未リリースの変更用（ここでは空）
- 各リリースはバージョンと日付を記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」のコア機能・ユーティリティ群をまとめて追加しました。

### Added
- 基本情報
  - パッケージ初期バージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB を参照）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離。
    - PID ファイル管理（data/execution.pid）と停止フラグ検知で安全に停止処理を実行。
    - スレッドベースで ExecutionEngine を実行し、停止フラグで engine.stop() を呼び出して終了。
- 設定管理・ユーティリティ
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）。
    - .env の自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env 行パーサーで export 形式、クォート、エスケープ、インラインコメントの扱いを実装。
    - 各種設定プロパティ（DB パス、ログレベル、環境判定フラグ、監視閾値、paper_trading の設定など）を提供。値検証（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック）を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 秘匿値のマスク表示、選択肢・デフォルト提示、既存 .env の読み込み・再利用、保存時のテンプレート出力を実装。
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合）パースチェック、本番環境向け追加警告等。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補抽出。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、上限を超えるセクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: market regime に対する資金乗数を提供（bull/neutral/bear をマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数計算ロジックを実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を用いた保守的なコスト見積、残差処理（fractional remainder）による追加配分ロジックを実装。
- 実行系コンポーネント（起動スクリプトから組み立てる部品）
  - Execution 側で使う OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て呼び出し箇所を run_execution に追加（依存注入の流れを明示）。
  - RiskManager に渡すデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 関連、max_drawdown、initial_portfolio_value=broker.get_available_cash()）を定義。
- 監視 DB 初期化ヘルパー呼び出し
  - run_monitoring / run_execution の両方で監視テーブルの存在を保証する init_monitoring_db() 呼び出しを追加（冪等）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通関数 setup_logging を追加。
    - LOG_DIR/LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバック、既存ハンドラのクリーンアップ等を実装。
  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定ヘルパーを追加。失敗時は警告してスキップ。
- ツール類
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）等を集計して PASS/FAIL を判定するレポートを標準出力へ出力。
    - P95 計算、日付フィルタ（--from / --to）、DB パス解決（--db / 環境変数）に対応。閾値はソース内定義で変更可能。
- 研究用モジュールの雛形
  - research/factor_research.py: DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）モジュールの骨子を追加。主に仕様と一部モメンタム計算の定数が実装済み（実装途中ファイルあり）。
- パッケージのエクスポート整理
  - portfolio パッケージの __init__ で主要関数をエクスポート。

### Changed
- N/A（初回リリースのため既存の変更点なし）

### Fixed
- N/A（初回リリースのため修正履歴なし）

### Removed
- N/A

### Security
- 環境変数管理で .env をデフォルトで Git にコミットしない旨の注意をテンプレートに追加（config_setup の出力メッセージ）。

---

補足:
- 本リリースは初期機能群の実装を目的としたもので、Strategy モデルの詳細実装や ExecutionEngine の内部ロジック（個別の注文アルゴリズム等）は別モジュール・別コミットで追加・改善される想定です。
- 実運用前に validate_config を実行し、環境変数・構成ファイルの検証を行ってください。config_setup により .env の初期作成が可能です。