# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はこの生成時点のリリース日です。

## [0.1.0] - 2026-04-22

初回リリース — 基本機能の実装と運用用ユーティリティ群を提供します。

### 追加 (Added)
- 全体
  - パッケージ初版を公開。主要サブモジュール（execution, monitoring, portfolio, utils, research, tools）を実装。
  - バージョン情報を `kabusys.__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（project/data/stop_requested.flag）を検知して安全にループを終了。
    - 監視用 DB は環境に依らず本番の sqlite_path を使用して接続・初期化。
    - DuckDB へも接続し SystemMonitor に渡す。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して paper_trading 専用 DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等を組み立てて ExecutionEngine を起動。
    - 停止フラグ・PID ファイル管理およびスレッドによるセッション実行をサポート。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み（.env → .env.local、OS 環境変数優先）を実装。プロジェクトルート検出は .git または pyproject.toml を基準。
    - 複雑な .env パースを実装（export 形式、クォート内エスケープ、インラインコメントの扱いなど）。
    - Settings クラスを提供し、各種環境変数をプロパティで取得（検証付き）。例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、PAPER_FILL_MODE の検証、KABUSYS_ENV の妥当性検査等。
    - paper_trading 用の専用 sqlite パス（PAPER_TRADING_SQLITE_PATH）、PID / kill flag のパス、監視閾値（CPU/Memory/Disk）などをプロパティとして提供。
    - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグをサポート。

  - config_setup.py
    - .env 初期作成・更新の対話型ウィザードを追加（キー一覧、デフォルト、シークレットマスク表示、書き込み）。
    - .env の読み取り・書き込みユーティリティ、対話入力のバリデーションを実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 監視/検証ツール
  - monitoring.monitoring_db への初期化呼び出しを各起動スクリプトで実行（監視テーブルを保証）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数 等を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。
    - P95 計算、各種 null/データ不足に対する N/A ハンドリングを実装。

- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を追加。
    - スコアが全て 0 の場合のフォールバック動作（等分配）を明示。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を追加。既存ポジションからセクター別エクスポージャ算出、上限超過セクターの新規候補除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算ロジックを実装（risk_based / equal / score の各方式）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金によるスケールダウン）、cost_buffer の扱い、端数処理（fractional remainder による追加配分）を実装。
    - 価格欠損時のスキップやログ出力によるフォールバックを適用。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。コンソール (stdout) と日次ローテーションのファイル出力をルートロガーに設定。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順を実装。ファイルハンドラ作成失敗時はコンソールのみで続行。
    - 既存ハンドラを安全にクローズしてから再設定。

  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収するプロセス優先度設定ユーティリティを追加。psutil を使用。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は警告出力してスキップ。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム、MA200、ATR、流動性・出来高系など）の設計と定数を実装。DuckDB 接続を受け、prices_daily / raw_financials を参照する想定の API を提供。
    - calc_momentum のインターフェース・定義および定数が追加（実装はファイル末尾で続く設計）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 破壊的変更 (Breaking Changes)
- 初版リリースのため特記すべき既存ユーザー向けの破壊的変更はありません。ただし初回導入時の注意点は以下を参照してください。
  - .env ファイルは Git に絶対にコミットしないでください（config_setup.py のヘッダに注意書きあり）。
  - 自動 .env 読み込み（プロジェクトルート探索）を無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - Paper Trading を行う場合は KABUSYS_ENV を `paper_trading` に設定すると data/paper_trading.db を使用し本番データと分離されます。

### セキュリティ (Security)
- 現時点で特記すべきセキュリティ脆弱性は報告されていません。ただし以下に注意してください:
  - .env に機密情報（API トークン・パスワード）を平文で保持する設計のため、ファイル権限管理と Git 管理に注意すること。
  - process_priority の操作には OS 権限が必要な場合がある（権限不足時は警告のみで続行）。

### マイグレーション / 運用上の注意
- 起動前に `python -m kabusys.config_setup` を実行して .env を生成し、`python -m kabusys.validate_config` で検証してください。
- 本番運用（KABUSYS_ENV=live）の場合、LINE 通知トークン（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を設定しておくことを推奨します（validate_config で警告を出します）。
- ログはデフォルトで logs/ 配下に日次ローテートで出力されます。ログディレクトリの作成権限がない場合はコンソールログのみになります。
- Paper Trading 用 DB はデフォルトで data/paper_trading.db。変更する場合は環境変数 PAPER_TRADING_SQLITE_PATH を設定してください。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）は無視され、デフォルト 60 秒にフォールバックします。

---

今後の予定:
- research/factor_research.py のファクター実装の続き（calc_momentum 等の完成）。
- Execution/Monitoring コンポーネントの統合テストと詳細なログ・メトリクス強化。
- strategy モジュールや運用向けドキュメントの拡充。