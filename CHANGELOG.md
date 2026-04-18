Keep a Changelog
=================

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし（新規リリース時に記載してください）

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーションと CLI を実装
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成（MockBrokerClient 等）。
    - ExecutionEngine をデーモンスレッドで起動し、data/stop_requested.flag の検出で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用テーブルの存在を保障するため init_monitoring_db を呼び出す。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番用の sqlite_path（Settings.sqlite_path）を使用。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定 / 環境管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートに .git または pyproject.toml がある場合に有効）。
    - `.env` と `.env.local` の読み込み優先順位（OS 環境変数 > .env.local > .env）。OS 環境変数を保護（上書き不可）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パースは `export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント等に配慮。
    - Settings クラスで各種設定値（トークン、API ベース URL、DB パス、監視しきい値、環境判定など）をプロパティとして提供。入力値検証あり（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI。
    - シークレット項目は表示をマスク、既存値の読み込み・再利用に対応。
- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本チェックを行う CLI。
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML 未インストール時は警告でスキップ）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/<app_name>.log、日次ローテーション、30 日分保持）を設定するユーティリティ。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使用することでタスクスケジューラや cron での挙動を想定。
  - utils/process_priority.py
    - psutil を用いてプラットフォーム差を吸収しつつプロセス優先度（high/normal/low）や CPU affinity を設定するユーティリティ。
    - Windows / POSIX（Linux, Darwin, FreeBSD）それぞれに対するデフォルト値を用意し、権限不足等で失敗した場合は警告を出してスキップする安全設計。
- Portfolio 建設ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク）。
    - 等配分・スコア加重（calc_equal_weights, calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap: 既存保有比率が上限を超えるセクターの新規候補を除外、"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier: bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - position size の計算（risk_based / equal / score）。risk_based の場合は risk_pct, stop_loss_pct を用いた計算式。
    - 単元株（lot_size、デフォルト 100）による丸め処理、1 銘柄上限（max_position_pct）、投下合計上限（max_utilization / available_cash）を考慮。
    - コストバッファ（cost_buffer）を考慮した保守的なコスト見積りと、投資合計が available_cash を超えた場合のスケーリング処理（小数部分の残差を用いた lot 単位での追加配分ロジックを含む）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）からデータを集計して検証レポートを標準出力に出すツール。
    - オプション: --from, --to（YYYY-MM-DD）、--db（データベースパス）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）。
    - しきい値を定義して PASS/FAIL 判定を行う（例: 稼働率 >= 99%、fill >= 90% 等）。
- Research（ファクター計算）
  - research/factor_research.py
    - モメンタム等のファクター計算の骨子を実装（duckdb 接続を受けて prices_daily / raw_financials を参照する設計）。
    - ファクター一覧・設計方針・定数（1M/3M/6M リターン、MA200 乖離、ATR 等）を定義。モメンタム計算関数の実装を開始（未完の箇所あり）。

Changed
- なし（初回リリース相当）

Fixed
- なし（初回リリース相当）

Notes / Important details
- 環境変数と既定値
  - 自動ロード: .env / .env.local をプロジェクトルートから読み込む（但し OS 環境変数が優先され上書きは保護される）。
  - 主要な環境変数とデフォルト:
    - KABUSYS_ENV: default "development"（有効値: development, paper_trading, live）
    - LOG_LEVEL: default "INFO"
    - DUCKDB_PATH: default "data/kabusys.duckdb"
    - SQLITE_PATH: default "data/monitoring.db"
    - PAPER_TRADING_SQLITE_PATH: default "data/paper_trading.db"
    - MONITOR_POLL_INTERVAL: default 60（run_monitoring 用）
    - PAPER_FILL_MODE: default "instant"（valid: instant, partial, never, reject）
  - 設定値が不正な場合は ValueError または警告で通知する実装が多く含まれる（Settings のプロパティ等）。
- ロギング
  - stdout に出力することで外部のログ集約やジョブスケジューラとの連携を考慮。
  - ログファイルはデフォルト logs/ 以下で日次ローテーション、30 日分保持。
- プロセス管理
  - 起動スクリプトは起動直後にプロセス優先度を "high" に設定しようと試みるが、権限不足等で失敗した場合は警告を出して継続。
- 停止フラグ / PID ファイル
  - data/stop_requested.flag といったフラグファイルを用いた外部制御に対応。
  - 実行エンジンは PID ファイルパスを受け取っている（settings.pid_file_path / data/execution.pid 等）。
- Paper Trading と本番の DB 分離
  - run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を使い分ける（本番 DB とデータ分離）。
  - 監視（run_monitoring）は明示的に本番の sqlite_path を参照する設計（環境に左右されない監視）。

Known limitations / TODO
- research/factor_research.py の実装は途中（モメンタム計算関数の途中でファイルが終わっている）。
- position_sizing の price フォールバック処理（価格欠損時の補完）等、幾つかの TODO コメントあり。
- stocks 毎の lot_size を持つ拡張（銘柄別単元対応）は未実装（コメントで言及）。

Security
- .env は絶対に Git にコミットしない旨を config_setup のヘッダで注意喚起。

ライセンスや貢献方法などのメタ情報は別途 README 等で管理してください。