# Changelog

すべての注記は Keep a Changelog の慣例に準拠します。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づいています。

## [Unreleased]

## [0.1.0] - 2026-04-20

### Added
- 初期リリース: 日本株自動売買システム「KabuSys」の基本機能群を追加。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定し、スレッドでエンジンを起動。停止フラグ（data/stop_requested.flag）や PID ファイルで制御。paper_trading モード時は専用の paper DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - execution パッケージ（OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine / BrokerClientFactory）を導入し、発注・リスク・突合せの基本フローを実装（設定可能な RiskConfig / EngineConfig を採用）。
  - 監視系
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを一元化。停止フラグでの終了、例外時のログ出力、KeyboardInterrupt の扱いを実装。
    - 監視 DB 初期化ユーティリティ init_monitoring_db を呼び出してテーブル存在を保証（冪等）。
  - 設定周り
    - config.py: 強化された .env 自動読み込みロジック（プロジェクトルート検出、.env/.env.local の読み込み順、OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）。.env パーサは export 構文・クォート文字列・バックスラッシュエスケープ・インラインコメント処理に対応。Settings クラスで多数の設定プロパティ（PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL のバリデーション、パス関連プロパティ等）を提供。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加（シークレットマスク、選択肢、書き出しテンプレートを提供）。
    - validate_config.py: 起動前検証 CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・DB パスの親ディレクトリ存在確認・config/*.yaml の存在/パース確認（PyYAML 任意）・本番環境向けのガード（LINE 通知設定や Kill Switch 設定）を実施。--strict オプションで警告も失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - kabusys.portfolio: 銘柄選定・重み計算・リスク調整・ポジションサイジングを実装。
      - portfolio_builder.py: select_candidates（スコア降順 + signal_rank タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
      - risk_adjustment.py: apply_sector_cap（セクター集中上限のチェックと候補除外）、calc_regime_multiplier（regime に応じた資金乗数: bull/neutral/bear、未知レジームはフォールバック）。
      - position_sizing.py: calc_position_sizes（allocation_method: risk_based / equal / score をサポート）、単元（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を利用した保守的見積り、残余キャッシュでの再配分ロジックを実装。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout への StreamHandler（cron/task 用に stdout を使用）と TimedRotatingFileHandler による日次ローテーション（30日保持）をルートロガーへ設定。既存ハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバックを実装。
    - utils/process_priority.py: cross-platform（Windows/Linux/macOS 等）でプロセス優先度と CPU affinity を設定するユーティリティを追加。アクセス権限や未サポート環境の例外をハンドル。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成するスクリプトを追加。稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）を計算し、閾値に基づく PASS/FAIL 判定を出力。日付フィルタと DB パス指定オプションをサポート。
  - 研究用モジュール（下書き）
    - research/factor_research.py: DuckDB を用いたファクター計算基盤（モメンタム等）の実装を開始。関数規約・定数群・calc_momentum の骨組みを追加（実装途中の箇所あり）。

### Changed
- ロギング出力を stdout に統一（StreamHandler） — cron/task からのリダイレクト運用を意識した設計変更。
- .env 読み込み順と上書きルールを明確化（OS 環境変数 > .env.local > .env）。.env.local は .env の上書き（override=True）として扱う。
- 監視機能は環境に依存せず常に sqlite_path（デフォルト data/monitoring.db）を使用する方針に統一（データの一元管理）。
- logging_setup: 既に設定済みのハンドラがある場合は一度 flush/close してから削除することで二重登録を防止。
- process_priority: Windows/Linux の差分を吸収するためにプラットフォーム固有定数を安全に解決して使用。

### Fixed / Robustness
- .env パーサの不正入力耐性を強化（export PREFIX、クォート、エスケープ、コメントを考慮）。
- run_monitoring/run_execution: 停止フラグ検知や例外発生時のログ出力を充実させ、DB 接続のクローズを finally で保証。
- init_monitoring_db を起動時に呼び出すことで監視テーブルの不存在によるクラッシュを防止（冪等に対応）。
- position_sizing の aggregate cap スケーリングで端数処理と残余配分を改善し、lot_size 単位で安定した再配分を行うようにした。
- process_priority と set_cpu_affinity は AccessDenied 等をハンドルしてログ警告でスキップするように。

### Known issues / Notes
- research/factor_research.calc_momentum の実装が途中（ファイル末尾で切れている）。ファクター計算の完全実装は今後の課題。
- 一部の機能（BrokerClientFactory の詳細実装や ExecutionEngine の内部の挙動）は本リリースでの統合テストが必要。
- PAPER_FILL_MODE の検証で無効な値は ValueError を発生させるため、運用環境での設定ミスに注意（config_setup で正しい選択肢を案内）。

---

その他、詳細な使い方・設定手順は以下の CLI/スクリプトを参照してください:
- python -m kabusys.config_setup  (.env 作成ウィザード)
- python -m kabusys.validate_config  (設定検証)
- python -m kabusys.run_execution  (ExecutionEngine 起動)
- python -m kabusys.run_monitoring (SystemMonitor 起動)
- python -m kabusys.tools.paper_verification_report (ペーパートレード検証レポート)

（変更内容はソースコードの実装から推測して記載しています。リリースノート作成時は実際のコミット履歴での確認を推奨します。）