# Changelog

すべての非重大な変更は semver の慣例に従って記載しています（初期リリース: 0.1.0）。

フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基本機能群を実装しました。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離する。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag による停止監視、data/execution.pid に PID を書き込む想定の処理フローを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）検知で優雅に終了する。

- 設定・環境関連
  - config.py
    - Settings クラスを導入し、環境変数から設定を取得する統一インターフェースを提供。
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。OS 環境変数は保護され、.env.local による上書きが可能。
    - 環境変数の必須チェック用ヘルパ（_require）、環境種別（development, paper_trading, live）やログレベルの検証実装。
    - Paper Trading 用の挙動制御（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
  - config_setup.py
    - .env を対話的に作成・更新するウィザードを追加。キー一覧、説明、シークレット入力、デフォルト、保存等をサポート。
  - validate_config.py
    - 起動前に .env および config/*.yaml の検証を行う CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスのディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）など多数の検証項目を実装。
    - 本番環境（KABUSYS_ENV=live）向けのガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を追加。

- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 標準化されたロギング設定を提供。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、保持 30 日）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows と POSIX 系を吸収して呼び出し側で OS を意識しなくてよい API を提供。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足や未対応 OS 時は警告を出してスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし、警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をサポートし、未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を実装（allocation_method="risk_based" / "equal" / "score" 対応）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、最大投資利用率（max_utilization）、手数料等のバッファ（cost_buffer）を考慮した aggregate cap スケーリングを実装。
    - スケールダウン時に端数（fractional remainder）に基づく優先配分ロジックを実装（再現性のため tie-breaker にコードを利用）。
    - 一部入力データ欠損時（価格未取得など）にスキップする実装。将来的に price フォールバックを検討する TODO を明記。

- モニタリング・ツール類
  - monitoring.monitoring_db.init_monitoring_db を利用して起動時に監視テーブルを冪等的に初期化するフローを各起動スクリプトに追加。
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを追加。期間指定 (--from/--to)、DB 指定 (--db) をサポート。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数などを計算し PASS/FAIL を判定する閾値（稼働率 99%、成立率 90% 等）を定義。
    - P95 の算出、latency 平均/最大、期間フィルタリング等を実装。DB 存在チェックやテーブル未存在（OperationalError）に対するフォールバックも実装。

- 研究用モジュール（初期）
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム、MA200乖離、ATR、流動性等）を設計。DuckDB の prices_daily / raw_financials テーブルを参照する前提で実装を開始（モジュール骨格と定数群、calc_momentum の docstring 等を含む）。

### 変更
- ログ出力について
  - ストリーム出力を stderr ではなく stdout を使用するように変更（cron / タスクスケジューラでのリダイレクト互換性向上）。
- .env 読み込みルール
  - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポートする堅牢な実装に更新。
  - 自動ロード順序は OS 環境変数（保護） > .env.local > .env。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを追加。

### 修正（注意点・安全策）
- run_monitoring の挙動
  - Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を参照する設計になっていることを明記（意図的な分離設計のため）。
- run_execution の安全措置
  - 起動前に停止フラグが既に存在する場合、エンジンの起動を行わず即時終了する保護を追加。
  - スレッド終了待機と停止フラグ検知による優雅シャットダウンを実装。
- process_priority の許容失敗
  - 権限不足・未対応環境では例外を送出せず警告ログを出して処理を継続する安全化を行った。

### ドキュメント補足 / TODO（既知の制約）
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨を TODO として記載。将来的に前日終値や取得原価でのフォールバックを検討。
- research/factor_research.py は一部実装が継続中（calc_momentum の実装開始がファイル末尾で切れている）。完全実装は今後のリリースで追加予定。
- PAPER_FILL_MODE の有効値制約と挙動は Settings にて厳密チェックを行うため、運用前に .env の設定を validate_config で確認することを推奨。

---

今後の予定（例）
- factor_research の完成とユニットテスト追加
- ExecutionEngine / SystemMonitor 周りの E2E テスト強化
- 銘柄別単元サイズや手数料モデルの拡張（stocks マスタ導入）
- レポートの HTML/CSV 出力対応

ご利用・フィードバック歓迎です。必要であればリリースノートの英語版や個別コンポーネントごとの詳細変更ログも作成します。