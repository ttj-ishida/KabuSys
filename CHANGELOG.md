CHANGELOG
=========

すべての変更は "Keep a Changelog" に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリースを追加。主な機能・モジュール:
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に完全分離して記録。停止用フラグファイル（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）に対応。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
  - 設定管理
    - config.py: Settings クラスによる環境変数ラップ。.env/.env.local 自動読み込み（優先順位: OS 環境変数 > .env.local > .env）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、PAPER_FILL_MODE のバリデーション、各種パス・閾値・フラグのプロパティ提供。
    - config_setup.py: 対話式 .env 作成ウィザード。既存 .env の読み取り、シークレットのマスキング表示、.env ファイル出力テンプレートを提供。
    - validate_config.py: 起動前チェック CLI。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在・本番向け注意点などを検査。--strict オプションで警告を FAIL 扱いに可能。
  - ポートフォリオ構築（純粋関数群、DB 不要）
    - portfolio.portfolio_builder: 候補選定（スコア降順）、等金額配分 / スコア加重配分を提供。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: position size 計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン処理を提供。
  - ユーティリティ
    - utils/logging_setup.py: 統一的ログ設定ユーティリティ。コンソール（stdout）出力 + 日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティ。権限不足や未対応環境では安全にスキップする。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB を指定可能。
  - リサーチ
    - research/factor_research.py: DuckDB を使ったファクター計算モジュール（モメンタム、移動平均乖離、ATR 等の計算方針と下地実装）。設計に基づき prices_daily / raw_financials テーブルのみ参照する方針。

Changed
- ロギング
  - すべての起動スクリプトは setup_logging() を呼び出して統一的なログ出力を行うように設計。
  - StreamHandler は stdout を使用（stderr ではない） — タスクスケジューラ等でのリダイレクト運用を考慮。
- データベース接続方針
  - 監視モジュールは常に本番用 sqlite_path を参照（環境に依存せず監視データを本番 DB に集約）。一方、ExecutionEngine は paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離。
- プロセス優先度の初期化
  - 起動時に set_process_priority("high") を呼び出して優先度を上げる設計（起動直後に実行）。

Fixed / Improved
- .env パーサの強化（config._parse_env_line）
  - export KEY=val 形式のサポート、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの適切な無視、クォート無し値のコメント判定ルール改善などを実装。これにより .env ファイルの柔軟な記述に対応。
- .env 読み込みの安全性
  - _load_env_file() は override/protected 引数で OS 環境変数を保護しつつ .env.local を上書き可能にする等、テスト時やデプロイ時の柔軟性を確保。
- MONITOR_POLL_INTERVAL の取り扱い
  - run_monitoring 内での環境変数取得関数 _get_poll_interval() にて不正値（0 以下や非整数）を検出し、警告を出してデフォルトにフォールバックする実装を追加。
- Paper Trading 検証レポート
  - P95 の計算、各種 NULL/データ不足時のフォールバック、期間フィルタ (--from/--to) を実装。DB ファイル存在チェックのメッセージ改善。

Security
- secrets の扱い
  - config_setup のウィザードはシークレット項目をマスキング表示。.env テンプレートではシークレット値を明示しない設計を採用（.env を Git にコミットしない注意喚起を出力）。

Notes / Implementation details
- PID / Stop / Kill フラグ
  - 複数スクリプトで停止フラグ（data/stop_requested.flag 等）と PID ファイルを使用することで外部からの安全な停止・存在確認を実現。
- DuckDB / SQLite の併用
  - 分析用途に DuckDB（kabusys.duckdb）、運用・監視用に SQLite（monitoring.db / paper_trading.db）といった役割分担を明示。
- 設計思想
  - portfolio やリサーチなどのコアロジックは副作用を避けるため純粋関数として実装（DB アクセスや外部 API 呼び出しを行わない）。

Deprecated
- なし

Removed
- なし

Acknowledgements
- 初回リリース。今後のリリースではユニットテストの追加、factor_research の完全実装、Engine/Monitor の耐障害性強化、設定/ドキュメントの追加を予定しています。