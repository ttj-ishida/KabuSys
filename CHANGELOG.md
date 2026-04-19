# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: このリポジトリの初期リリースを表す変更ログです。ファイル内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期実装を追加
  - src/kabusys/__init__.py
    - バージョンを `0.1.0` に設定。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB は環境に依らず本番の `sqlite_path` を使用。
    - 停止フラグ（data/stop_requested.flag）検知および例外ハンドリングを実装。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知と PID ファイル管理（data/execution.pid）を実装。
    - ExecutionEngine をデーモンスレッドで起動し、停止フラグで停止させるループを実装。

- 設定読み込み・管理
  - src/kabusys/config.py
    - 環境変数と .env/.env.local の自動読み込み（OS 環境変数を保護）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）。
    - 各種設定プロパティを持つ `Settings` クラスを追加（DB パス、API トークン、PID / kill flag パス、しきい値等）。
    - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）と `paper_sqlite_path` サポート。
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックと bool プロパティ（is_live, is_paper, is_dev）。

- 設定 / 検証 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - J-Quants / kabuステーション / DB / LINE / ログなど主要設定項目のプロンプトと .env 書き込み機能を実装。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコアがゼロの場合のフォールバック（等金額）警告を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。既存ポジションのセクター別エクスポージャ計算と候補除外ロジックを提供。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（"bull"/"neutral"/"bear" に対応、未知レジームはフォールバックし警告）。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の allocation method をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、コストバッファ（手数料・スリッページ推定）を考慮したスケーリング、残差処理ロジックを含む。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - アプリ共通のログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合のフォールバック（コンソール出力のみ）。
    - LOG_LEVEL / LOG_DIR の解決ルールを実装。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX の差分を吸収）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS 時の安全なフォールバック（警告ログ）を実装。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義して PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と DB パスの指定（--db / 環境変数）をサポート。
    - P95 計算、欠損値（N/A）ハンドリング、DB が存在しない場合のメッセージ表示を実装。

- 研究用モジュール（ファクター計算）
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算モジュールを追加（duckdb 接続を受け、prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、ボリューム指標等の計算を想定した設計（関数 calc_momentum 等、未完の実装が含まれる可能性あり）。

### Changed
- 環境自動ロードの挙動
  - src/kabusys/config.py
    - プロジェクトルートが検出可能なときに .env / .env.local を自動で読み込むロジックを実装（OS 環境変数は保護）。
    - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能。

### Fixed
- なし（初期リリースのため該当なし）

### Notes / Migration
- 起動方法（例）
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]

- 環境変数とファイルパス
  - Paper Trading を行う場合、`KABUSYS_ENV=paper_trading` にすると paper データベース（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）が使われ、本番 DB と完全分離される点に注意してください。
  - Kill / Stop フラグはデフォルトで data/*.flag を参照します（プロジェクトルート検出に依存）。

- ログ
  - デフォルトでは logs/ 以下に日次ローテーションのログファイルが作成されます。ログディレクトリ作成に失敗した場合は標準出力のみでの出力になります。

---

以上。追加・変更点はコードベースからの推測に基づき記載しています。実際の変更履歴として利用する場合は必要に応じて日付・担当者・詳細差分を調整してください。