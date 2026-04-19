CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

次のバージョン規約に従います: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-19
-------------------

Added
- プロジェクト初期リリース。以下の主要コンポーネントを追加。
  - 実行・監視用エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）を利用する仕組みを実装。スレッドで engine.run_session を実行し、停止フラグ（data/stop_requested.flag）検出で安全に停止する。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用し、停止フラグ検出でループを終了する。
  - 設定管理
    - config.py: Settings クラスを追加。.env の自動読み込み（プロジェクトルート検出）と、環境変数からの設定取得ロジックを提供。各種既定値・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を実装（シークレット入力、既存値の再利用、書き込みテンプレート含む）。
    - validate_config.py: 起動前に .env と config/*.yaml の基本検証を行う CLI を実装（--strict により警告をエラー扱いにできる）。PyYAML 未インストール時の挙動や本番環境向けの追加ガードも含む。
  - ポートフォリオ構築関連（純粋関数）
    - portfolio.portfolio_builder: 銘柄選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - portfolio.position_sizing: 発注株数決定ロジック（calc_position_sizes）を実装。allocation_method として "risk_based", "equal", "score" をサポートし、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積りを実装。
  - ユーティリティ
    - utils.logging_setup: stdout の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定を提供。ログディレクトリ作成失敗時はコンソール出力のみで継続する。
    - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定用ユーティリティを提供。権限不足時は警告を出してスキップする。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite を読み解析し、稼働率、注文成功率、送信率、P95 レイテンシなどを算出する検証レポート生成ツールを追加。閾値判定により PASS/FAIL を出力。
  - データ分析（研究用）
    - research.factor_research: DuckDB 接続を受け取り価格テーブルからファクター（Momentum 等）を計算するモジュールを追加（モジュール設計、定数、calc_momentum の導入を含む。実装は継続中／部分的）。
  - パッケージ
    - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （既知のセキュリティ修正は無し）

Notes / Known issues / TODO
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。プロジェクトルートを特定できない場合は自動ロードをスキップする。
- .env のパースは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントなどに対応する堅牢な実装を目指しているが、特殊ケースの追加検証が必要。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）があるとエクスポージャーが過少に見積もられる問題があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が残る。
- research.factor_research はモジュール設計と一部関数が追加されているが、ファイル末尾で実装が途中で切れている（calc_momentum の続きが未完）。研究用ファクター算出ロジックは今後追加予定。
- ExecutionEngine 側の既知の設計点:
  - Engine 起動時に停止フラグが既に存在する場合は起動を行わず終了する安全措置を実装。
  - RiskConfig の初期 portfolio value は broker.get_available_cash() に依存するため、BrokerClient の実装に応じた初期化挙動確認が必要。
- logging_setup はログディレクトリの作成に失敗した場合にファイルハンドラをスキップするため、ディスク容量・権限の問題がある環境ではログが標準出力のみになる点に注意。

参考: 実行方法の例
- 環境セットアップ: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Acknowledgements
- 本 CHANGELOG は提供されたソースコードからの挙動・設計意図を推測して作成しています。実際のリリース履歴や過去の変更差分が存在する場合は、その履歴に基づいて追記・修正してください。