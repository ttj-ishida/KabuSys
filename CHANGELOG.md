# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般的なバージョニングは semver に従います。

## [0.1.0] - 2026-04-19

### 追加
- プロジェクト初期リリース。
- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト: 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag ファイルで検知。
    - 監視は環境（KABUSYS_ENV）に関係なく本番用 sqlite_path を使用して DB に接続。
    - プロセス優先度を最初に "high" に設定する処理を組込。
    - duckdb の接続も確立（duckdb_path）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成を組込（paper_trading 時は MockBrokerClient 利用想定）。
    - エンジンは別スレッドで run_session() を実行し、停止フラグを監視して安全停止する仕組みを実装。
    - 起動時にプロジェクト data/execution.pid ファイルへ PID を扱う仕組み（pid_file の利用）。
- 設定管理
  - config.py
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
    - Settings クラスを実装し、各種設定値（J-Quants トークン、kabu API、DB パス、paper_trading の挙動、監視閾値、PID/kill flag パス、環境判定など）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）をサポート。
- 設定支援・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 秘密値は入力後の確認表示でマスク（****）される。
    - 保存時にテンプレート形式で .env を書き出す。
  - validate_config.py
    - .env と config/*.yaml の静的検証 CLI を追加（--strict モードで警告を失敗として扱う）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パス（親ディレクトリ存在確認）、config YAML ファイルの存在確認とパース（PyYAML が無い場合はスキップして警告）、本番時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（ログディレクトリ: logs/、日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR からの設定・引数上書きに対応。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - stdout を使用することでスケジューラ実行時のリダイレクトを考慮。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows と POSIX（Linux/macOS/FreeBSD）での優先度設定を抽象化して提供。権限不足や未対応 OS は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピン留めする機能を実装（権限不足時は警告でスキップ）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates(): BUY シグナルをスコア降順（同点は signal_rank の小さい方を優先）で上位 N 件を選択。
    - calc_equal_weights(), calc_score_weights(): 等配分とスコア加重配分（全スコアが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中上限（max_sector_pct）に基づき新規候補を除外するロジック。sell_codes（当日売却予定）によりエクスポージャー計算から除外する。unknown セクターは上限適用外。
    - calc_regime_multiplier(): market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") に基づく銘柄ごとの発注株数計算を実装。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）、cost_buffer を考慮した保守的見積もりと aggregate cap によるスケーリングロジックを実装。
    - スケーリング後の残余キャッシュを用いた端数処理（lot 単位での追加配分）を行うことで再現性ある割当を行う。
- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を各スクリプト起動時に冪等に呼び出して監視テーブルの存在を保証。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）から指標を集計して検証レポートを出力するツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg/max/P95）。
    - P95 計算、日付フィルタ（--from / --to）、DB パスの引数/環境変数指定をサポート。
    - デフォルト基準値（閾値）を定義して PASS/FAIL の判定を行う（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms など）。
- 研究用ファイル群
  - research/factor_research.py
    - ファクター計算のためのスケルトンと定数（モメンタム、MA200、ATR、出来高等）を追加。DuckDB 接続を受け prices_daily/raw_financials から計算する設計方針を記載（関数実装の一部が継続中）。

### 変更
- なし（初期リリース）。ただし実装上の注意点をドキュメント的に明記:
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する（監視データを本番 DB に集約する設計）。
  - logging_setup はログディレクトリ作成に失敗した場合でも stdout ログにフォールバックしてプロセス継続する。

### 修正
- なし（初期リリース）。

### 削除
- なし（初期リリース）。

### 既知の注意点 / TODO
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、現状はスキップしているためエクスポージャーが過少評価される可能性がある。将来的には前日終値や取得原価などのフォールバック価格を導入する予定。
- research/factor_research.py は未完（calc_momentum の実装途中で切れている）。今後 DuckDB を用いた各ファクター計算処理を実装予定。
- 一部の機能は外部モジュール（psutil、duckdb、PyYAML 等）に依存する。これらが無い場合は該当チェックや機能をスキップして警告を出す挙動になっている。

---

注: この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートに反映する際は、コミット履歴やリリース担当者による確認を行ってください。