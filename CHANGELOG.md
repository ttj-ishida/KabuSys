# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
このリポジトリの初期公開バージョンは v0.1.0（パッケージ内部 __version__ に基づく）です。

※日付はこのコードベースを確認した日付です：2026-04-19

## [Unreleased]

- 特になし。

## [0.1.0] - 2026-04-19

Added
- 基本アプリケーション構成
  - パッケージ初期版を追加。パッケージメタ情報は src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を検知してループを安全に終了。
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（デフォルト data/monitoring.db）を使用する設計。
    - SQLite と DuckDB の接続初期化、監視 DB スキーマ初期化処理を実施。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository・OrderManager・RiskManager・Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) により実行中エンジンを停止可能。実行 PID は data/execution.pid に管理。
    - プロセス優先度を起動時に "high" に設定。

- 設定・環境変数管理
  - config.py
    - Settings クラスを実装し、環境変数から設定値を取得する API を提供。
    - .env 自動読み込み機構: プロジェクトルート（.git か pyproject.toml）を検出し、.env → .env.local の順でロード（OS 環境変数を保護）。
    - 環境変数のパース強化: export プレフィックス、シングル/ダブルクォート、エスケープ文字、インラインコメント処理に対応。
    - 主要な設定値とデフォルトを明示（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH など）。
    - PAPER_FILL_MODE は有効値チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）と LOG_LEVEL の検証。

  - config_setup.py
    - .env を対話式に作成・更新するウィザード CLI を追加。
    - 入力補助、既存 .env の読み込み、シークレット項目のマスク表示、保存前確認などの UX を提供。
    - 書き出しフォーマットとデフォルト値を定義。

  - validate_config.py
    - 起動前に .env や config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がある場合）を実施。
    - live 環境向けのガードチェック（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定等）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates: スコア降順、同点は signal_rank）と重み算出（等配分 calc_equal_weights、スコア加重 calc_score_weights）。
    - スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を制限し、既存保有比率が閾値を超えるセクターの新規候補を除外。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を提供。未知のレジームはフォールバック（1.0）し警告。
    - 実装に一部注意点（price 欠損時の取り扱い TODO をコード内に記載）。
  - portfolio/position_sizing.py
    - 株数算出ロジック（allocation_method: risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積りを実装。
    - 利用可能現金を超えた場合のスケールダウンと残差配分ロジック（fractional remainders）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを提供。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーへ設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみ継続。
    - LOG_LEVEL / LOG_DIR / 引数での上書きをサポート。
  - utils/process_priority.py
    - プロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice）を抽象化して提供。
    - CPU affinity 設定ヘルパー set_cpu_affinity を提供。
    - psutil の権限不足や未実装ケースは警告を出して安全にスキップ。

- データ分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・API レイテンシ（P95 等）を出力するレポート生成 CLI を追加。
    - 基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタと --db オプションをサポート。

- 研究用ファクターモジュール（実装開始）
  - research/factor_research.py
    - momentum 等のファクター計算（1M/3M/6M リターン、MA200 乖離、ATR、出来高指標）を設計・部分実装。DuckDB を利用して prices_daily / raw_financials を参照する設計。
    - 戻り値は (date, code) ベースの dict リストを想定。
    - （ファイルの後半は一部未収録／未完の部分あり）

Changed
- n/a（初期リリースのため該当なし）。

Fixed
- n/a（初期リリースのため該当なし）。

Security
- n/a（初期リリースのため該当なし）。

Notes / 実行時の重要な挙動（ドキュメント的補足）
- 環境変数自動読み込み
  - デフォルトで .env/.env.local をプロジェクトルートから自動ロードする。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- ペーパートレードの完全分離
  - run_execution は KABUSYS_ENV=paper_trading 時、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用することで本番データベースと分離する。
- 監視（monitoring）
  - run_monitoring は監視用 DB 初期化を行い、KABUSYS_ENV に関わらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっている点に注意。
- ログ
  - デフォルトで stdout にログを出力しつつ、logs/ 配下へ日次ローテートでファイル出力を行う。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみになる。
- プロセス優先度
  - 起動スクリプトは起動直後に set_process_priority("high") を呼び出す。権限がない場合は警告ログを出してスキップする。

Known issues / TODO（コード内注記）
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）時のフォールバックが未実装（TODO コメントあり）。
- position_sizing の将来拡張: 個別銘柄ごとの lot_size を取れるようにする（TODO コメントあり）。
- research/factor_research.py: ファイル末尾に未完のコード断片あり（実装継続が必要）。
- 一部の YAML 検証は PyYAML が未インストールの場合スキップされる（validate_config）。

環境変数（主な一覧・デフォルト）
- 必須（runtime に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用系 / デフォルトあり
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - PAPER_FILL_MODE — default: instant (valid: instant|partial|never|reject)
  - PID_FILE_PATH — default: data/execution.pid
  - KILL_FLAG_PATH — default: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — default: 0
  - MONITOR_POLL_INTERVAL — default: 60 (秒)
  - LOG_DIR — default: logs/

コマンドライン（エントリポイント）
- python -m kabusys.run_monitoring  （監視ループ起動）
- python -m kabusys.run_execution   （ExecutionEngine 起動）
- python -m kabusys.config_setup    （対話式 .env ウィザード）
- python -m kabusys.validate_config （設定検証ツール）
- python -m kabusys.tools.paper_verification_report （Paper Trading レポート）

ライセンスや配布に関する注意
- .env は機密情報を含むため絶対に Git にコミットしない旨が config_setup のヘッダに記載されています。

---

（この CHANGELOG はコードを読み取って推測した機能・挙動をもとに作成しています。実際の動作確認や運用手順・セキュリティ要件等は別途テスト・レビューを行ってください。）