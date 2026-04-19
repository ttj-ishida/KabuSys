CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付はこのリリースの想定日です。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本機能の初回リリース。
- 起動スクリプト / サービス
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境変数 KABUSYS_ENV に応じて paper_trading 用の専用 SQLite （data/paper_trading.db）を使用可能。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用する設計。
    - stop flag（data/stop_requested.flag）検知で安全にループを終了。
- 設定関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 強力な .env パーサ実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - Settings クラスにより環境変数を型付きプロパティでアクセス可能（DB パス、PID/kill flag、しきい値など）。
    - 環境チェック（KABUSYS_ENV, LOG_LEVEL 等）とデフォルト値の管理を提供。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。既存値の読み込み、秘匿入力サポート、保存前の確認を実装。
- 検証ツール
  - validate_config.py
    - .env と config/*.yaml の簡易的な設定検証 CLI を追加（必須環境変数チェック、パス存在チェック、YAML パース検証、ライブ環境向けガード等）。
    - --strict オプションで警告を失敗扱いにする機能。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通に使えるログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30 日分保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重出力を防止。
    - LOG_DIR / LOG_LEVEL の環境変数、引数による上書きをサポート。ログディレクトリ作成失敗時はファイル出力をフォールバックして無効化。
  - utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収したプロセス優先度設定と CPU affinity 設定関数を追加。
    - 失敗時は警告を出し処理を継続する安全設計。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）と等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）を追加。
    - スコア合計が 0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定銘柄の除外、unknown セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear 対応、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを追加。
    - 単元株（lot_size）に丸め、per-position 上限および aggregate cap（available_cash）でスケール調整する実装。
    - cost_buffer による手数料・スリッページ考慮、スケーリング時の小数端数処理を安定した順序で再配分するロジックを実装。
- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、レイテンシ（P95 含む）を集計し PASS/FAIL 判定を出力。
    - DB ファイルが存在しない場合やテーブル不備時のフォールバック処理を実装。
- 研究用モジュール（骨格）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム / MA200 / ATR / 出来高関連の定数と calc_momentum の実装開始）。
    - DuckDB を用いた時系列計算を想定して設計。

Fixed
- _get_poll_interval の堅牢化
  - run_monitoring の MONITOR_POLL_INTERVAL を int に変換し、0 以下や不正な値はログ警告のうえデフォルト（60 秒）にフォールバックするように修正。
- logging_setup の既存ハンドラクリア処理
  - 既にハンドラが設定済みの場合に重複登録されないよう、既存ハンドラの flush/close と削除を明示的に行うように変更。
- process_priority の例外ハンドリング強化
  - 権限不足や未実装 API に対して警告ログでフォールバックするようにし、起動失敗につながらない堅牢性を確保。
- .env パーサの改善
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを正しく処理するように実装。無効行は無視。

Security
- .env の取り扱いに関する注意喚起を config_setup の出力に追加（.env を絶対に Git にコミットしない旨のコメントを生成）。
- config.validate で本番環境（KABUSYS_ENV=live）向けに LINE 通知設定不備や KILL_FLAG_CLEAR_ON_START の危険設定を警告。

Removed
- なし（初回リリース）。

Deprecated
- なし。

Known issues / Notes
- research/factor_research.py の calc_momentum 実装は続きが必要（ファイル終端で途中断になっている箇所あり）。詳細なファクター実装および単体テストは今後の課題。
- position_sizing の price 未取得時の挙動に関する TODO が存在（価格欠損時のフォールバック戦略）。
- 一部の機能（ExecutionEngine / SystemMonitor / BrokerClientFactory 等）はこのレポジトリの他ファイルに依存しており、実行にはそれらの実装（および外部ライブラリ: duckdb, psutil, PyYAML 等）の導入が必要。

どう読むか（短いガイド）
- 起動系: run_execution.py / run_monitoring.py をエントリとして利用。両者とも起動時に set_process_priority("high") を呼び出します。
- 設定系: .env は config_setup.py で対話的に作成/更新し、validate_config.py で起動前検査を行ってください。
- ログ: setup_logging を全スクリプトで使うことで一貫したログ管理（stdout + 日次ローテーション）を行えます。
- ポートフォリオ構築: kabusys.portfolio 以下は純粋関数で副作用なし。単体テストが容易になっています。

お問い合わせ・貢献
- バグ報告・改善提案は issue を開いてください。重要な仕様変更やセキュリティ問題は速やかに対応します。