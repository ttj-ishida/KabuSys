CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
慣例: 追加 (Added), 変更 (Changed), 修正 (Fixed), 非推奨 (Deprecated), 削除 (Removed), セキュリティ (Security)。

[0.1.0] - 2026-04-18
--------------------

初期リリース — KabuSys のコア機能群を実装しました。本リリースはローカル開発・ペーパートレード・本番を想定した自動売買基盤の最小構成を提供します。

Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータレイヤーの基盤を追加。環境変数でパスを指定可能（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により実行環境に応じた Broker クライアント（Mock / 本物）を生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag を監視して安全に停止する仕組みを実装。
    - 実行用 PID ファイル（data/execution.pid）をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 常に本番用 sqlite_path を使用して監視テーブルを操作（環境にかかわらず）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
- 設定管理 / CLI
  - Settings クラス: 環境変数からアプリ設定を取得するユーティリティを追加（プロパティによる遅延評価）。
    - J-Quants / kabuAPI / LINE / DB / 監視閾値 等の設定をサポート。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実装（不正な値は ValueError）。
    - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）。
  - config_setup: .env 対話ウィザードを追加。
    - .env の読み書き、秘密入力のマスク、既存値の再利用、保存確認をサポート。
    - 出力テンプレートには .env を絶対に Git にコミットしない旨を明示。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml 存在チェック（PyYAML 未導入時はスキップ）、本番向けガード（LINE 通知設定や Kill フラグ挙動）を実装。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築 (pure functions)
  - portfolio.portfolio_builder:
    - シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア合計が 0 の場合に等分配へフォールバックする挙動を実装（警告ログ）。
  - portfolio.risk_adjustment:
    - セクター集中制限 apply_sector_cap を実装（既存保有比率が閾値を超えるセクターの新規候補除外）。
    - レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知は警告とフォールバック）。
  - portfolio.position_sizing:
    - allocation_method（risk_based / equal / score）に応じた株数計算を実装。単元（lot_size）に丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap のスケーリングを実装。
    - スリッページ・手数料を見越した cost_buffer による保守的見積りと、残差に基づく追加配分ロジックを実装。
- 監視 / 実行補助
  - utils.logging_setup:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェイルセーフを実装。
  - utils.process_priority:
    - プロセス優先度（high/normal/low）設定と CPU affinity 固定ユーティリティを追加。Windows と POSIX 系（Linux/Mac/FreeBSD）に対応し、権限不足等の例外は警告でスキップ。
- Paper Trading 検証
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力する CLI を追加。
    - P95 計算、閾値による PASS/FAIL 判定ロジックを実装（稼働率 99% 等のデフォルト閾値を定義）。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究用スケルトン
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクター計算を行うためのモジュール骨格を追加（モジュールの一部は未完）。
- その他
  - monitoring.monitoring_db による監視用テーブル初期化呼び出し（init_monitoring_db）を実行スクリプトで使用。
  - execution 側に RiskManager / Reconciler / OrderManager / OrderRepository の組み立て例を追加（RiskConfig のデフォルト値含む）。

Changed
- ロギング
  - コンソール出力を stderr ではなく stdout に変更（cron やスケジューラで stdout/stderr を一元管理しやすくするため）。
- 設定自動読み込み
  - .env の自動ロード順序を OS 環境 > .env.local > .env として、OS 環境変数は保護（上書き禁止）する動作を実装。

Fixed
- 環境変数パースの堅牢化
  - .env 読み込みで export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメントの扱いに対応。
  - MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）が指定された場合にデフォルトにフォールバックして warning を出力するように修正。
- プロセス優先度設定の安全化
  - 権限不足や未サポート環境での例外をキャッチして警告ログに落とすことでクラッシュを防止。

Security
- シークレット取り扱い
  - config_setup にてシークレット項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE_CHANNEL_ACCESS_TOKEN）は入力時にマスク表示をするように配慮。
  - .env を絶対に Git にコミットしない旨を明記。

Known issues / Limitations
- research.factor_research モジュールが途中で切れている（calc_momentum の実装継続が必要）。まだ完全実装ではありません。
- portfolio.position_sizing の price 欠損時の扱いについて TODO コメントあり（価格が欠損するとエクスポージャーが過小評価される可能性）。将来的に前日終値等のフォールバックを実装予定。
- 一部のファイルハンドラ作成・ディレクトリ作成で失敗した場合はファイル出力を無効化するフェイルセーフを入れているが、ログ出力の永続性が保証されない場合がある。
- 本番運用に際しては validate_config のチェック内容を必ず確認し、KABUSYS_ENV=live のガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の設定等）を遵守してください。

Acknowledgements / Notes
- 本リリースはローカル開発およびペーパートレードから本番移行までのワークフローを念頭に設計されています。今後のリリースでは research モジュールの完成、テスト強化、外部サービス連携の拡張（例: ブローカー固有の拡張）を予定しています。