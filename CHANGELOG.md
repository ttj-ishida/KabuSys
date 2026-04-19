# Changelog

すべての変更は Keep a Changelog 形式に準拠しています。  
日付はこのリリース作成日（2026-04-19）です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初期リリース番号を設定: `kabusys.__version__ = "0.1.0"` を導入。
  - パッケージ構成に以下の主要コンポーネントを追加:
    - 実行系（execution）
    - 監視系（monitoring）
    - ポートフォリオ構築（portfolio）
    - ユーティリティ（utils）
    - 設定管理（config）
    - 開発支援ツール（tools, research）

- 起動スクリプト
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。停止はプロジェクトの `data/stop_requested.flag` ファイルで行う。
    - Monitoring は環境（KABUSYS_ENV）に関係なく本番用 `sqlite_path` を使用して DB に接続する。
    - duckdb 連携を備え、例外発生時はログを残して次ポーリングに進む耐障害性を備える。

  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）で本番 DB と分離して動作。
    - 起動時にプロセス優先度を "high" に設定。
    - Broker クライアントのファクトリ（BrokerClientFactory）経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine を開始。
    - 停止は `data/stop_requested.flag` 検出で行い、PID ファイル (`data/execution.pid`) をサポート。

- 設定管理
  - config.py:
    - 環境変数の読み込み・管理用 Settings クラスを追加。
    - `.env` 自動ロード機能をプロジェクトルート（.git または pyproject.toml）から行う（無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` あり）。
    - `.env` の読み込みは OS 環境変数を保護（protected）する方式で `.env` → `.env.local` の順に読み込み（`.env.local` は override）。
    - `.env` のパースロジックが拡張され、`export KEY=val`、シングル/ダブルクォート、エスケープ文字、インラインコメント扱いなどに対応。
    - 多数の設定プロパティを実装（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `paper_fill_mode`, `pid_file_path`, 各種閾値、`env`/ログレベル判定等）。
    - 環境値のバリデーションを行い、不正な値は例外を投げる。

  - config_setup.py:
    - 対話式 .env 作成 / 更新ウィザードを追加（CLI: `python -m kabusys.config_setup`）。
    - 必要項目（J-Quants トークン、kabu API パスワード等）やオプション項目の入力補助、既存 .env 読み込み、シークレットマスク表示、保存機能を提供。
    - 書き込み時のテンプレート（.env ファイルフォーマット）を用意。

  - validate_config.py:
    - 起動前に環境変数と config/*.yaml を検証する CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML ファイルの存在・パース検証、live 環境向けの追加ガード等を実装。
    - `--strict` オプションで警告も失敗（exit 1）として扱う。

- ユーティリティ
  - utils/logging_setup.py:
    - アプリケーション共通のログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定（ログディレクトリ作成失敗時はファイル出力をスキップ）。
    - `LOG_LEVEL`, `LOG_DIR`, 引数 `level`/`log_dir` による解決ロジックを実装。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level: "high"|"normal"|"low")` を提供し、psutil を利用して Windows の優先度クラスまたは POSIX の nice 値にマップ。
    - `set_cpu_affinity(cpu_count: Optional[int])` を提供。
    - 権限不足や未対応 OS では警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定と重み計算:
      - select_candidates: BUY シグナルをスコア降順にソートして上位 N を返す（同点は signal_rank でタイブレーク）。
      - calc_equal_weights: 等金額配分（1/N）を返す。
      - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等分配へフォールバックして警告を出す。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクター集中を制限するフィルタ。既存保有（当日売却予定は除外）に基づき、セクターの時価が上限を超える場合にそのセクターの新規候補を除外する（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に基づく資金乗数を返す。未知レジームは警告を出して 1.0 でフォールバック。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を計算するロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - risk_based: 損切り幅とリスク許容率に基づいて株数を算出。
      - equal/score: 重みと価格に基づいて目標株数を計算。
      - lot_size（単元）で丸め処理、1 銘柄上限・aggregate cap（利用可能現金）を考慮したスケーリング、cost_buffer（手数料・スリッページ見積）対応、残差分の公平配分ロジックを提供。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 向け検証レポートを生成する CLI を追加（`python -m kabusys.tools.paper_verification_report`）。
    - デフォルト DB は `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` / `--db` で上書き可）。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均/最大/P95）等を集計して出力。
    - 合格基準（閾値）を設定:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - データ不足やテーブル未存在時の耐性（sqlite3.OperationalError を捕捉して N/A 扱い）を持つ。

- リサーチ（作業中）
  - research/factor_research.py:
    - ファクター計算モジュール（モメンタム、ボラティリティ、バリュー、流動性等）を追加。DuckDB を用いて prices_daily / raw_financials を参照して計算する設計。
    - ファイルは途中で切れている（calc_momentum の実装が途中）ため、作業継続中（WIP）。

### Changed
- なし（初期リリースのため新規追加中心）

### Fixed
- なし（初期リリース）

### Notes / Implementation details
- `.env` 自動読み込みはプロジェクトルートが特定できない場合はスキップされる（配布後やテスト時の柔軟性確保）。
- 設定パースは POSIX シェル風の .env をかなり忠実に扱うよう拡張しており、引用符中のエスケープ等をサポートする。
- ログ出力は stdout をメインに使い、ファイル出力が利用可能なら日次ローテーションを行う。ログディレクトリ作成失敗時にもコンソールログのみで動作を継続する。
- プロセス優先度設定は権限がない場合や未対応 OS では安全にスキップする実装になっている。
- ExecutionEngine の RiskManager 初期設定には broker.get_available_cash() に基づく initial_portfolio_value を使用（実稼働前に現金額を参照して設定）。
- 監視ループと実行エンジンの停止制御は `data/stop_requested.flag` によるファイルベースの Kill Switch を利用（config でパス変更可）。

### Known issues / TODO
- research/factor_research.py の calc_momentum 等は未完（ファイル末尾で途切れている）。ファクター計算の完全実装は今後のタスク。
- position_sizing の価格欠損（price が 0.0 の場合）の扱いに関する注記（TODO）が残っている。将来的に前日終値等のフォールバックを検討する必要あり。
- 一部の外部依存（psutil, duckdb, PyYAML 等）がインストールされていない場合、該当機能は警告を出してスキップする設計になっているが、実稼働前に依存関係の確認・インストールが必要。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や開発ノートに基づく補足・修正がある場合は、反映してください。