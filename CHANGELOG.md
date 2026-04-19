# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリの現状のコードベースから推測して作成した初期リリース向けの変更履歴です。

<!-- 変更履歴は時系列（最新が上）に記載します -->

## [0.1.0] - 2026-04-19

初回リリース (推定)。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、および検証ツールを追加。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度を上げて実行し、スレッドでエンジンを動作させる。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - 停止制御: プロジェクト直下の data/stop_requested.flag を監視して安全に停止。
    - 実行時 PID を data/execution.pid に保存する仕組み（Engine 側に PID ファイルを渡す）。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行。
    - RiskManager 用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視用テーブルを初期化。
    - 停止制御: data/stop_requested.flag を検知してループ終了。KeyboardInterrupt による終了もハンドリング。
    - check_once() 実行中の例外を捕捉して次回ポーリングに影響させないようにログを出力。

- 設定管理 / 設定ツール
  - config.py
    - Settings クラスを導入し、環境変数から設定値を取得する共通インタフェースを提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG 等のプロパティを追加。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
    - KABUSYS_ENV の有効値検証（development/paper_trading/live）およびログレベルの検証を実装。
    - 自動 .env 読み込み機能を追加（プロジェクトルート(.git または pyproject.toml) を基準に .env/.env.local を読み込む）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須環境変数のチェック用 _require 関数を提供。

  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。主要な設定項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、ログレベル、Kill Switch 設定等）をサポート。
    - 既存 .env の読み込み、マスク表示（シークレット項目）やデフォルト提示、保存前の確認を実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の問題を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック（PyYAML が利用可能な場合）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（select_candidates）及び重み算出（calc_equal_weights, calc_score_weights）を追加。スコア合計が 0 の場合は等金額配分にフォールバックし警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加。既存ポジションのセクター別時価を計算し、上限超過セクターの新規候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear に対応、未知値はフォールバックと警告）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジックを追加（allocation_method: "risk_based","equal","score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（available_cash による aggregate cap）、手数料・スリッページを考慮した cost_buffer、スケーリングロジック、残差分の分配アルゴリズムを実装。

  - portfolio/__init__.py
    - 上記の関数群をエクスポートして簡易利用可能に。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。StreamHandler を stdout に出力し、TimedRotatingFileHandler で日次ローテーション（30 日保持）する実装。
    - ログレベルとログディレクトリ解決の優先度、既存ハンドラのクリア処理、ファイル作成失敗時のフォールバックを実装。

  - utils/process_priority.py
    - プロセス優先度・CPU アフィニティ設定ユーティリティを追加。Windows / POSIX の差分を吸収して set_process_priority, set_cpu_affinity を提供。権限不足や未対応 OS の場合は警告を出力してスキップ。

- ツール / レポート
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。SQLite の trade_logs / system_status / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。

- 研究用モジュール（部分実装）
  - research/factor_research.py（初期実装）
    - DuckDB 接続を受けてモメンタム・移動平均乖離・ATR・出来高系の計算方針を実装するモジュールを追加（calc_momentum 等の骨格と定数を配置、設計方針を明記）。実装は継続予定（ファイルの末尾は未完）。

- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### 変更
- なし（初回リリース相当の追加群のみ）

### 修正
- なし（初回リリース相当）

### 既知の注意点 / 使用上の重要なポイント
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や CWD が別の場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に環境変数をロードしてください。
- PAPER_TRADING 環境では execution が paper_trading 用の SQLite を使い、本番データベースと完全に分離されます。PAPER_FILL_MODE の値は有効候補を満たす必要があります（invalid な値は ValueError を発生させます）。
- run_monitoring は監視 DB として常に settings.sqlite_path を使用する設計です（環境に依存せず本番 sqlite_path を参照）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。
- process_priority / cpu_affinity 設定は権限やプラットフォームに依存します。失敗時は警告でスキップされます。
- research/factor_research.py は設計方針と一部の関数骨格が実装されていますが、完全実装はまだのため運用前に追加実装が必要です。

### セキュリティ
- .env ファイルは Git にコミットしないでください（config_setup にもその旨の注意を明記）。

---

今後のリリースでは以下を予定（推奨）
- research/factor_research の完成（DuckDB クエリ実装）
- ExecutionEngine / SystemMonitor の詳細動作とエラーハンドリングの拡充（より厳密な監視・再試行ロジック）
- 単体テスト・統合テストと CI 設定の追加
- ドキュメント（README、運用ガイド、環境変数一覧）の整備

以上。必要であればこの CHANGELOG を英語版に翻訳したり、項目の粒度を調整したりできます。どの形式で出力するか指示してください。