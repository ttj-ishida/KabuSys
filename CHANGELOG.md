CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 基本パッケージ初期実装を追加（初回リリース）。
  - パッケージメタデータ: kabusys.__version__ = 0.1.0
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を High に設定。
    - 停止管理: data/execution.pid、data/stop_requested.flag を利用して安全に停止可能。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて実行。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) の検知でループ終了。
    - 例外はログに記録して次ポーリングへ（例外耐性あり）。
- 設定・環境管理
  - config.Settings: アプリケーション設定読み取りクラスを追加。
    - .env 自動読み込み機能（.env, .env.local）をサポート（OS 環境変数優先）。自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 各種プロパティを提供（J-Quants, kabuAPI, DB パス, PAPER_FILL_MODE, PID/kill フラグパス, CPU/MEM/DISK 閾値 など）。
    - 値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション）。
- 設定支援ツール
  - config_setup: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / Kill Switch など主要設定を対話形式で入力・保存。
    - .env 出力テンプレートには .env を Git にコミットしない旨の注意を含む。
  - validate_config: 設定検証 CLI を追加。
    - .env と config/*.yaml の基本的整合性チェックを実施。
    - --strict モードで警告をエラー扱いにできる。
    - 本番 (KABUSYS_ENV=live) 向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
- データベース / 分析
  - DuckDB 統合: duckdb 接続を各所で受け取る設計を採用（duckdb_path 設定）。
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を run_* スクリプトで呼び出し、監視テーブル存在を保証（冪等）。
- ポートフォリオ構築（純関数ライブラリ）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート/上位選抜。
    - calc_equal_weights, calc_score_weights: 重み計算（スコアが全て 0 の場合のフォールバックを含む）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中度制限の実装（既存保有を考慮し、売却予定銘柄は除外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を提供。
  - portfolio.position_sizing
    - calc_position_sizes: 等配分・スコア配分・リスクベースの株数決定ロジックを実装。
      - 単元株（lot_size）で丸め、aggregate cap（利用可能現金）によりスケーリング、残差処理の実装あり。
      - cost_buffer による保守的コスト見積もりを考慮。
- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。
    - StreamHandler (stdout) + TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: クロスプラットフォーム（Windows/Linux/macOS 等）のプロセス優先度設定と CPU affinity 設定を実装（psutil ベース）。
    - 標準的なレベル: high / normal / low。設定失敗時は警告ログ出力。
- 運用ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定を出力。
    - デフォルトしきい値をコード内に定義（稼働率 99%、成功率 90% 等）。
    - 日付フィルタ機能（--from / --to）、DB パス指定（--db または 環境変数 PAPER_TRADING_SQLITE_PATH）。
- 研究用モジュール（着手）
  - research.factor_research: DuckDB を用いたファクター計算モジュールの実装開始（モメンタム、MA200、ATR、Volume 系の定義・定数を含む）。（一部未完）

Changed
- logging の出力先を stdout に統一（stream handler は stdout を使用）。cron/task 実行時のログ集約を考慮。

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし（が、.env を絶対にリポジトリにコミットしない旨の注意を .env テンプレートに明記）

Notes / Known limitations
- research.factor_research モジュールは実装途中（ファイル末尾が切れている／一部未完）。本格利用前に追加実装が必要。
- position_sizing、risk_adjustment 内で価格データが欠損（0.0）の場合に保守的な挙動や TODO コメントあり。価格フォールバックロジック（前日終値等）は将来追加予定。
- run_monitoring は監視 DB として環境に関わらず sqlite_path（本番用）を使用するため、複数環境で同じ DB を参照すると分離できない点に注意。
- process_priority / cpu_affinity の設定はプラットフォーム依存で例外が発生する場合がある（権限不足等）。失敗時はログで警告し、処理は継続する。

Contributing
- バグ修正や改善提案は issue / PR を歓迎します。重要な設定（API トークンなど）は .env で管理し、リポジトリに含めないでください。

License
- プロジェクト内にライセンス記載がないため、利用時はライセンスを明確にしてください。