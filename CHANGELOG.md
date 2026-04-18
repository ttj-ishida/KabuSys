CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
-------------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本ライブラリの初期実装を追加（初回リリース）。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止制御はプロジェクト直下の data/stop_requested.flag を監視して行う。
      - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する実装。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading の場合は専用の Mock ブローカ/専用 SQLite（data/paper_trading.db）を利用して本番 DB と分離。
      - 停止フラグおよび PID ファイル（data/execution.pid）をサポート。スレッドで engine.run_session を実行し、停止時に安全に停止処理を呼び出す。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機構（プロジェクトルートの検出: .git または pyproject.toml を基準）。
      - .env の行パースを堅牢化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
      - OS 環境変数を保護するための protected 上書きルールと KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ。
      - Settings クラスを提供し、環境変数の取得/検証を整理（J-Quants / kabu API / DB パス / 各種閾値等）。
      - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
  - 設定検証・セットアップ CLI
    - src/kabusys/validate_config.py
      - .env や config/*.yaml の不足・誤設定を検出する CLI を実装。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML があれば）や本番環境の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を行う。
      - --strict により警告を失敗扱いにできる。
    - src/kabusys/config_setup.py
      - .env 作成/更新を対話式で支援するウィザードを実装。既存 .env の読み込み、シークレット項目のマスク表示、確認して書き込み可能。
  - ロギング・プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 統一ログ設定ユーティリティを実装。
      - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。
      - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみ継続。
      - ログレベル・ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォームのプロセス優先度設定ユーティリティを実装（Windows / POSIX に対応）。
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。psutil を利用して実装。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
      - スコアが全て 0 の場合は等分配へフォールバック（警告ログ）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
      - セクター未知 ("unknown") の扱いや、レジームに応じた multiplier マップ（bull/neutral/bear）を定義。未知レジームは 1.0 にフォールバック。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、per-stock 上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ見積り）対応、残差に基づく追加配分ロジックを備える。
    - src/kabusys/portfolio/__init__.py
      - 上記 API をパッケージレベルでエクスポート。
  - 解析・リサーチ
    - src/kabusys/research/factor_research.py（モジュール開始。モメンタム等のファクター計算を目的に実装を開始）
      - DuckDB 接続を受けて prices_daily / raw_financials を参照し、モメンタムや MA200 乖離等を計算する設計。
      - （ファイル末尾に未完の実装が存在：calc_momentum の続きが未収録）
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレードの検証レポート生成スクリプトを実装。
      - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（P95 等）を集計し PASS/FAIL を判定する閾値を定義。
      - コマンドライン引数 --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先的に参照可能。

Changed
- 初期リリースにつき該当なし。

Fixed
- 初期リリースにつき該当なし。

Notes / 実装上の注意
- run_monitoring は Monitoring 用 DB 接続に settings.sqlite_path（本番用）を常に使用します。環境に依らず監視データは単一の監視 DB に集約されます。
- run_execution は paper_trading の場合に settings.paper_sqlite_path を使用して発注記録を本番 DB と分離します。
- .env 読み込みは自動実行されるが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト時などに使用）。
- logging_setup では stdout を StreamHandler に使うことで cron やスケジューラとの相性を考慮しています。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームの場合に警告を出し処理をスキップします。
- research/factor_research.py は設計方針・定数が定義されていますが、一部実装が未完（calc_momentum の続きなど）。今後のリリースで完成予定です。

以上。