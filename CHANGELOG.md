CHANGELOG
=========

すべての変更は「Keep a Changelog」標準に準拠して記述しています。
問い合わせ・補足説明が必要な場合はお知らせください。

0.1.0 - 2026-04-21
-----------------

Added
- 初回リリース: KabuSys 基本機能を実装。
- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて
    paper_trading モードでは専用の MockBrokerClient と data/paper_trading.db を使用し、
    本番 DB と分離して動作する。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL
    環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルの検出で
    安全にループを終了する。
- 設定・環境
  - config.py: 環境変数/​.env 自動ロードと Settings クラスを実装。プロジェクトルート検出ロジックにより
    .env/.env.local を自動読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - config_setup: 対話式 .env 作成ウィザードを追加（複数の設定項目、シークレットマスク、保存機能）。
  - validate_config: 起動前チェック CLI を追加し、必須環境変数や config/*.yaml、パス存在確認、本番向けガードを検証可能。
- ポートフォリオ構築（純粋関数群、DB非依存）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、
    スコア加重（calc_score_weights）を実装。
  - portfolio.position_sizing: 株数決定ロジック（risk_based / equal / score 対応）、単元（lot_size）丸め、
    aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）対応を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジームに応じた乗数（calc_regime_multiplier）を実装。
- ユーティリティ
  - utils.logging_setup: 統一ロギング設定を提供。StreamHandler（stdout）と日次ローテーションファイルハンドラを設定、
    ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils.process_priority: Windows/Linux/macOS を吸収するプロセス優先度設定（set_process_priority）、
    CPU affinity 設定ユーティリティ（set_cpu_affinity）を実装。権限不足などは警告でフォールバック。
- 監視・実行の耐障害性
  - run_execution / run_monitoring で PID ファイル・停止フラグの扱いを実装し、安全な起動停止制御を提供。
  - init_monitoring_db 呼び出しにより監視用テーブルの冪等初期化を保証（監視テーブルが存在することを担保）。
- Paper Trading 検証レポート
  - tools.paper_verification_report: ペーパートレード DB（デフォルト data/paper_trading.db）から各種指標を集計して
    レポートを標準出力に出力。指標: 稼働率、注文成功率、送信率、P95レイテンシ 等。閾値（稼働率 99%、成功率 90% 等）付き。

Changed
- ログ出力の統一
  - 全起動スクリプトから setup_logging(app_name=...) を呼び出す想定で、ログファイル名が app_name ベースになるよう統一。
  - コンソール出力は stderr ではなく stdout を使用（Task Scheduler / cron とのリダイレクト運用を想定）。
- 環境変数読み込みの挙動
  - .env のパース処理を堅牢化（export プレフィクスの対応、クォート内のバックスラッシュエスケープ処理、コメント処理の改善）。
  - .env.local を .env の上書きとして扱う（ただし OS 環境変数は保護）。
- Settings の検証とデフォルト
  - Settings.env の許容値を "development" / "paper_trading" / "live" に限定し、不正値は ValueError を送出。
  - PAPER_FILL_MODE に対するバリデーションを追加（instant/partial/never/reject のみ有効）。
  - SQLite / DuckDB / PID ファイル等のデフォルトパスを明示化。
- position_sizing のアルゴリズム調整
  - risk_based と equal/score の両方式をサポート。単元丸め（lot_size）や max_position_pct、max_utilization、
    cost_buffer を取り入れて保守的な計算を実施。
  - aggregate cap 超過時のスケーリングは、小数端数の扱い（lot_unit 単位での再配分）を行い、再現性を確保するためソート安定化を導入。

Fixed
- ログディレクトリ作成失敗時の挙動を修正: 失敗してもプロセスが停止せず、コンソール出力のみで継続するように変更。
- run_execution / run_monitoring の例外ハンドリングを強化し、チェック中の例外時にループを継続して次ポーリングへ移行するようにした。
- .env 読み込みで OS 環境変数を上書きしてしまう可能性を排除（protected set により保護）。

Security
- シークレット系設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は
  config_setup の対話でマスク表示するようにし、.env を誤ってコミットしないよう注意喚起ヘッダを追加。

Known Issues / Notes
- 一部の操作（プロセス優先度設定、CPU affinity 設定）は権限やプラットフォームによって失敗する可能性があります。
  失敗時はログに警告が出力され、フォールバックする設計です。
- portfolio.position_sizing は価格欠損（price が 0/None）の場合に一部計算がスキップされます。
  将来的に前日終値や取得原価などのフォールバック価格を追加する予定です（TODO コメントあり）。
- validate_config は PyYAML が未インストールの場合、YAML のパース検証をスキップします（警告表示）。

参考: 今後の予定（未実装・検討中）
- 銘柄別 lot_size のサポート（stocks マスタからの取得）
- position_sizing のさらなる単体テスト追加と境界条件の硬化
- DuckDB を用いたファクター計算（research パッケージ）の完了・最適化
- CI での設定検証・静的解析の導入

--- 
（本 CHANGELOG は、提示されたコードベースの内容から推測して作成しています。実際の開発履歴やコミット単位の記録とは異なる場合があります）