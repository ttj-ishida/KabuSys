CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （今後の変更をここに記載）

[0.1.0] - 2026-04-19
--------------------

Added
- 基本パッケージを追加（初回リリース）。
  - パッケージ識別子: kabusys、バージョン 0.1.0
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。  
    - KABUSYS_ENV によるペーパートレード分離（paper_trading の場合は専用 SQLite を使用し MockBrokerClient を利用）。
    - プロセス優先度を起動時に "high" に設定。
    - stop フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）。
    - スレッドでエンジンを起動し、停止フラグを監視して安全に停止。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプトを実装。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（環境に依存せず監視情報を一元化）。
    - stop フラグ検出でループ終了、例外時のログ出力とリトライ継続。
- 環境設定管理
  - config.py: .env 自動ロード機能（プロジェクトルート検出による .env / .env.local の読み込み）、環境変数のパース（クォート・エスケープ・インラインコメント処理対応）、Settings クラスによる設定プロパティを提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等の既定値とプロパティバリデーション（env, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 設定関連 CLI
  - config_setup.py: .env を対話的に作成/更新するウィザードを実装（既存値の読み込み、シークレットマスク、確認後保存）。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスと YAML パース検証、live 環境向けのガード（LINE 設定や Kill Switch 設定の警告）。--strict オプションで警告を FAIL 扱いにできる。
- Portfolio 構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights）を実装。スコア合計が 0 の場合のフォールバックログあり。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバックと警告。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、per-position 上限・aggregate cap のスケーリング、cost_buffer を考慮した保守的見積りをサポート。価格欠損時のスキップやログ出力あり。
  - portfolio/__init__.py による公開 API 統合。
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日分保持）をルートロガーに設定。
    - LOG_DIR 環境変数・引数でディレクトリ指定可能。既存ハンドラのクリア処理を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定補助を実装。アクセス権限不足や未対応 OS の場合は警告ログでスキップ。
- モニタリング DB 初期化（監視テーブルの冪等初期化）機能の統合（init_monitoring_db を各スクリプト起動時に呼び出す）。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB（デフォルト data/paper_trading.db）から指標を集計して検証レポートを生成する CLI を追加。  
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシなど。閾値による PASS/FAIL 判定を実装。
- research/factor_research.py: DuckDB を利用したファクター計算モジュールを追加（モメンタム / MA / ATR / ボリューム等の算出方針を記述）。（一部実装途中）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- ペーパートレードと本番 DB の完全分離を意図しており、settings.is_paper により paper_sqlite_path を利用する実装になっている。
- .env の自動ロードはプロジェクトルートが検出できた場合のみ行われる（.git または pyproject.toml を探索）。テスト等で自動ロードを無効にするため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用可能。
- PAPER_FILL_MODE の値検証（instant/partial/never/reject）を行い、不正値は ValueError を送出する。
- Logging: ログディレクトリ作成に失敗した場合でもコンソール出力は継続するように安全策を講じている。
- process_priority/set_cpu_affinity は権限や OS の差分に起因する失敗をハンドリングしており、失敗時は警告ログを出してスキップする。
- position_sizing の aggregate スケーリングは lot_size 単位での再分配アルゴリズムを備え、端数扱いは残差の大きい銘柄から lot 単位で追加配分する実装。

Security
- 機密情報（トークン・パスワード）は .env で管理し、config_setup ウィザードでは入力値をマスクして表示。 .env は Git にコミットしない旨を .env ヘッダに明記。

Acknowledgements
- このリリースは初期実装フェーズのため、多くのコンポーネントが今後拡張・堅牢化される予定です。特に research モジュールやバックテスト、実運用ガード（レート制限、リトライ戦略、異常時の自動ロールバック等）は今後の重点対象です。

-----
（注）本 CHANGELOG は提供されたソースコードに基づき推測して作成しています。実際の変更履歴や開発ノートが存在する場合はそちらを優先してください。