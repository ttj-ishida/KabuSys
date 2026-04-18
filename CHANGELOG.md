# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
リリース日: 2026-04-18

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 全体
  - KabuSys の初期実装を追加。パッケージバージョンは __version__ = "0.1.0"。
  - DuckDB / SQLite を使ったデータ保存を前提とした設計。環境変数で DB パスを指定可能。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）と MockBrokerClient を利用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - エンジンはデーモンスレッドで run_session を実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル（data/execution.pid）サポート。
    - デフォルトでプロセス優先度を "high" に設定。

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上でデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了。
    - プロセス優先度を "high" に設定。

- 設定管理
  - config.py:
    - Settings クラスを追加。環境変数から各種設定を取得するプロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値など）。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。.env / .env.local の読み込み順をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加。
    - .env の行パーサは export 文、クォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - paper_trading 用の PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH をサポート。
    - 各種閾値（CPU/MEM/DISK）や PID / kill flag のパス等のプロパティを提供。
    - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を実装。

  - config_setup.py:
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - J-Quants / kabu API / DB パス / LINE / ログレベル / Kill Switch の設定項目をサポート。
    - 既存 .env の読み込み、現在値の再利用、シークレットのマスク表示、保存確認を実装。
    - 作成される .env に対する注意事項（Git にコミットしない等）を明記。

  - validate_config.py:
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在／パース検証（PyYAML がインストールされている場合）などを実施。
    - --strict フラグで警告も失敗扱いにするモードを追加。
    - 本番 (live) 時の追加チェック（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で上位 N を選択する関数。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（スコア全てが 0 の場合は等金額にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用して候補をフィルタする関数（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 等分・スコア重み・リスクベースの発注株数算出。単元株（lot_size）丸め、1銘柄上限、利用可能現金による aggregate cap、cost_buffer による保守的見積り、スケールダウンと残余配分ロジックを実装。
  - portfolio パッケージの __init__ で主要関数をエクスポート。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - DuckDB の prices_daily / raw_financials を利用したモメンタム、ボラティリティ、バリュー、流動性等のファクター計算モジュールの基盤を追加（モジュール構成と定数を定義、momentum 計算関数等の実装を想定）。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB を解析して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を算出して判定（PASS/FAIL）を出力。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - --from / --to / --db オプションで期間・DB パスを指定可能。

- ユーティリティ
  - utils/logging_setup.py:
    - setup_logging 関数を追加。全起動スクリプトで共通のログ設定を行う。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで続行。
    - 既存ハンドラを一旦 flush/close してから再設定することで二重設定を防止。
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX を吸収するプロセス優先度設定。権限不足等の失敗は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 指定数の CPU コアにプロセスを固定する機能（存在しない OS / 権限不足は警告でスキップ）。
    - psutil を利用したクロスプラットフォーム実装。

- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を用いて監視テーブルの冪等な初期化を実行（Execution と Monitoring の両方で呼び出し）。

### Changed
- N/A（初回リリース）

### Fixed
- .env パースの強化
  - export KEY=val 形式、シングル／ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの扱いなどをサポートするよう改善。これにより複雑な値の .env 設定に耐性が向上。

### Security
- config_setup.py による .env 作成時に「.env を絶対に Git にコミットしないこと」をファイル内コメントで明記。
- Settings._require による必須環境変数未設定時の明確なエラー。設定不備の早期検出を促進。

### Documentation / Dev UX
- 各モジュールに docstring と利用手順（CLI の使い方、環境変数の説明など）を追加。起動スクリプト・ツールには usage コメントを付与。
- validate_config と config_setup により、導入時のセットアップ・検証フローを提供。

---

今後の予定（想定）
- factor_research の残りファクター実装とユニットテストの追加。
- ExecutionEngine / RiskManager / Broker クライアント周りの細部実装・結合テスト。
- ログの構造化（JSON）やメトリクス出力の追加、より高度な監視アラート機能の実装。

もし特定ファイルについてより詳細な変更点（関数・引数・挙動の差分）を出力したい場合は、対象ファイルを指定してください。