# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
    - 実行中の停止制御に stop_requested.flag（data/execution.pid / data/stop_requested.flag）を使用。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を利用）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトへフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視用テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理ユーティリティを追加
  - config.py: .env 自動読み込み（.env, .env.local）ロジック、環境変数パース（クォート・エスケープ・コメント対応）、Settings クラスを提供。
    - 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種設定プロパティ（DB パス、PID パス、閾値、PAPER_FILL_MODE 等）を提供し、バリデーションを行う。
    - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）。
- 設定支援・検証 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を生成・更新する機能を提供。シークレット項目はマスク表示。
  - validate_config.py: .env と config/*.yaml の事前検証ツール。--strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML が無ければスキップ）などを実行。
    - 本番（live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を追加。
    - 標準出力（stdout）用 StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日分保持）をルートロガーに設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの解決順と引数での上書き対応。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、アクセス権限不足等の例外は警告として扱う。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築ロジック（純粋関数群）を追加
  - portfolio/portfolio_builder.py:
    - select_candidates: スコアでソートして上位 N 件を選択。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重配分。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑制するフィルタ。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を計算。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の配分アルゴリズム、単元（lot_size）丸め、aggregate cap（available_cash）に基づくスケーリング、cost_buffer 考慮の実装。
    - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）を引数で柔軟に設定可能。
- 研究・分析用モジュール（骨子）を追加
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組み（モメンタム / MA200 / ATR 等の計算方針、定数定義）を追加（関数の実装が途中まで含まれる）。
- ツールを追加
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成する CLI。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を行う（デフォルト閾値を定義）。
    - 日付フィルタ（--from / --to）対応。
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。主要エクスポートパッケージを __all__ で定義。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Deprecated
- （初回リリースのため履歴なし）

### Removed
- （初回リリースのため履歴なし）

### Security
- （初回リリースのため履歴なし）

---

注記:
- run_execution/run_monitoring はそれぞれプロセス優先度を高く設定して起動する設計です。実行環境によっては権限の関係で警告が出ますが、実行自体は継続されます。
- .env や秘密情報（トークン・パスワード）は .env ファイルに保存しないよう注意してください（config_setup でも警告を表示）。
- DuckDB/SQLite 両方を使用する設計です。データベースパスは Settings 経由で環境変数により柔軟に指定できます。