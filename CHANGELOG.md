CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
重大なリリース、追加、修正、既知の問題などを日本語でまとめています。

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Deprecated: 廃止
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------
- 現時点で未リリースの変更はありません。

0.1.0 - 2026-04-18
-----------------
初回公開リリース。プロジェクトのコア機能および運用用ユーティリティを実装。

Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 環境設定・読み込み
  - .env の自動読み込み機能を実装（プロジェクトルートが特定できる場合のみ）。  
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env のパース機能を堅牢化（export 形式、シングル/ダブルクォート、エスケープ、行末コメント対応）。
  - Settings クラスを実装し、環境変数をプロパティ経由で型安全に扱えるようにした。
  - 必須/オプション設定（J-Quants, kabuステーション, DBパス, ログ等）をプロパティとして公開。

- 設定ウィザード CLI
  - python -m kabusys.config_setup による対話式 .env 作成/更新ウィザードを追加。
  - 既存 .env の読み込み・マスク表示、選択肢・デフォルト提示、保存確認をサポート。
  - .env 出力テンプレートには注意喚起（.env をコミットしない）を含む。

- 設定検証 CLI
  - python -m kabusys.validate_config により起動前検証を実装。
  - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml 存在と YAML パース（PyYAML がある場合）を行う。
  - --strict オプションにより警告を失敗扱いにできる。
  - 本番 (live) 向けの追加ガード（LINE 設定未設定警告、KILL_FLAG_CLEAR_ON_START の警告）。

- 実行 / 監視の起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。プロセス優先度を設定し、SQLite / DuckDB に接続してエンジンを起動。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite（data/paper_trading.db、または環境変数で上書き）を使用して本番 DB と分離。
    - BrokerClientFactory により本番/モックブローカーの切替サポート。
    - PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を参照して監視テーブルを初期化。

- 監視 DB 初期化支援
  - init_monitoring_db 呼び出しにより監視用テーブルの冪等初期化を確実に行う（実装は monitoring パッケージに依存）。

- ロギングユーティリティ
  - setup_logging 関数を追加。全起動スクリプトで共通に使用することでログ設定を統一。
  - stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーにセットアップ。ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/。
  - ファイル出力失敗時はコンソールのみで継続する堅牢設計。

- プロセス優先度 / CPU Affinity ユーティリティ
  - set_process_priority/set_cpu_affinity 実装（Windows / POSIX の差分を吸収）。
  - 権限不足等で失敗した場合は警告を出して処理を継続。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合のフォールバックを実装。
  - portfolio.risk_adjustment
    - セクター集中上限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターの扱い等）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - portfolio.position_sizing
    - position size 計算（risk_based / equal / score 配分）を実装。lot_size（現状共通単元）、max_position_pct、max_utilization、cost_buffer を考慮。
    - aggregate cap によるスケールダウンと、小数端数の公平な配分ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から期間指定で検証レポートを生成。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を出力。
    - P95 計算、N/A 表示の整備、閾値定義を実装。

- 研究用ファクター計算（研究モジュール）
  - research.factor_research にてモメンタム/MA/ATR 等のファクター計算の骨格を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Deprecated / Removed / Security
- .env は絶対に Git にコミットしない旨をドキュメント出力（config_setup の .env テンプレート）で明示。

Notes / Migration
- データベース
  - 実行と監視で使う SQLite の分離: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用するため、本番データベースと完全に分離される。
  - 監視モジュールは環境にかかわらず設定された sqlite_path（本番用）を使用する挙動があるため、運用時は注意。

- ログ出力
  - デフォルトでは logs/<app_name>.log に日次ローテーションで出力。ログディレクトリ作成に失敗した場合は stdout のみになる。

Known issues / TODO
- research.factor_research はファイル末尾で未完（コードが途中で切れている箇所あり）。実装の継続が必要。
- position_sizing:
  - 個別銘柄ごとの lot_size を将来的にサポートするための TODO が存在。
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる点についての注記あり。フォールバック価格（前日終値など）を利用する拡張を検討する必要がある。
- 一部の外部依存（psutil, duckdb, PyYAML など）が環境に存在しない場合は機能制限や警告が発生する。デプロイ前に依存関係を整備すること。

参考
- 起動スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

以上。追加のリリースノートや差分を反映したい場合は変更箇所（ファイル/関数）を教えてください。