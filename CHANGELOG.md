KEEP A CHANGELOG
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-21
-------------------

Added
- 初回リリースを追加。
- 基本的な実行スクリプトを追加:
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して MockBrokerClient を利用する想定（BrokerClientFactory による生成）。
    - 起動時にプロセス優先度を "high" に設定し、停止用フラグファイル（data/stop_requested.flag）および pid ファイル管理に対応。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用監視 DB）を参照して初期化する。
    - 停止フラグの検出、例外発生時のログ、KeyboardInterrupt による終了処理を実装。
- 環境設定周りのユーティリティを追加:
  - config.py
    - .env の自動ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と OS 環境変数の保護ロジックを実装。
    - 各種設定プロパティを提供（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 設定、監視しきい値など）。値検証 (有効値チェック) を含む。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など Paper Trading 用設定をサポート。
  - config_setup.py
    - 対話式 .env 作成ウィザード。既存 .env の読み込み・マスク表示・確認・保存までをサポート。
  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数や config/*.yaml の存在・パース、パスの親ディレクトリ存在確認、KABUSYS_ENV=live 時の追加ガードなどを実施。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリを追加:
  - portfolio/portfolio_builder.py
    - 候補選択（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ想定）を考慮した配分ロジック。
  - portfolio/__init__.py でエクスポートを整備。
- 監視・分析関連:
  - monitoring 初期化ユーティリティ呼び出し（init_monitoring_db を利用）を各起動スクリプトで実施し、監視テーブルが存在することを保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。期間フィルタ（--from / --to）と DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）に対応。
- ユーティリティ群:
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティ。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先順位解決を実装。
  - utils/process_priority.py
    - Windows と POSIX 系でのプロセス優先度設定（nice/priority class の差分吸収）。CPU affinity 設定ユーティリティも実装。権限不足等は警告でフォールバック。
- 研究用コード（一部）:
  - research/factor_research.py（ファクター計算の骨格を実装）
    - Momentum、Value、Volatility、Liquidity 等の計算方針を記述し、DuckDB を利用する設計。calc_momentum 等の関数を実装の方向で追加（ファイル末尾は未完の部分あり）。
- パッケージメタ:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため修正履歴はなし）

Security
- N/A

Notes / Implementation details / 注意点
- .env 自動読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
- config._load_env_file は OS 環境変数を保護（既存のキーは上書きされない、.env.local は override=True で上書きするが protected set は保護）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 以下や数値以外）を検出してデフォルト 60 秒にフォールバックし、警告ログを出す。
- run_execution は起動前に停止フラグを検出すると起動を中止する安全措置を含む。
- position_sizing のスケーリングは単元株（lot_size）単位で行われ、残余キャッシュの利用は fractional remainder に基づいて再配分する仕組みを持つ。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" とし、unknown セクターには上限を適用しない（設計上の判断）。
- ファイルやディレクトリの作成に失敗した場合、多くのユーティリティはログ警告を出して処理を継続するよう設計されている（安全第一のフォールバック）。

References
- CLI:
  - python -m kabusys.config_setup  (.env ウィザード)
  - python -m kabusys.validate_config  (設定検証)
  - python -m kabusys.run_execution  (ExecutionEngine 起動)
  - python -m kabusys.run_monitoring (SystemMonitor 起動)
  - python -m kabusys.tools.paper_verification_report (Paper Trading レポート)

This project adheres to Keep a Changelog and Semantic Versioning.