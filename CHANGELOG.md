# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式で記載します。言語は日本語です。

フォーマット:
- Unreleased: 今後の変更（現状なし）
- 各リリースはバージョンと日付（YYYY-MM-DD）を表記
- セクションは Added / Changed / Fixed / Removed / Security 等

なお、以下の変更点はリポジトリ内のソースコードから機能追加・挙動を推測してまとめたものです。

## [Unreleased]
（該当なし）

## [0.1.0] - 2026-04-19
初回公開リリース。主要な機能追加とユーティリティをまとめて含みます。

### Added
- 実行エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の MockBrokerClient を使用可能（paper_trading 時は専用 SQLite を使用して本番 DB と分離）。
    - 実行中の停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全な起動・停止フローを実装。
    - プロセス優先度を起動時に High に設定する処理を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視用 DB 接続は環境に依らず本番 sqlite_path を使用する設計。
    - 停止フラグファイルでループを安全に終了。

- 設定 / 環境管理
  - config.py
    - Settings クラスを導入し、環境変数経由で各種設定（J-Quants トークン、kabu API パスワード、DB パス、環境種別 等）を集中管理。
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env ロードは .env → .env.local の順で読み込み、OS 環境変数を保護する仕組みを採用（override/protected）。
    - PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE など paper_trading 向け設定を提供。
  - config_setup.py
    - 対話式ウィザードにより .env を生成 / 更新する機能を追加。
    - シークレット入力のマスク、選択肢・デフォルト値の提示、保存前の確認をサポート。
  - validate_config.py
    - 起動前に .env や config/*.yaml の設定不備を検出する CLI。
    - --strict オプションを用意（警告を FAIL 扱いにできる）。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML がある場合）等を実行。

- ポートフォリオ構築ライブラリ（pure functions）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルのソートと上位選出。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分関数。全スコアが 0 の場合は等分にフォールバックし警告。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限を適用するフィルタリング関数（売却予定銘柄の除外対応、"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear を扱う、未知レジームはフォールバックして警告）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株丸め、aggregate cap によるスケールダウン・端数処理（lot_size 単位での再配分）を実装。

- ログ/プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。
    - stdout に出力する StreamHandler（stdout 使用）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
    - LOG_LEVEL / LOG_DIR / app_name による設定をサポート。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX（Linux/macOS 等）を吸収してプロセスの優先度を設定。
    - set_cpu_affinity(cpu_count) によりカレントプロセスを最初の N コアに固定する補助関数を追加。
    - 権限が無い場合は警告を出して安全にスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から期間指定で統計を集計し、PASS/FAIL 判定を行う CLI レポートを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数 等。閾値はスクリプト上で定義（例: uptime >= 99%、fill_rate >= 90% 等）。
    - P95 計算、SQL 日付フィルタ組立、欠損テーブルへの耐性（OperationalError を捕捉して N/A 表示）を実装。

- リサーチ（ファクター算出）骨格
  - research/factor_research.py
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて Momentum / Value / Volatility / Liquidity 系ファクターを算出する設計方針と初期的定数を追加（関数 calc_momentum が途中まで実装済みの様子）。

### Changed
- ロギング設計の改善
  - コンソール出力は stderr ではなく stdout を使用するように変更（cron/Task Scheduler 等でのリダイレクト運用を意識）。
  - 既存ハンドラの重複登録を避けるため、setup_logging はルートハンドラを一度 flush/close してから再設定する。

- .env の読み込みポリシー
  - OS 環境変数を保護するため .env の上書きを制御（.env.local を override=True で読み込むが OS 環境変数は protected）。自動読み込みはプロジェクトルートを基準に行われる（CWD 非依存）。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line において、クォート文字内のバックスラッシュエスケープやインラインコメント処理、export プレフィックス対応など、より現実的な .env 行のパースに対応。これにより .env の読み込みで誤った分割やコメント判定が軽減。

### Security
- シークレット管理配慮
  - config_setup の対話入力ではシークレット項目をマスクして表示。README 等への注意喚起として .env を絶対に Git にコミットしない旨を .env ヘッダに記載。

### Removed
- （該当なし）

---

注記:
- 上記はリポジトリ内の Python ファイルから推測した変更点のまとめです。実際のコミット履歴や過去バージョンとの差分があれば、より正確な CHANGELOG を作成できます。必要であれば、git log / diff を与えていただければ追記・修正します。