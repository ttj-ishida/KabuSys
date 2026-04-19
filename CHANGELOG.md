CHANGELOG
=========

すべての変更は Keep a Changelog の方針に沿って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース。KabuSys のコアスクリプト・ユーティリティ・ライブラリを実装。
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時には MockBrokerClient を使用し、Paper Trading 用に data/paper_trading.db を利用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知および KeyboardInterrupt による安全な終了に対応。
- 設定管理
  - config.py: .env 自動読み込み（.env, .env.local）、プロジェクトルート自動検出（.git または pyproject.toml 基準）、各種設定プロパティ（DB パス、API トークン、閾値など）を提供。環境値の検証（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL 等）を実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。
  - validate_config.py: 起動前に .env と config/*.yaml の基本チェックを行う CLI（--strict オプションで警告を FAIL 扱い）。
- 監視・モニタリング
  - monitoring_db 初期化呼び出し（init_monitoring_db）を各起動スクリプトで実行して監視テーブルの存在を保証（冪等）。
  - duckdb / sqlite の併用を想定した DB 接続設定を追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額/スコア重み（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、コストバッファ対応。
  - portfolio パッケージのエクスポートを整備。
- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。LOG_LEVEL / LOG_DIR の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - utils.process_priority: Windows/Linux/macOS を横断してプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを実装。権限不足などの例外は警告を出してスキップ。
- ツール群
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB を指定可能。デフォルトの閾値（稼働率 99.0%、Fill 90%、Send 95%、P95 レイテンシ 200 ms）を定義。
- リサーチ
  - research.factor_research（実装開始）: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計。momentum 計算関数の骨組みを追加（未完部分あり）。
- パッケージメタ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- データベース動作方針
  - 監視（monitoring）は実行環境に関わらず本番用 sqlite_path を使用して監視データを一元化（run_monitoring の挙動）。
  - 実行（execution）は paper_trading モード時に専用の paper_sqlite_path を使用して本番データから完全分離（run_execution の挙動）。
- ログ出力
  - ログは stdout に出力されるようにデフォルト設定（cron/Task Scheduler などでリダイレクトしやすくするため）。
  - 既存ハンドラがある場合は一旦クリアして再設定することで二重ログ出力を防止。

Fixed
- 例外処理／安全停止
  - poll ループ内で monitor.check_once() が例外を投げてもループを継続し、次回ポーリングまで待機するように例外キャッチを追加（run_monitoring）。
  - run_execution / run_monitoring ともに DB 接続（sqlite/duckdb）を finally で確実にクローズするように修正。

Security
- 環境変数の取り扱い
  - config_setup と .env の書き出しで秘密値（トークン・パスワード）はマスクして対話表示。.git に .env をコミットしない旨の注意を .env ヘッダに記載。

Breaking Changes
- Settings のバリデーション
  - Settings.env / PAPER_FILL_MODE / LOG_LEVEL などの検証に厳格なチェックを追加。無効な値を与えると ValueError を送出するため、運用スクリプト・デプロイ時は .env の見直しが必要。
- .env 自動ロード
  - プロジェクトルート検出に失敗した場合は自動ロードをスキップする挙動。テストや特殊な配布状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須（validate_config でもチェック）。未設定の場合は起動前に .env を用意してください。
- 主要コマンド:
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ログ:
  - デフォルトで logs/ ディレクトリに日次ローテーションのログファイル（execution.log / monitoring.log 等）を出力。LOG_DIR 環境変数で変更可能。
- Paper Trading:
  - paper_trading 環境では実際の注文は送信されず、paper 用 SQLite にトレードログを記録します。PAPER_TRADING_SQLITE_PATH を設定して管理してください。

Acknowledgements / Future
- research.factor_research の他ファクター（Value, Volatility, Liquidity）や momentum 実装の続き、strategy/execution 側の詳細実装（ExecutionEngine 内部、BrokerClient 実装等）を今後追加予定。