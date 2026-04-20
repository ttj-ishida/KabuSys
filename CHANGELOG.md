CHANGELOG
=========

すべての重要な変更はこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-04-20
--------------------

Added
- 初回リリース: KabuSys 基本機能群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の Mock クライアント（BrokerClientFactory 経由）を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）へ記録することで本番 DB と完全分離する仕組みを提供。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照する点に注意。
- 設定管理
  - config.py: .env 自動ロード（.env / .env.local）と Settings クラスを実装。多くの設定プロパティ（DBパス、KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）と検証を提供。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - config_setup.py: 対話式ウィザードで .env ファイルの初期作成・更新が可能。シークレット項目はマスク表示して保存を補助。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの存在確認、config/*.yaml のパース（PyYAML がインストールされている場合）など。--strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights)を実装。
  - portfolio.risk_adjustment: セクター集中制限(apply_sector_cap)と市場レジームに基づく投下資金乗数(calc_regime_multiplier)を実装。
  - portfolio.position_sizing: position size 算出ロジック(calc_position_sizes)を実装。risk_based / equal / score の配分方法、lot 単位による丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り等をサポート。
- 監視・レポート
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定を出力。期間指定および DB パス指定オプションあり。
- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定を提供。コンソール (stdout) と日次ローテート（TimedRotatingFileHandler）の両方をサポート。ログディレクトリは logs/（環境変数 LOG_DIR で上書き可）。ファイルハンドラは作成失敗時にフォールバックしてコンソールのみで継続。
  - utils.process_priority: psutil を用いたプロセス優先度設定ユーティリティ。Windows/Linux/macOS の差分を吸収。CPU アフィニティ設定も提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- データリサーチ
  - research.factor_research: ファクター計算モジュール（モメンタム等）の骨組みを追加（DuckDB を利用）。（calc_momentum の計算ルーチン実装を開始。）
- パッケージ化
  - パッケージ初期化: src/kabusys/__init__.py にバージョンと公開 API を定義。

Changed
- n/a（初回リリースのため該当なし）

Fixed
- n/a（初回リリースのため該当なし）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

運用上の注意・移行メモ
- 環境変数/デフォルト
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config でもチェック）
  - KABUSYS_ENV の有効値: development / paper_trading / live（Settings で検証）
  - PAPER_FILL_MODE の有効値: instant / partial / never / reject（Settings で検証）
  - DB のデフォルト:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - ログ: デフォルトログディレクトリは logs/、ファイル名はアプリ名（例: execution.log）。LOG_DIR 環境変数で変更可。
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を秒で指定（デフォルト 60）。0 以下や不正な値は警告してデフォルトにフォールバック。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env ファイルを読み込まなくなる（テスト等で利用）。
- 実行プロセスの挙動
  - run_execution は Paper Trading 時に本番 DB を汚さないよう paper_sqlite_path を使用。
  - run_monitoring は監視用に常に sqlite_path（monitoring.db）を使用する点に留意。
  - 監視・実行の停止はプロジェクトルート/data/stop_requested.flag（stop_requested.flag）ファイルの作成で検知して安全に終了する。
- 依存関係の挙動
  - psutil: process_priority 周りで使用。権限不足や未対応プラットフォームでは警告を出してスキップする設計。
  - PyYAML: validate_config の YAML パースは PyYAML が存在する場合のみ実行。未導入でも起動は可能だが YAML 検証はスキップされる。
- ログハンドリング
  - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続します。ログ設定は全起動スクリプトで統一的に行われます。

既知の制限 / TODO
- position_sizing や apply_sector_cap は価格欠損時（price が 0 または None）の扱いで注意が必要。将来的に前日終値や取得原価でのフォールバックを検討。
- research.factor_research の一部関数（calc_momentum など）は実装途中で、追加実装・テストが必要。
- 単元株（lot_size）は現状全銘柄共通のパラメータになっている。将来的に銘柄別単元対応を検討。

お問い合わせ
- バグ報告や改善提案は Issue を作成してください。