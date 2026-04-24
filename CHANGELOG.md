CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョンはパッケージの __version__ に合わせています。

Unreleased
----------

Added
- .env ファイルのパースと自動読み込みを強化
  - export KEY=val 形式、クォート（'"/"）とバックスラッシュエスケープ、インラインコメントの扱いに対応。
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード。
  - OS 環境変数は保護（protected）され、.env.local の上書き時にも意図しない上書きを防止。
- 実行・監視の起動スクリプトを追加/整備
  - run_execution: ExecutionEngine の起動ロジック（broker ファクトリ、OrderManager、RiskManager、Reconciler の組立て、別スレッドでの実行、停止フラグ検出）。
  - run_monitoring: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全にループ終了。
  - どちらも起動直後に process priority を "high" に設定する処理を組み込み（失敗時は警告を出して継続）。
- Paper Trading 用に実運用 DB と分離
  - KABUSYS_ENV=paper_trading のときは settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 sqlite_path と分離。
  - paper_fill_mode (instant/partial/never/reject) の設定を追加。無効値は例外を送出。
- 設定関連 CLI の追加/改善
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援（シークレット入力のマスク表示、選択肢サポート、確認・保存）。
  - validate_config: .env と config/*.yaml を事前検証。--strict オプションで警告を FAIL 扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ロギング・プロセスユーティリティを整備
  - setup_logging: stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、作成失敗時はファイル出力をスキップして stdout のみで継続。ログローテーションは 30 日分保持。
  - process_priority: Windows / POSIX の差分を吸収してプロセス優先度を設定。CPU affinity 設定ユーティリティも追加。権限不足や未対応 OS は警告を出して安全にスキップ。
- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等分配にフォールバックして WARNING を出す。
  - portfolio.risk_adjustment: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め（lot_size）、max_position_pct / max_utilization による上限管理、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り。端数処理は残差に応じて lot 単位で追加配分。
- Paper Trading 検証レポートツールを追加
  - tools.paper_verification_report: SQLite の paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計してレポート出力。閾値に基づく PASS/FAIL 判定を表示。P95 計算ロジックを実装。
- research モジュールの骨組み（factor_research）を追加（ファクター計算のための定数・設計方針とモメンタム計算の骨子を含む。未完部分あり）。

Changed
- 設定読み込みの既定動作
  - OS 環境変数が最優先。続いて .env.local（上書き可）、最後に .env（未設定時にのみセット）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト時に便利）。
- ログ出力は意図的に stdout を使用（stderr ではない）。これは cron / Task Scheduler 等で stdout/stderr をまとめてリダイレクトする運用を意識。

Fixed
- MONITOR_POLL_INTERVAL の不正な値（0 や負値、非整数）に対して検証を追加し、不正な場合はデフォルト値（60 秒）にフォールバックし警告を出すようにした。
- SQLite/DuckDB 接続の確保とクローズ処理を明示的に行うようにし、例外発生時でもリソースが解放されるよう finally ブロックを使用。

0.1.0 - 2026-04-24
------------------

Added
- 初期リリースとして以下の主要機能を実装:
  - アプリケーション設定管理 (kabusys.config)
    - プロジェクトルート検出、.env/.env.local 自動ロード、必須/任意設定のプロパティを提供。
    - データベースパス、ログレベル、KABUSYS_ENV（development/paper_trading/live）などを環境変数経由で取得。
  - 実行エンジン・監視コンポーネントの起動スクリプト
    - run_execution.py: ExecutionEngine の起動フロー、ペーパートレード時の MockBroker 切替、停止フラグ / PID ファイル管理。
    - run_monitoring.py: SystemMonitor のポーリングループ、停止フラグ検知、監視 DB 初期化。
  - 設定操作用 CLI
    - config_setup.py: 対話式ウィザードで .env を生成・更新。
    - validate_config.py: 起動前チェックランナー（必須環境変数、パス・YAML ファイル、live 用ガード等）。
  - ログ・プロセスユーティリティ
    - utils.logging_setup: 統一的なログ設定（コンソール + 日次ローテーション）。
    - utils.process_priority: プラットフォーム非依存のプロセス優先度設定、CPU affinity。
  - ポートフォリオ構築ライブラリ
    - portfolio.*: 候補選定、重み計算、セクターキャップ、ポジションサイズ計算（単元丸め、aggregate cap）。
  - ツール類
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト。
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- なし（初期リリース）。

Fixed
- なし（初期リリース）。

注記 / 既知の制約
- research.factor_research の実装は骨子が含まれているが一部未完（calc_momentum の続きなど）。将来的な追加実装が必要。
- process_priority や CPU affinity の適用は権限やプラットフォームに依存するため、権限不足時は警告でスキップする設計。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布パッケージや環境によっては期待通りに検出されない場合がある（その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- Paper Trading 関連の動作（MockBrokerClient のふるまい、fill_mode）は設定値に依存し、実運用時は設定の確認が必須。

作業メモ（開発者向け）
- .env のパースロジックは既存のシェル風表記（クォート、エスケープ、export 句）にかなり忠実に実装しているが、すべての edge case を網羅しているわけではない。必要に応じてパーサーの追加拡張を検討すること。
- logging_setup はログディレクトリ作成に失敗した場合でもプロセスを停止しない方針。CI / コンテナ環境でのログ配置を想定しており、環境に合わせた LOG_DIR 指定を推奨する。

----- 
この CHANGELOG はコードベースから推測して作成しています。詳細や誤りがあれば差分に基づいて修正できます。