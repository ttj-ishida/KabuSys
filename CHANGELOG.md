# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在の日付: 2026-04-18

## [Unreleased]

## [0.1.0] - 2026-04-18
最初の公開リリース。KabuSys の基本的な起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、および Paper Trading 検証ツールを実装しました。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に記録し、本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定する仕組みを導入。
    - 停止制御用のフラグファイル (data/stop_requested.flag) と PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知・KeyboardInterrupt による安全終了処理を実装。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
    - .env のパースはシングル/ダブルクォート、エスケープ、コメントを考慮した堅牢な実装。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 等）。
    - 設定値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を追加。
  - config_setup.py:
    - 対話式ウィザードで .env を初期生成・更新する CLI を実装。シークレット項目はマスク表示し、既存値の再利用やデフォルト選択をサポート。
    - .env 書き込みはテンプレート形式で出力。生成後の検証フローを案内。
  - validate_config.py:
    - .env と config/*.yaml の基本的な妥当性チェック CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、YAML ファイルの存在/パース検査（PyYAML がインストールされている場合）など。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て0 の場合はフォールバックで等金額配分）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株（lot）丸め、aggregate cap によるスケール調整、手数料/スリッページ想定（cost_buffer）を考慮。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、上限超過セクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通ロギング初期化関数 setup_logging を実装。StreamHandler を stdout に設定し、TimedRotatingFileHandler による日次ローテーション（30 日保持）をサポート。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリを引数 / 環境変数 / デフォルトの順で解決。
  - utils/process_priority.py:
    - set_process_priority / set_cpu_affinity を実装。Windows と POSIX 系（Linux / Darwin / FreeBSD）での差分を吸収し、psutil を使って nice 値やプロセス優先度を設定。権限不足等のケースは警告でスキップ。

- 監視用 DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を起動スクリプトから呼び出し、監視テーブルが存在することを保証（冪等）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを実装。SQLite（PAPER_TRADING_SQLITE_PATH）から集計して稼働率、注文成功率、送信率、API レイテンシ（P95 など）を出力。閾値に応じて PASS/FAIL を判定。
    - コマンドライン引数 --from / --to / --db をサポート。

- リサーチ（骨組み）
  - research/factor_research.py:
    - DuckDB を使ったファクター計算モジュールの骨組みを追加（モメンタム・移動平均・ATR・ボリューム系指標等の計算を想定）。（実装はモジュール内関数の雛形および定数が含まれる）

### Changed
- ロギング挙動の統一化:
  - すべての起動スクリプトから setup_logging を呼び出すことでログの出力先・フォーマットを統一。
  - コンソール出力は stdout を使用（cron/Task Scheduler での取り扱いを意識）。
- DB パスの扱い:
  - run_monitoring は環境変数 KABUSYS_ENV に関わらず監視用 sqlite_path（デフォルト: data/monitoring.db）を使用する明示的な挙動。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用してデータを本番 DB と分離。

### Fixed
- .env パーサの頑健化:
  - クォート内のバックスラッシュエスケープ、クォートなしの行内コメント処理、export プレフィックス対応など、実運用で見られる .env 形式に対応。
- 起動時のファイル/ディレクトリ不在ハンドリング:
  - logging_setup でログディレクトリ作成失敗時にファイル出力をスキップすることで起動失敗を回避。
  - validate_config による DB パス親ディレクトリ存在チェックで注意喚起メッセージを出力。

### Notes / Migration
- .env は絶対にリポジトリへコミットしないでください（config_setup の出力にも注意喚起あり）。
- 本番運用時は KABUSYS_ENV=live を設定する前に validate_config を実行し、LINE 通知設定等を含めて警告を確認してください。
- Paper Trading と本番データベースは意図的に分離されています。ペーパートレード検証時には PAPER_TRADING_SQLITE_PATH（またはデフォルト data/paper_trading.db）を使用してください。

---

参考: リポジトリ内の主要 CLI / スクリプト
- python -m kabusys.config_setup          — .env 対話式ウィザード
- python -m kabusys.validate_config      — 設定検証ツール
- python -m kabusys.run_execution        — Execution エンジン起動
- python -m kabusys.run_monitoring       — 監視 (SystemMonitor) 起動
- python -m kabusys.tools.paper_verification_report — Paper Trading 検証レポート

（今後のリリースでは factor_research の実装拡充、Strategy/Execution 実装の追加、単体テスト・CI 設定の導入を予定しています。）