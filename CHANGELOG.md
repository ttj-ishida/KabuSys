# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初版リリース。モジュール群（実行エンジン、監視、ポートフォリオ構築、ユーティリティ、CLI ツール等）を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 起動スクリプト / 実行・監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント抽象化に対応。
    - ExecutionEngine をスレッドでデーモン起動し、data/stop_requested.flag により外部から停止要求を受け付ける。起動時に stop フラグが立っている場合は起動を行わない。
    - 実行用 PID ファイルをサポート（data/execution.pid、設定経由でパス指定可能）。
  - 監視（SystemMonitor）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用する旨を明示。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt による終了処理を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出し。

- 設定・環境
  - 環境設定管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env パース機能は `export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
    - 各種設定プロパティ（DB パス、API トークン、モード判定フラグ、監視しきい値等）を提供。`paper_fill_mode` の検証や `KABUSYS_ENV` / `LOG_LEVEL` 等のバリデーションを実装。
    - settings オブジェクトをエクスポート。

  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を新規作成・更新するウィザード。デフォルト値・選択肢・シークレット入力に対応。
    - 生成された .env のテンプレートフォーマットを定義して書き込み。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の整合性チェック、DB パスや config/*.yaml の存在／パース検証（PyYAML がインストールされていない場合はスキップして注意喚起）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティ。
    - ログディレクトリ自動作成。作成失敗時はファイル出力をスキップしてコンソールログのみで継続。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）やログディレクトリ解決順を明示。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX 系 OS（Linux/Mac/FreeBSD）に対応した優先度設定を吸収。
    - `set_process_priority(level)` で "high" / "normal" / "low" を設定。権限不足や未対応環境では警告出力してスキップ。
    - `set_cpu_affinity(cpu_count)` で最初の N コアに固定する機能（未指定は全コア使用）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み算出を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - signal のソート・上位選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み付け（calc_score_weights、全スコア 0 の場合は等配分にフォールバック）。
  - セクター制約・レジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター集中制限（apply_sector_cap）。売却予定銘柄を除外して既存セクターエクスポージャを計算し、上限超過セクターの候補を除外。
    - レジームに基づいた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear に対応、未知レジームは警告を出して 1.0 をフォールバック。
  - 発注株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）。
    - 複数の割当方式をサポート: "risk_based", "equal", "score"。
    - 損切り率・リスク許容率に基づく risk_based の計算、銘柄ごとの上限（max_position_pct）や単元株（lot_size）で丸め処理。
    - 全体投資額が利用可能現金を超える場合のスケーリング処理と、スケール後の残余を fraction（端数）に基づいて lot 単位で再配分するアルゴリズムを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる機能を追加。
  - モジュールエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター
  - ファクター計算のための基盤モジュール（src/kabusys/research/factor_research.py）を追加（モジュールの先頭まで実装。モーメンタム等の計算実装を開始）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを想定した計算方針を仕様書コメントとして記載。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出してレポート出力。
    - P95 計算、期間フィルタ、スレショルドによる PASS/FAIL 判定を実装。
    - DB パスは引数 `--db` > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト の優先順位で解決。

### Changed
- DB 初期化
  - 監視用テーブルの初期化ロジックを idempotent に保証するため init_monitoring_db(sqlite_conn) を起動時に呼び出す（run_monitoring, run_execution）。これにより監視テーブルが存在しない場合に自動作成され、既存時は問題なくスキップされる。

- ロギング挙動
  - StreamHandler を stdout に向けるように変更（cron / Task Scheduler 等でのリダイレクト運用を考慮）。
  - 既存ハンドラがある場合は一度 flush/close してから再設定し、二重設定を防止。

- .env パース仕様の強化
  - export プレフィックス対応、クォート有無の厳密なパース、バックスラッシュエスケープ、インラインコメントの扱いなどを追加。より現実的な .env ファイルのフォーマットをサポート。

- process_priority
  - Windows の優先度定数、POSIX の nice 値の取り扱いを抽象化し、呼び出し側が OS を意識しないインターフェースに統一。

### Fixed
- 環境変数のバリデーション強化
  - `Settings.paper_fill_mode` に対して有効値チェックを実装し、不正値で ValueError を送出することで誤設定を早期検出。
  - `Settings.env` / `Settings.log_level` の不正値時に明確なエラーを出すように。

- 監視ループの堅牢性向上
  - monitor.check_once() 内で例外が発生しても監視ループ全体が停止しないよう、例外キャッチとログ出力を追加（run_monitoring.py）。
  - 不正な MONITOR_POLL_INTERVAL 値に対して警告を出し、デフォルト値にフォールバックする実装で time.sleep に渡す不正値によるクラッシュを回避。

### Notes / Known limitations
- research.factor_research.py は仕様・設計ポイントと一部の実装（定数・関数ヘッダ）を含むが、完全実装は継続中。
- position_sizing の価格が欠損（0.0）の場合は現在はスキップする実装。将来的に前日終値や取得原価等のフォールバック価格採用を検討している（TODO コメントあり）。
- ログディレクトリ作成やプロセス優先度の設定は権限不足等で失敗するケースがあるが、その場合は警告を出して処理を継続する（フェイルセーフ設計）。

--- 

今後の予定:
- factor_research の完全実装、ユニットテスト追加、config/*.yaml のテンプレート生成スクリプト整備、ドキュメント（README / Usage）拡充を予定しています。