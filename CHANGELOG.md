CHANGELOG
=========

このプロジェクトは Keep a Changelog のガイドラインに準拠しています。
https://keepachangelog.com/ja/1.0.0/

フォーマット:
- Unreleased: 未リリースの変更（現状なし）
- バージョン履歴は逆時系列（最新が上）

Unreleased
----------
（なし）

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース。以下の主要機能・モジュールを追加。
  - 実行・監視用エントリポイント
    - run_execution.py
      - ExecutionEngine の起動スクリプト。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 経由でペーパートレード実行が可能。
      - 実行 PID を data/execution.pid に出力し、data/stop_requested.flag により安全停止が可能。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプト。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
      - 監視は環境に依らず本番用 sqlite_path を使用する設計。
  - 設定・環境管理
    - config.py
      - .env 自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml）。
      - 必須/任意の環境変数取得ユーティリティ（Settings クラス、settings インスタンス）。
      - 各種既定値の定義（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
      - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
    - config_setup.py
      - 対話式の .env 作成/更新ウィザード。既存値の読み込み・マスク表示・保存機能を提供。
    - validate_config.py
      - 起動前チェック CLI。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML 必須）。
      - --strict オプションで警告をエラーとして扱うモードを提供。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py
      - 銘柄候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合は等配分でフォールバックし警告を出力。
    - portfolio/risk_adjustment.py
      - セクター集中制限 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装。
      - レジーム別乗数: bull=1.0, neutral=0.7, bear=0.3。未知のレジームは 1.0 でフォールバック。
    - portfolio/position_sizing.py
      - 発注株数算出ロジックを実装（risk_based / equal / score の振る舞い）。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時はスケールダウン）の実装。
      - cost_buffer による保守的コスト見積り対応。
  - 監視・logging・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR の環境変数対応。
    - utils/process_priority.py
      - Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。権限不足などは警告を出してスキップ。
  - 解析・検証ツール
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計してレポート出力。
      - レポートの合否判定し PASS/FAIL を表示。P95 計算と閾値はソース内で定義（稼働率 99%、Fill 90%、Send 95%、P95 <= 200 ms）。
  - 研究用ファクター計算基盤（下準備）
    - research/factor_research.py
      - モメンタム等の指標計算のための骨組みを実装（DuckDB 接続を受け、prices_daily / raw_financials を参照）。（一部未完了の実装片あり）
  - パッケージ情報
    - __init__.py にて __version__ = "0.1.0" を設定。パッケージの主要エクスポートを __all__ で定義。

Changed
- 初期リリースのため変更履歴なし。

Fixed
- 初期リリースのため修正履歴なし。

Known issues / Notes
- position_sizing.calc_position_sizes:
  - TODO コメントあり: 将来的に銘柄別 lot_size への対応を予定（現状は全銘柄共通の lot_size）。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りになり、ブロックが回避される可能性がある。将来的に前日終値等のフォールバックを検討。
- research/factor_research.py:
  - ファイル末尾で未完のコード断片があり（start_da など）、実装完了が必要。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、デグレードしてコンソール出力のみで継続する設計。
- 環境変数の自動ロード:
  - デフォルトではプロジェクトルートの .env/.env.local を読み込むが、テストなどで自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD が利用可能。
- セキュリティ:
  - .env は決して Git にコミットしない旨を config_setup.py のヘッダで警告。

Environment / Defaults (参考)
- KABUSYS_ENV: development (valid: development, paper_trading, live)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（run_monitoring の既定ポーリング秒。1 以上の整数。無効値はデフォルトにフォールバック）
- PID ファイル / stop フラグ: data/execution.pid, data/stop_requested.flag
- PAPER_FILL_MODE: instant (valid: instant, partial, never, reject)

How to run (主なエントリポイント例)
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス、貢献、その他のメタ情報はリポジトリのトップレベルドキュメントを参照してください。