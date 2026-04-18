CHANGELOG
=========

All notable changes to this project will be documented in this file.
The format is based on "Keep a Changelog" and this project adheres to
Semantic Versioning.

現在の日付: 2026-04-18

[Unreleased]
------------

- なし（初回リリースを参照してください）

[0.1.0] - 2026-04-18
-------------------

Added
- プロジェクト初期リリース。
- 実行スクリプト:
  - run_execution.py: 実取引 / ペーパートレード両対応の ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを選択。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag により安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知・例外時のログ出力・KeyboardInterrupt のハンドリングを実装。
- 設定管理:
  - config.py: 環境変数・.env 自動読み込み機能を実装。
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）。
    - .env / .env.local の読み込み順と保護キー（既存 OS 環境変数は保護）をサポート。
    - .env パースの強化（export 形式対応、クォート内のエスケープ処理、インラインコメント処理等）。
    - Settings クラスを提供し、各種設定（DB パス、Paper trading 設定、監視しきい値、ログレベル等）をプロパティで取得可能。
- 設定ツール:
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - シークレット入力マスク、選択肢、デフォルト値、確認プロンプトを実装。
    - .env ファイルのテンプレート出力（注意文含む）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ検査、config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）。
    - KILL フラグや LINE 通知設定など本番向けガードを実装。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセスユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせる。
    - ログディレクトリ自動作成、作成失敗時はファイルハンドラをスキップして継続。
    - ログレベル解決ロジック（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収、例外発生時は警告を出してスキップ。
    - set_process_priority(level) / set_cpu_affinity(count) を提供。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: 候補選定・重み付け（等配分・スコア加重）を実装。
    - スコア全てが 0 の場合は等分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター上限フィルタ apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
    - 未知セクター / 未知レジームに対するフォールバックとログ警告を実装。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap のスケールダウン（残差の取り扱いで再分配）を含む詳細なアルゴリズムを実装。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db、--db / 環境変数で指定可能。
    - P95 計算、欠損時の N/A 表示、しきい値はソース内定義でわかりやすく記載。
- 研究用モジュール:
  - research/factor_research.py: Momentum などのファクター計算モジュール（設計と一部実装）を追加（prices_daily / raw_financials を想定して DuckDB 経由で計算）。
- パッケージ情報:
  - __init__.py: バージョン番号を __version__ = "0.1.0" に設定。公開モジュール一覧を __all__ で定義。

Changed
- 初回リリースのため、設計上の注意点・デフォルト値・フォールバック動作を多数文書化（関数 docstring やモジュールレベルの説明に反映）。
- ログハンドラの挙動: 標準出力を stdout に統一（cron 等でのリダイレクト運用を意識）。

Fixed
- 実行中の例外耐性を強化:
  - run_monitoring の監視ループで check_once() が例外を投げてもループ継続し例外をログ出力するように変更。
  - run_execution のスレッド監視と停止処理で停止フラグ検知時に安全に engine.stop() を呼ぶ実装と、最終的に DB 接続を必ず close する finally を追加。
- 設定ファイル読み込みの堅牢化:
  - .env パースでクォート内のバックスラッシュエスケープを考慮するように改善。
  - export KEY=val 形式やインラインコメントの扱いを改善。

Security
- .env ファイル生成テンプレートに「絶対に Git にコミットしないこと」の注意を明記。
- 環境変数取得で必須項目が未設定の場合に明示的な ValueError を出して起動前に検出できるようにした（Settings._require）。

Notes / Migration
- 初回リリースのため、既存ユーザーは以下を確認してください:
  - .env（または .env.local）をプロジェクトルートに配置し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須環境変数を設定してください。config_setup.py のウィザードで .env を生成できます。
  - KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかを指定してください。
  - ペーパートレードは paper_sqlite_path（環境変数: PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）で完全に本番 DB と分離されます。
  - ログは既定で logs/ に出力されます。権限やディレクトリ作成に問題がある場合はコンソール出力のみになります。
  - 実行スクリプトは data/stop_requested.flag により外部プロセスから停止可能です。kill/stop フラグの扱いに注意してください。
  - process_priority の設定は OS 権限により失敗する場合があり、その場合は警告が出力されますが実行は継続します。

参考: 主な環境変数
- KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START, LOG_DIR

――――
（この CHANGELOG はコードベースから推測して作成しています。実装の詳細やリリースノートの正確な要旨は開発履歴や git コミットログに基づいて更新してください。）