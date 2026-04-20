# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

全般方針:
- バージョンはパッケージ内の __version__ に合わせています。
- 日付は本リリースの推定公開日です（コードベースの内容から推測）。

## [Unreleased]
リリース候補や開発中の変更はこちらに記載します。

## [0.1.0] - 2026-04-20
初回リリース（コードベースから推測した機能群をまとめたもの）。

### Added
- 基本アプリケーション情報
  - パッケージ初期バージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（環境に応じて MockBrokerClient を使用する想定）。
    - ExecutionEngine をデーモンスレッドで起動し、プロセス間フラグファイル（`data/stop_requested.flag`）で安全に停止できる仕組みを実装。
    - PID ファイル (`data/execution.pid` 等) によるプロセス管理をサポート。
    - RiskManager / OrderManager / Reconciler 等の依存コンポーネントを組み立てるロジックを追加。RiskConfig の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番向けの sqlite_path を使用する設計（監視データは本番 DB に貯める想定）。
    - 停止フラグファイルでループを終了する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを含む。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env の読み込みルール:
      - 優先度: OS 環境変数 > .env.local > .env
      - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
      - 読み込み時に既存 OS 環境変数を保護する仕組みあり（protected set）。
    - .env 行パーサ（クォート/エスケープ/インラインコメントの扱い、`export KEY=...` に対応）を実装。
    - Settings クラスを実装し、環境に依存する各種設定（J-Quants トークン、kabu API パスワード、DB パス、Paper Trading 設定、監視閾値、KABUSYS_ENV 検証等）をプロパティとして提供。
    - PAPER_FILL_MODE の入力検証（有効値: "instant","partial","never","reject"）を実装。
    - 各種閾値・パス（CPU/MEM/DISK の閾値、PID/KILL フラグパス等）を Settings で取得可能に。

- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 設定など主要な項目をウィザードで入力可能。
    - 既存 .env を読み込み、Secret 項目はマスク表示、確認後に .env を出力（.env を絶対に Git にコミットしない旨のヘッダを付与）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在/パース検証（PyYAML が無ければスキップ）等を実装。
    - `--strict` オプションにより警告も失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - 標準出力（stdout）向け StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30世代保持）をルートロガーに設定。
    - 既存ハンドラをクリアしてから再設定することで二重出力を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py
    - プロセス優先度設定および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX の差分を吸収（Windows: HIGH/NORMAL/IDLE クラス、POSIX: nice 値）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境では警告を出してスキップするフォールバックを実装。

- Portfolio（銘柄選定・配分・サイズ決定）
  - portfolio/portfolio_builder.py
    - select_candidates: Buy シグナルをスコア降順（同点は signal_rank 昇順）で最大 N 件抽出。
    - calc_equal_weights: 等分配重を計算（各銘柄 1/N）。
    - calc_score_weights: スコア正規化による配分（全スコアが 0 の場合は等分配にフォールバックし警告を出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を検出し、既存保有がセクター上限（デフォルト 30%）を超える場合に新規候補を除外するロジックを実装（unknown セクターは制限適用外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数（1.0/0.7/0.3）を提供。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各配分方式（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
    - risk_based: 許容リスク率・損切り率からベース株数を算出し単元株（lot_size）で丸め。
    - equal/score: 資産・重み・max_utilization・max_position_pct を考慮し株数を算出。
    - aggregate cap（全銘柄合計が available_cash を超えた場合）のスケーリングと、小口の補正アルゴリズム（端数の優先付け）を実装。
    - cost_buffer による保守的コスト見積もり、lot_size による丸め処理をサポート。
    - 価格欠損時の挙動をログ出力してスキップするように実装。

- 監視・検証ツール
  - monitoring モジュール初期化呼び出しを run_* スクリプトから行う（init_monitoring_db）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下数等を算出し PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms。
    - 日付フィルタ（--from, --to）や DB パス指定（--db）をサポート。
    - P95 計算のためのロジックと欠損データ処理を実装。

- research モジュール（着手）
  - research/factor_research.py
    - ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）の計画・一部実装の跡が存在（モメンタムに関する定義や定数を含む）。
    - DuckDB 接続を使用し prices_daily / raw_financials を参照する設計方針。

### Changed
- なし（初回リリースのため新規追加が主体）。

### Fixed
- なし（初回リリースのためバグ修正履歴なし。コード内に例外処理やフォールバック処理を多数実装しているため堅牢性を確保）。

### Notes / Migration
- .env 取り扱い:
  - 自動読み込み機能によりローカルの .env/.env.local がプロセス開始時に環境へ反映されます。テストなどで自動ロードを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - .env を絶対にリポジトリへコミットしないでください（config_setup が警告を出します）。
- Paper Trading と本番 DB は分離されています（paper_trading 環境では `PAPER_TRADING_SQLITE_PATH` を使用）。本番 DB (`SQLITE_PATH`) を Paper Trading で誤って上書きしないよう注意してください。
- 監視ループは停止フラグファイル `data/stop_requested.flag`（プロジェクトルート基準）を監視します。停止フラグを用いた制御フローに従ってください。
- ログはデフォルトで logs/ ディレクトリへ日次ローテーションで出力しますが、ディレクトリ作成に失敗した場合はコンソール出力のみになります。ログ出力先は環境変数 `LOG_DIR` または setup_logging の引数で変更可能です。
- システム権限や OS により process priority / CPU affinity の設定が失敗する場合があります（権限不足）。その場合は警告が出力されますが起動は継続されます。

### Security
- なし（秘匿情報（API トークン等）は .env に格納する想定。config_setup は secret 項目をマスクして扱う）。

---

（注）本 CHANGELOG は与えられたコードベースの内容から推測してまとめたものであり、実際のリリースノートは開発履歴やコミットログに基づいて作成してください。