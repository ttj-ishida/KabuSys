# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
日付はリリース日または変更日を示します。

なお、本 CHANGELOG は与えられたソースコードの内容から実装・設計意図を推測して作成しています。

## [Unreleased]

- 進行中 / 要検討
  - research/factor_research.py のモメンタム系ファクター実装が途中（ファイル末尾で切れている）ため、計算ロジックの完成・ユニットテスト追加が必要。
  - テストカバレッジ、CI 設定、ドキュメント（API レベル）の整備。
  - 監視・実行コンポーネントのさらに堅牢なエラーハンドリングやメトリクス export（Prometheus 等）の検討。
  - ペーパートレードのモック挙動（PAPER_FILL_MODE）やスリッページ/手数料のシミュレーション拡張。

---

## [0.1.0] - 2026-04-21

Added
- 基本機能の初期実装（一通りの CLI / ランタイム / ポートフォリオ構築ロジックを実装）
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI。
      - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（data/paper_trading.db）を使用して本番 DB から分離。
      - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた安全停止機構を備える。
      - プロセス優先度を "high" に設定する処理を起動時に実行。
    - run_monitoring.py
      - SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用 DB 初期化と duckdb 接続を行う。
      - 停止フラグ検知・KeyboardInterrupt の処理を含む安全なループ実装。
  - 環境設定・検証ツール
    - config_setup.py
      - .env を対話式に作成/更新するウィザードを実装。
      - 各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を網羅。
      - .env 書き込み時に注意書き（.env をコミットしない等）を含むテンプレート出力。
    - validate_config.py
      - 起動前に .env と config/*.yaml の不備を検出する CLI。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が無ければ警告）および本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）を実装。
  - 設定管理
    - config.py
      - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。OS 環境変数は保護）。
      - .env 行パーサは export 形式やシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
      - Settings クラスでアプリケーション設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、ペーパートレード関連、監視閾値、PID/kill フラグパス、ログレベル、環境種別判定等）。
      - 設定値の検証（有効な KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検査）を含む。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定する共通関数。
      - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
      - ログレベル・ログディレクトリの解決順を明示。
    - utils/process_priority.py
      - Windows/Linux/macOS 間の差を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS など）を設定するユーティリティ。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足や未対応プラットフォームは警告を出してスキップする設計。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナルの候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存保有を考慮して候補をフィルタリング）。
      - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマップ。未知値は警告のうえ 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - 各銘柄の発注株数決定ロジック calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超えた場合のスケーリングと残差処理）、cost_buffer の考慮などを含む堅牢なアルゴリズム。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計してレポート出力。
      - P95 計算、期間フィルタ、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）による PASS/FAIL 判定を実装。
  - パッケージメタ
    - __init__.py にてパッケージバージョンを "0.1.0" に設定。

Changed
- N/A（初期リリースのため既存挙動の変更なし）

Fixed
- N/A（初期リリース）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の注意点
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やパッケージ化後に動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化できます。
- run_monitoring は「監視 DB（SQLite）」に対して常に本番 sqlite_path を使う実装になっているため、開発環境で監視 DB を分離したい場合は環境変数 SQLITE_PATH を明示的に設定してください。
- run_execution は paper_trading モードで paper_sqlite_path を使用することで、本番データベースとの完全分離を図っています。
- process_priority や CPU affinity の設定は権限の制約により失敗する可能性があるため、失敗時はログに警告を残してスキップします。
- portfolio/position_sizing のスケーリング処理では lot_size 単位での端数処理を行っており、端数処理により期待通りの利用金額にならない場合があります。将来的に銘柄別単元の導入やより厳密なコスト見積もりを検討してください。

---

過去の変更履歴が存在する場合はここに追記してください。必要に応じて各リリースでの具体的なコミットや差分、影響範囲を補足で記載することを推奨します。