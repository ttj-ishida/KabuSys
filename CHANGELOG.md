CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

（なし）

0.1.0 - 2026-04-18
-----------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本機能を追加。
- 実行系
  - 実行エンジン起動スクリプト run_execution.py を追加。:
    - プロセス優先度を起動時に設定（high）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（Mock クライアントを含むことを想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine をスレッドで起動。PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止を実装。
    - RiskManager のデフォルト設定を定義（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。initial_portfolio_value を broker.get_available_cash() で初期化。
- 監視系
  - 監視ループ起動スクリプト run_monitoring.py を追加。:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境設定に依らず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - stop フラグ検知によるループ終了、check_once() 内の例外をログ出力して継続する堅牢化。
- 設定管理
  - Settings クラスを実装（kabusys.config）。.env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
  - 各種設定プロパティを提供: J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境種別（development/paper_trading/live）等。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）や LOG_LEVEL / KABUSYS_ENV の検証を実装。
- 設定ユーティリティ
  - 対話式 .env ウィザード config_setup.py を追加。シークレット項目はマスク表示、.env の読み書きロジックを提供（.env を絶対にコミットしない旨のヘッダを出力）。
  - 設定検証 CLI validate_config.py を追加。必須環境変数チェック、DB パス・YAML ファイル存在チェック、KABUSYS_ENV=live 時の追加ガード、--strict モード（警告も失敗扱い）。
  - .env パーサーはクォート内エスケープ、インラインコメント等に対応し堅牢化。
- ロギング / プロセス制御ユーティリティ
  - setup_logging による統一ロギング設定を提供（StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション、ログディレクトリ作成失敗時のフォールバック）。
  - set_process_priority / set_cpu_affinity を提供（Windows / POSIX の差分吸収、権限不足等は警告でスキップ）。
- ポートフォリオ構築
  - 銘柄選定・重み計算モジュールを追加（select_candidates, calc_equal_weights, calc_score_weights）。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装。未知レジームはフォールバックして警告を出力。
  - 株数決定（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）対応、lot_size（単元）丸め、aggregate cap（全体投下額のスケール調整）、cost_buffer（手数料・スリッページ想定）考慮。
- リサーチ
  - factor_research の骨組み（モメンタム / MA200 / ATR / ボラティリティ等の計算方針と定数）を追加（DuckDB 接続を受け SQL/Python で計算する設計）。
- ツール
  - Paper Trading 検証レポート生成スクリプト tools/paper_verification_report.py を追加。:
    - 稼働率、注文成功率（fill rate）、送信率、リスク却下数、平均/最大/P95 レイテンシ等を算出。
    - CLI オプション --from/--to/--db をサポート。閾値による PASS/FAIL 判定を出力。
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として登録。

Changed
- 初版のため該当なし（初回導入）。

Fixed
- 設定読み込み・値検証の堅牢化:
  - MONITOR_POLL_INTERVAL 等の環境変数に不正値が与えられた場合のフォールバック処理を追加。
  - .env パーサーのクォート・エスケープ・コメント処理を強化。
  - ログディレクトリ作成失敗時にファイルハンドラを無効化してコンソール出力にフォールバックする安全策を追加。

Security
- config_setup の出力ではシークレット項目をマスク表示し、.env を絶対にリポジトリへコミットしない旨の警告をヘッダに記載。

Notes / 注意事項
- 本リリースでは多くの機能がスケルトンまたは初期実装の段階です。特に DuckDB / SQLite の想定スキーマ（prices_daily, raw_financials, system_status, trade_logs, risk_logs 等）は外部から供給されるか、init_monitoring_db 等で事前準備が必要です。
- 実運用（KABUSYS_ENV=live）では .env の設定、LINE 通知や Kill Switch の運用方針に十分注意してください。validate_config の警告を必ず確認することを推奨します。
- Paper Trading は本番 DB と分離されていますが、パラメータ（PAPER_FILL_MODE など）によって挙動が大きく変わるため、テストを十分に行ってください。

---