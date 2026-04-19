# CHANGELOG

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠します。  

注: この CHANGELOG はコードベース（src/ 以下）の現状から推測して作成した初期リリース向けの要約です。

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を監視して安全に停止。実行中は PID を data/execution.pid に記録。
    - スレッドで engine.run_session を実行し、停止フラグ検知時は engine.stop() を呼び出してシャットダウンする。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す実装。
    - 監視は環境にかかわらず本番の sqlite_path を使用する挙動を明示。
    - 停止フラグ (data/stop_requested.flag) によりポーリングループを停止。KeyboardInterrupt にも対応。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / 環境読み込み
  - config.py
    - Settings クラスを導入し、環境変数経由の設定取得を統一。
    - 自動 .env ロード機能:
      - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env, .env.local を自動読み込み（環境による上書き制御あり）。
      - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DuckDB / SQLite パス、paper trading の挙動、監視閾値、環境種別判定等）。
    - PAPER_FILL_MODE の検証（有効値: "instant" | "partial" | "never" | "reject"）および紙トレード DB パス（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 環境種別（KABUSYS_ENV）の検証（development / paper_trading / live）。
    - ログレベル（LOG_LEVEL）の検証。

  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 通知設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）と保存機能を提供。
    - .env を書き出す際に重要な注意（.env を Git にコミットしないこと）を明示。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、LOG_LEVEL の検証、DB パスの存在チェック（親ディレクトリ有無警告）、config/*.yaml の存在およびパース検査（PyYAML がある場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - `--strict` オプション: 警告も失敗扱いにして exit(1) を返す。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ（LOG_DIR 環境変数またはデフォルト logs/）を自動作成。作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラはクリアして二重設定を防止。
    - stdout を使用する理由を明記（単一ストリームでのリダイレクト対応）。

  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - psutil を利用して Windows と POSIX 系（Linux, Darwin, FreeBSD）で移植性を担保。アクセス拒否や未実装時は警告を出してスキップ。
    - set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を提供。
    - 未対応 OS は警告を出してスキップ。

- Execution 周辺コンポーネント（骨子）
  - execution 以下のファクトリ・エンジン・オーダーマネージャ・リポジトリ・リコンシリエータ・リスクマネージャ（参照実装を想定）を組み立てる起動ロジックを run_execution で実装（実際の各クラスは別ファイル参照）。
  - RiskConfig によるデフォルトリスクパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を適用。初期ポートフォリオ値は broker.get_available_cash() を参照して決定。

- 監視（Monitoring）
  - monitoring 初期化（monitoring_db.init_monitoring_db を呼び出し監視テーブル存在を保証）。
  - SystemMonitor を使用して定期チェックを行う（duckdb も接続）。

- Portfolio ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（score 降順、同点は signal_rank 昇順のタイブレーク）。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア比率。全スコア 0 の場合は等金額にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合は同セクターの新規候補を除外。unknown セクターは除外対象外）。
    - レジーム乗数 calc_regime_multiplier（"bull":1.0, "neutral":0.7, "bear":0.3、未知は 1.0 にフォールバックして警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 銘柄ごとの発注株数を計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合はスケールダウン＋残差で追加配分）を実装。
    - cost_buffer による保守的見積り（手数料・スリッページ反映）をサポート。
    - 不足データ（価格欠損等）時はログを出してスキップ。
    - TODO / 注意点: price 欠損時のフォールバック（前日終値等）の検討がコメントとして残る。

  - portfolio/__init__.py で主要 API をエクスポート。

- 解析・研究ツール
  - research/factor_research.py（骨子）
    - DuckDB 接続を使った定量ファクター計算モジュール（Momentum, Value, Volatility, Liquidity を想定）。
    - モメンタム計算（calc_momentum）の設計が含まれる（1M/3M/6M リターン、200日移動平均乖離など）。関数は (date, code) をキーとする dict を返す設計。
    - 設計方針と定数（窓幅等: 21,63,126,200 等）を定義。
    - （注）ファイル末尾で実装が途中で切れているため、完全実装は今後必要。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - デフォルト DB パスは data/paper_trading.db。コマンドライン引数で --db を指定可能。
    - システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出してレポート表示。
    - 判定基準（閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率（fill） >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 の計算、日付フィルタ（ISO8601 UTC 文字列変換）対応、テーブルが存在しない場合の安全ハンドリングを実装。

### Changed
- （初回リリース）パッケージとしての初期構成・API 設計を確定。

### Fixed
- N/A（初回リリースのため既知の修正履歴はありません）。

### Notes / Known issues / TODO
- research/factor_research.py は設計と一部実装が含まれますが、ファイル末尾で実装が途中で切れている（"start_da" で途切れている）ため、完全な計算ロジックの追加実装が必要です。
- portfolio/position_sizing.py の注記: price が欠損（0.0）の場合にエクスポージャー等を過少に見積もる可能性があり、将来的に前日終値等のフォールバックを実装することが望ましい。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続する設計だが、運用時にログ出力先の権限やディスク容量を事前に確認することを推奨。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性があるため、運用環境でのテストを推奨。

### Usage / Examples
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

### Security / Operational reminders
- .env ファイルは絶対にリポジトリへコミットしないこと（config_setup.py のヘッダにも明記）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_SWITCH 設定を必ず確認すること。
- KILL_FLAG_CLEAR_ON_START は本番で "1" にしない（自動クリアは危険。デフォルト "0" を推奨）。

---

以上。必要であれば、各モジュールごとの詳細な変更差分（関数一覧、引数仕様、例）や未実装箇所のチケット化案を作成できます。どのレベルの詳細が必要か教えてください。