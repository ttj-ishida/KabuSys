CHANGELOG
=========

すべての重大な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初回リリース: KabuSys 基本コンポーネント群を追加
  - 環境設定 / 起動支援
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI（各種設定項目の入力補助、秘密値マスク表示、保存可否の確認）。
    - validate_config.py: 起動前チェックツール（必須環境変数の有無、パスの親ディレクトリ確認、config/*.yaml の存在/パース等）。--strict オプションで警告を FAIL 扱いにできる。
    - Settings クラス: 環境変数をラップしてアプリ用設定を提供（env 判定、DB パス、paper_trading の分離設定、監視閾値など）。
  - 実行系 / 発注
    - run_execution.py: ExecutionEngine 起動スクリプト
      - KABUSYS_ENV=paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離する挙動をサポート。
      - BrokerClientFactory を介したブローカー抽象化。
      - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立てて実行。ExecutionEngine はデーモンスレッドで run_session を実行し、stop flag による安全停止対応。
      - デフォルトの RiskConfig を内蔵（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。initial_portfolio_value は broker.get_available_cash() を使用。
  - 監視
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db をデフォルト）を使用する設計。
      - 停止はプロジェクト直下 data/stop_requested.flag によるフラグ検出で行う。
  - ポートフォリオ構築ライブラリ
    - portfolio モジュールを追加（純粋関数群）
      - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights。全スコア0 の場合は等配分にフォールバック）。
      - risk_adjustment: セクター集中制限（apply_sector_cap）、マーケットレジームに応じた乗数（calc_regime_multiplier。bull/neutral/bear をサポート、未知レジームは 1.0 フォールバック）。
      - position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の割当方式、lot_size（単元）・aggregate cap・コストバッファ考慮のスケールダウンロジックを実装。
  - 解析 / レポート
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツール
      - system_status / trade_logs / risk_logs から各種指標（稼働率、Fill/Send 率、P95 レイテンシ等）を集計し PASS/FAIL 判定を出力。コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）を受け付ける。
  - 研究 / ファクター計算（基盤）
    - research/factor_research.py: DuckDB 接続を利用したファクター計算モジュール（モメンタム、MA200乖離、ATR 等を想定した骨組みを実装）。（注: ファイル末尾に未完の箇所あり）
  - ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティ
      - stdout StreamHandler（stdout 使用）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR / app_name を解決。
    - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
      - Windows / POSIX（Linux, Darwin, FreeBSD）対応の優先度設定（high/normal/low）と CPU affinity 設定関数を提供。権限不足や未対応環境では警告を出して安全にスキップ。

Changed
- なし（初回リリース）

Fixed
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート有無で挙動を分離）を実装して .env の柔軟な記述に対応。
- .env 読み込み挙動の明確化
  - .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）および上書き保護（protected set）を実装。

Security
- .env ファイル取り扱いに関する注意書きを config_setup の出力に追加（.env を絶対に Git にコミットしない旨を明記）。

Notes / Behaviour highlights
- DB 分離
  - paper_trading モードでは paper_trading 用 SQLite を使用して本番の監視 DB とデータを分離する設計。本番誤用防止に配慮。
- 監視と実行の停止制御
  - data/stop_requested.flag（および execution.pid 等の PID ファイル）による外部からの停止指示をサポート。validate_config により起動前に Kill Switch の設定もチェック可能。
- ログ出力
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続。
- 未実装 / TODO
  - research/factor_research.py の末尾に未完の実装箇所（calc_momentum の途中）あり。将来的に DuckDB クエリと統合した完全なファクター計算ロジックを追加予定。
  - position_sizing の価格欠損 (price == 0) 時のフォールバック（前日終値や取得原価を利用する等）は TODO コメントあり。

References / Usage examples
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

Acknowledgements
- 初期リリースでは内部設計を優先し、外部 API 呼び出しや本番デプロイ用の詳細（例: 銘柄別単元情報、厳格なエラーハンドリング、DB マイグレーション等）は順次改善予定です。