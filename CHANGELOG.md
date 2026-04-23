CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

各リリースには、追加（Added）、変更（Changed）、修正（Fixed）、非推奨（Deprecated）、削除（Removed）、セキュリティ（Security）のカテゴリで要約しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-23
------------------

初回公開リリース。

Added
- 基本機能
  - パッケージ初期版を追加。バージョンは kabusys.__version__ = "0.1.0"。
  - 実行スクリプト:
    - run_execution.py — ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続（paper_trading 環境では専用 DB を使用）、BrokerClientFactory によるブローカークライアント生成、OrderManager / OrderRepository / Reconciler / RiskManager の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検出・安全終了をサポート。
  - 設定とセットアップ:
    - kabusys.config.Settings — 環境変数駆動の設定管理を実装（多くの既定値とバリデーションを含む）。
    - .env 自動読み込み機能（OS 環境変数 > .env.local > .env、プロジェクトルート探索の実装）。
    - config_setup.py — 対話式の .env 作成・更新ウィザードを追加。
    - validate_config.py — 起動前チェック用 CLI を追加（必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在と YAML パースなどを検査）。--strict オプションあり。
  - ロギング / プロセス管理ユーティリティ:
    - utils.logging_setup.setup_logging — stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）を用いた統一ログ設定。LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリア、ファイルハンドラ作成失敗時のフォールバックを実装。
    - utils.process_priority — プロセス優先度設定（Windows / POSIX を吸収）、CPU affinity 設定補助を実装。
  - ポートフォリオ構築関連（純粋関数群、メモリ内計算）:
    - portfolio.portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights を実装（スコアでのソートやフォールバック動作を含む）。
    - portfolio.risk_adjustment: apply_sector_cap（セクター集中の新規候補除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。
    - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score の配分方法、単元株丸め、aggregate cap のスケーリング、コストバッファ考慮）を実装。
  - 解析・検証ツール:
    - tools.paper_verification_report.py — Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し PASS/FAIL を判定。しきい値（稼働率99%、成立率90% 等）を定義。
  - データベース連携:
    - sqlite3 と DuckDB の接続を利用する実行/監視スクリプトを追加。monitoring 用テーブル初期化関数 init_monitoring_db を呼び出すことで冪等に監視テーブルを保証。
  - .env パーサ実装:
    - クォート（' "）付き値のバックスラッシュエスケープ対応、export プレフィックス対応、インラインコメント処理（非クォート時の '#' 扱い）、既存 OS 環境変数を保護する protected オプション等を実装。

Changed
- 設計・動作方針
  - run_monitoring は KABUSYS_ENV にかかわらず「本番の sqlite_path」を使用する（監視は常に本番 DB を参照する設計）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離する設計を採用。
  - setup_logging はログ出力を stdout に向ける（stderr ではない）ため、cron 等で stdout/stderr を一本化してリダイレクトする運用に合わせた挙動。
  - process_priority.set_process_priority は Windows と POSIX の差を吸収し、権限不足や未対応プラットフォームでは警告を出してフォールバック。

Fixed
- 安定性・堅牢性向上
  - .env 読み込みでファイル読み込み失敗時に警告を出して継続するように（テスト環境等で安全）。
  - logging_setup: ログディレクトリ作成失敗時にファイル出力を無効化しても StreamHandler で継続するようにフォールバック処理を実装。
  - process_priority / set_cpu_affinity は AccessDenied や未実装例外を捕捉して警告出力にとどめる（起動失敗を防止）。
  - run_execution / run_monitoring の停止フラグ（data/stop_requested.flag）検出を追加し、安全に起動/終了できる仕組みを提供。
  - paper_verification_report はデータ欠損（テーブル未作成や行なし）を扱うため、OperationalError を捕捉して N/A 相当で出力する堅牢化を行った。

Security
- 注意事項
  - .env は絶対にリポジトリにコミットしないよう README 等で徹底する旨を明記（config_setup のヘッダにも同旨を追加）。
  - config_setup と Settings の組み合わせで必須項目が未設定の場合は ValueError を発生させることで起動前に明確に失敗する設計。

Notes / Defaults / 環境変数（抜粋）
- 主要な環境変数とデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: INFO（既定）
  - LOG_DIR: logs/（既定）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、既定: 60）。不正値はデフォルトにフォールバック。
  - PAPER_FILL_MODE: paper_trading 時の挙動（instant|partial|never|reject、既定: instant）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1、既定: 0）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するフラグ

Known limitations / TODO
- portfolio.position_sizing:
  - lot_size は全銘柄共通の想定（将来的に銘柄別の lot_map に拡張予定）。
  - price の欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、前日終値等のフォールバック導入を検討。
- research.factor_research:
  - モジュール実装途中（ファイル末尾が切れている箇所があり、未完成の関数が含まれる可能性あり）。今後の拡張でファクター計算ロジックの完成を予定。

Acknowledgements
- 初回リリースに含まれる主要機能は設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に準拠して実装されています。今後のリリースでより多くのテスト、エラー処理、ドキュメントを追加する予定です。