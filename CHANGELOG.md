CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-------------

- 開発中の変更や未リリースの調整はここに記載します。

0.1.0 - 2026-04-19
------------------

初回公開リリース。

Added
-----

- 全体
  - パッケージ初回公開。モジュール群を追加して自動売買システムの基盤を実装。
  - バージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 実行スクリプト
  - run_monitoring.py を追加（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動用スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ file: data/stop_requested.flag の監視による安全停止。
    - Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用して監視データを記録。
    - SQLite / DuckDB 接続初期化と例外保護（check_once の例外はログ出力して継続）。
  - run_execution.py を追加（src/kabusys/run_execution.py）
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db）を使用し MockBrokerClient を利用（アプリケーション設計に基づく切り分け）。
    - 停止フラグと PID ファイル管理（data/execution.pid）。
    - スレッドで ExecutionEngine を起動し、停止フラグ検知で安全に engine.stop() を呼ぶロジック。
    - デフォルトでプロセス優先度を "high" に設定する呼び出しを実施。

- 設定管理・検証・ウィザード
  - config.py を追加（src/kabusys/config.py）
    - .env の自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - 複雑な .env パース実装（export 前置、クォート内バックスラッシュエスケープ、インラインコメント扱い等）。
    - Settings クラスで各種環境変数をプロパティ化（検証付）。例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV/LOG_LEVEL の検証、SQLite/DuckDB パスの Path 化、監視しきい値やフラグ設定の取得等。
  - validate_config.py を追加（src/kabusys/validate_config.py）
    - .env や config/*.yaml の起動前検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在警告、YAML ファイルの存在チェックとパース（PyYAML がない場合はスキップして警告）。
    - KABUSYS_ENV=live のガード（LINE 通知の設定確認、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を失敗と見なすモード。
  - config_setup.py を追加（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env を生成 / 更新する CLI。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 設定等を順に入力して .env を書き出す機能。
    - 既存 .env の読み込み再利用やシークレットのマスク表示に対応。

- ロギング・プロセス制御ユーティリティ
  - logging_setup.py を追加（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティ。
    - LOG_LEVEL / LOG_DIR の優先解決とディレクトリ作成処理、既存ハンドラのクリーンアップを実装。
    - ファイルハンドラ作成に失敗した場合のフォールバック（コンソール出力のみ）を考慮。
  - process_priority.py を追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の違いを吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装（例外処理とプラットフォーム対応を含む）。
    - パーミッション不足や未対応 OS では警告ログを出して失敗をスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio モジュールを追加（src/kabusys/portfolio/*）
    - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights)。
    - risk_adjustment.py: セクターキャップ適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)。
    - position_sizing.py: 発注株数算出ロジック (calc_position_sizes)。risk_based / equal / score の各 allocation_method をサポートし、lot_size 単位で丸め、aggregate cap（利用可能現金に合わせたスケーリング）と cost_buffer を反映する堅牢な実装を提供。
    - すべてメモリ内純粋関数で、DB に依存しない設計。

- ツール類
  - tools/paper_verification_report.py を追加（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite データベースから検証レポートを生成する CLI。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで上書き可能。
    - P95 計算、日付フィルタ、欠損テーブルに対する耐性（OperationalError をキャッチして N/A を扱う）を実装。

- リサーチ
  - research/factor_research.py を追加（src/kabusys/research/factor_research.py）
    - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）設計の骨格を実装。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針。
    - calc_momentum の実装を開始（モジュール内の定数・設計方針を定義）。

Changed
-------

- （初回リリースのため該当なし）

Fixed
-----

- （初回リリースのため該当なし）

Deprecated
----------

- （初回リリースのため該当なし）

Removed
-------

- （初回リリースのため該当なし）

Security
--------

- （初回リリースのため該当なし）

Notable implementation details / operational notes
-------------------------------------------------

- .env 自動読み込み
  - デフォルトでプロジェクトルートの .env/.env.local を自動ロードします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OS 環境変数は保護され .env の上書き対象になりません（protected 機能）。

- Paper Trading と本番 DB の分離
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番の monitoring DB と完全分離を図っています。
  - run_monitoring は監視データの記録に常に sqlite_path（デフォルト data/monitoring.db）を使用します。

- ロギング
  - ログは標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみになります。

- プロセス優先度
  - 起動スクリプトは先頭で set_process_priority("high") を呼び出し、重要プロセスの優先度を上げます。実行環境によっては権限不足で設定に失敗する可能性があり、その場合は警告が出力されます。

Known issues / TODO
-------------------

- research/factor_research.calc_momentum の実装はファイル末尾で途中（ソースが切れている箇所があります）。完全実装・テストは今後の作業項目です。
- position_sizing.calc_position_sizes の価格欠損時の扱いについて注記（price が 0.0 の場合に過少見積のリスクあり）。将来的に前日終値や取得原価をフォールバック価格として使う改善を検討。
- 一部の機能（ExecutionEngine、BrokerClientFactory、SystemMonitor 等）はこのリリースでは呼び出し先の実装（別モジュール）に依存しており、統合テストが必要。

作者
----

KabuSys 開発チーム

--- 

注: 本 CHANGELOG はソースコードから推測して作成しています。実際のユーザー向けリリースノート作成時は変更内容や動作を実際に確認の上で更新してください。