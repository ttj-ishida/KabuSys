CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-20
------------------

Added
- 基本機能の初期実装を追加（初回リリース相当）。
  - パッケージ情報
    - バージョンを __version__ = "0.1.0" として追加。
  - 設定管理 (kabusys.config)
    - .env 自動読み込み機能を実装（プロジェクトルートを自動検出し、`.env` → `.env.local` の順で読み込み）。
    - .env のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォートのエスケープ、インラインコメントの扱い）。
    - Settings クラスを実装し、環境変数から各種設定を取得可能に。
    - 設定値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を組み込み。
    - paper_trading 用の専用 SQLite パス設定（PAPER_TRADING_SQLITE_PATH）を追加。
    - 各種デフォルトパス (DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等) を定義。
  - 設定ツール・検証ツール
    - config_setup: 対話式ウィザード (python -m kabusys.config_setup) で .env を作成/更新する機能を追加。
      - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）をサポート。
    - validate_config: 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加（--strict オプションあり）。
      - 必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML がある場合）等を実施。
      - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
  - 起動スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 DB を使用し本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアントを作成（Mock 実装を差し替え可）。
      - ExecutionEngine の依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立てて起動。
      - data/stop_requested.flag により外部から安全に停止できる仕組みを導入。実行中は execution.pid を利用。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告しデフォルトにフォールバック。
      - Monitoring は実行環境に関わらず本番 sqlite_path を使用して監視データを保存。
      - stop_requested.flag による停止検知、KeyboardInterrupt での終了処理をサポート。
  - ロギング / プロセス制御ユーティリティ
    - utils.logging_setup: 共通ログ設定ユーティリティを追加。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）をルートロガーにセットアップ。
      - LOG_DIR/LOG_LEVEL の環境変数による上書き、ログディレクトリ自動作成時のフォールバック処理を実装。
      - ファイルハンドラ作成失敗時はコンソール出力のみで継続。
    - utils.process_priority: クロスプラットフォームなプロセス優先度設定を追加。
      - Windows / POSIX（Linux/Mac/FreeBSD）向けに優先度（high/normal/low）を適用。
      - CPU affinity 設定ヘルパーも提供（set_cpu_affinity）。
      - 実行権限不足や未対応環境時は警告してスキップ。
  - ポートフォリオ構築ライブラリ (kabusys.portfolio)
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコアでソートし上位 N を選択する処理を実装。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分の計算を実装。スコアが全て 0 の場合は等配分にフォールバックして Warning を出力。
    - risk_adjustment:
      - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合、新規候補から当該セクターを除外する処理を実装。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の算出を実装（未知のレジームは警告して 1.0 をフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算法を実装。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap のスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮などのロジックを実装。
  - モニタリング／検証ツール
    - monitoring.monitoring_db の初期化が run_* スクリプトから呼ばれるように組み込み（監視テーブルの冪等初期化）。
    - tools.paper_verification_report:
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を出力。
      - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
      - 日付フィルタ（--from / --to）と DB パス指定 (--db)、PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
  - 研究用モジュール（下地）
    - research.factor_research にファクター計算ロジックの骨組みを追加（モメンタム / ATR / Value 等の計算方針記載、DuckDB 接続利用）。モメンタム計算ロジックの実装が開始されている（ファイル一部は未完）。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Security
- なし（初回リリース）。

Notes / 実行時注意事項
- 環境変数 / ファイルパスのデフォルト
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE: data/execution.pid（実行時に指定可能）
  - stop フラグ: data/stop_requested.flag（存在検知で停止）
- run_execution は paper_trading モード時に本番 DB と完全に分離された専用 SQLite を使用する設計です。ペーパートレードと本番のデータ混在を避けるため、paper_trading 環境では PAPER_TRADING_SQLITE_PATH を確認してください。
- run_monitoring は環境に関わらず sqlite_path（デフォルト: data/monitoring.db）を使って監視データを記録します。
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）へ出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト目的）。
- validate_config を利用して起動前に設定を検証することを推奨します（本番環境では特に重要）。

開発者向けメモ
- process_priority は権限や OS により動作が制限される可能性があります。AccessDenied 等はログで警告してスキップする実装です。
- position_sizing の将来拡張点:
  - 銘柄ごとの lot_size を stocks マスタに持たせる等の拡張を想定（現状は全銘柄共通 lot_size）。
  - price が欠損（0.0）の場合のフォールバック（前日終値など）を TODO として明記。
- research.factor_research は現状部分実装のため、完全なファクター計算を行うには追加実装が必要。

今後の予定（提案）
- research.factor_research の完全実装（Momentum / Value / Volatility / Liquidity の計算を完成）。
- テストカバレッジの追加（設定パーサ、position_sizing のスケーリングロジック等）。
- コンフィグ YAML の詳細スキーマ検証（現在は存在確認と safe_load による単純パースのみ）。
- モニタリング/アラートの LINE 通知連携実装（現在はトークン受け取りのみ設定値を保持）。

---