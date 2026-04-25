# Changelog

すべての重要な変更は「Keep a Changelog」仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-25

初回リリース。本バージョンで導入された主要機能・モジュールは以下の通りです。

### Added
- コアアプリケーションと起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、デーモンスレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）で安全停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中の PID ファイルを管理（data/execution.pid を想定、設定可能）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動用スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用の sqlite_path を使用して監視テーブルを管理。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - Settings クラスで環境変数をラップし、各種設定（DB パス、API トークン、監視閾値、環境モード判定など）を提供。
    - .env 自動読み込み機能を提供（プロジェクトルート判定に .git / pyproject.toml を使用）。.env.local は .env を上書き可能。
    - 環境変数の検証ロジック（値の妥当性チェック）やデフォルト値を埋め込んでいる。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等のペーパートレード／Kill Switch 関連設定を追加。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI。
    - 質問テンプレートとデフォルト値、シークレット項目マスク表示、保存確認を提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI（--strict オプションで警告を FAIL 扱いにできる）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が存在する場合）などを実施。
    - live 環境向けの追加ガード（LINE 通知設定や Kill Switch の自動クリア警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio パッケージを追加。
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順選定（同点タイブレークに signal_rank を使用）。
      - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分。全スコア 0 の場合は等分にフォールバックし WARNING を出力。
    - risk_adjustment.py
      - apply_sector_cap: 既存保有に基づくセクター集中制限（max_sector_pct）を適用し、上限超過セクターの新規候補を除外。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ。未知レジームはフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based/equal/score）に応じた発注株数計算。リスクベース計算、単元株丸め（lot_size）、max_position_pct / max_utilization による上限、aggregate cap に対するスケーリングと余り配分ロジックを実装。
    - これらは DB を参照しない純粋関数として設計され、単体テストしやすい。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング初期化ユーティリティ。
    - stdout への StreamHandler と 日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を定義し、ログディレクトリ作成失敗時はファイル出力をフォールバックで無効化（コンソールのみ）。
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度（nice / Windows priority class）を設定するユーティリティ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権や未対応 OS 時のフォールバック/警告を実装。
    - psutil に依存（適切にアクセス拒否等をハンドル）。

- 監視・モニタリング基盤
  - monitoring DB 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring の起動時に行い、監視テーブル存在を確保（冪等）。
  - SystemMonitor の単一チェック check_once() をポーリングループで呼び出し、例外は捕捉して次回ポーリングへ継続。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH）から各種指標を集計し、人間向けレポートを出力する CLI。
    - 集計内容: システム稼働率（system_status）、注文成功率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）等。
    - P95 計算、日付フィルタ（--from/--to）、PASS/FAIL 判定用しきい値（稼働率 99%、成功率 90% 等）を組み込み。

- リサーチ基盤（初期実装）
  - research/factor_research.py（ファクター計算モジュールの骨組み）
    - Momentum/Value/Volatility/Liquidity 等の因子計算を目指す設計（DuckDB 接続を受け、prices_daily / raw_financials を参照）。
    - モメンタム計算関数 calc_momentum の実装開始（設計定義と定数群を導入）。なおファイル終端が途中で切れているため未完の箇所あり。

- パッケージ初期化
  - __init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージを __all__ で公表。

### Changed
- ログ出力方針
  - コンソール出力は stdout を使用するよう統一（cron/Task Scheduler 等で stdout/stderr を一元化しやすくするため）。
- .env 自動読込の挙動
  - 環境変数の保護（OS 環境変数を protected として .env/.env.local の上書きを制御）を導入。
  - プロジェクトルート判定は .git または pyproject.toml を基準に探索するようにし、CWD に依存しない設計に変更。

### Fixed
- ロバストネス改善
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしても起動できるようにフォールバック処理を追加（警告出力して StreamHandler のみで継続）。
  - process_priority / cpu_affinity の呼び出しでアクセス権限不足や未対応環境が発生した場合に例外を吐かず警告ログでスキップするように改善。
  - .env パーサーの引用符内エスケープやインラインコメント対応を実装して .env の柔軟な記述に対応。

### Security
- API トークン等の取り扱い
  - config_setup にてシークレット項目をマスク表示。`.env` の生成時に「絶対に Git にコミットしないこと」を明記。

### Documentation / UX
- 対話ウィザード（config_setup）で既存 .env の読み込み・既存値の再利用をサポート。Enter でデフォルト/現状値を簡単に使える UX を実装。
- validate_config で検出した INFO/WARNING/ERROR を人間向けに出力し、--strict オプションで警告を失敗扱いにできる CLI UX を提供。
- paper_verification_report に対してコマンドラインオプション（--from/--to/--db）を提供。

---

注:
- この CHANGELOG は提供されたコード内容から推測して作成したものであり、実際のコミット履歴ではありません。将来的な変更や追加機能（例えば research/factor_research の未実装部分の完了、ExecutionEngine/ SystemMonitor の内部実装詳細、Broker クライアントの具象実装など）は別途リリースノートに反映してください。