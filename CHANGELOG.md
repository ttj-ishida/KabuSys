CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。主要なバージョン、機能追加、修正点等を日本語で記載しています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更・改善
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当する場合に記載

Unreleased
----------
（現在なし）

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーション構成を実装（初期リリース）。
  - パッケージ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行用スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検知して安全にループを終了。
    - monitoring 用 DB は実行環境にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - 起動時にプロセス優先度を high に設定し、停止フラグ検知で安全にエンジン停止。
    - 実行用 PID ファイル（data/execution.pid）への対応。
- 環境設定・検証用ツールを追加
  - config_setup.py
    - 対話式ウィザードで .env ファイルを初期作成／更新する CLI を実装。
    - J-Quants / kabuAPI / DB パス / LINE 通知など主要設定項目を扱う。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を実装。必須環境変数・パスの存在・YAML のパースチェック等を行う。
    - --strict オプションで警告をエラー扱いにする機能を搭載。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースはクォート文字・エスケープ・インラインコメントを考慮した堅牢な実装。
    - Settings クラスに各種環境設定プロパティを実装（DB パス、paper_trading 切り替え、監視閾値、ログレベル等）。値検証とデフォルトを提供。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定を実装。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX を抽象化したプロセス優先度設定（high/normal/low）を追加。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を実装（アクセス権限がない場合は警告してスキップ）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選出（select_candidates）と配分重み算出（等配分 calc_equal_weights、スコア加重 calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py
    - 発注株数算出アルゴリズム calc_position_sizes を実装（risk_based / equal / score の割当方式に対応、単元株丸め、aggregate cap スケーリングなど）。
  - portfolio/__init__.py で主要関数をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均／最大／P95）などを集計してレポート出力する CLI を実装。
    - レポート期間のフィルタ（--from / --to）と DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）に対応。
    - 基準値（稼働率 99% など）に基づく PASS/FAIL 判定を出力。
- リサーチ（ファクター計算）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity に関する設計と一部実装を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針）。
    - （注）ファイル末尾が一部未完であるため、さらなる実装が見込まれる。
- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db が各スクリプト起動時に監視テーブル存在を保証（冪等に実行）。

Changed
- 環境変数パース改善
  - config._parse_env_line にて export プレフィックスの対応、クォート内エスケープ、インラインコメントの扱いを強化。より柔軟な .env 記述を許容。
- ロギングのデフォルト動作
  - logging_setup.setup_logging は既存ハンドラをクリアしてから設定することで多重ハンドラ登録を防止。
  - 標準出力は stdout を使用（stderr ではない） — cron 等での stdout/stderr のリダイレクト運用を想定。
- DB の運用分離
  - run_execution.py は paper_trading 環境で paper_trading 用別 DB を利用するようにして本番 DB との混在を防止。

Fixed
- 環境変数無しの際の明確なエラー
  - Settings._require により必須環境変数が未設定の場合に ValueError を投げるようにし、早期に問題を検出可能に。
- モニタリングループの例外耐性
  - run_monitoring.monitor の check_once() 呼び出しで例外が発生してもループを継続し、ログにスタックトレースを残して次回ポーリングまで待機するように変更。

Notes / Known issues
- research/factor_research.py は設計方針と一部関数（calc_momentum 等）の実装が含まれるものの、ファイル末尾が未完（途中で切れている）です。完全実装は今後のリリースで対応予定。
- 一部の機能（例: BrokerClientFactory の実装、ExecutionEngine 内部、SystemMonitor 実装等）は本 CHANGELOG に記載するコード上位モジュールで参照されていますが、実体は別ファイルに依存しています。統合テストや実運用前にそれらのコンポーネント連携の確認が必要です。
- process_priority / set_cpu_affinity / logging_setup 等は OS 権限や環境によって挙動が制限されることがあります（権限不足時は警告ログでスキップします）。

今後の予定（例）
- research モジュールの完全実装（ファクター計算の追加検証・最適化）。
- ExecutionEngine と BrokerClient の統合テストおよびペーパートレードの検証強化。
- モニタリングのアラート出力（LINE 連携等）の強化と自動通知機能の追加。

参考: 主要ファイル一覧
- 実行スクリプト: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ポートフォリオ: src/kabusys/portfolio/
- ユーティリティ: src/kabusys/utils/
- ツール: src/kabusys/tools/paper_verification_report.py
- リサーチ: src/kabusys/research/factor_research.py (部分実装)

以上。必要であれば、リリースノートを英語表記や細かいコミット別の履歴に分割して作成します。