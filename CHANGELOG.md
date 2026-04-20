# Keep a Changelog — 変更履歴

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このファイルは、提示されたコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-04-20

### 追加
- 全体
  - 初期リリース。パッケージメタ情報として `__version__ = "0.1.0"` を設定。

- 起動スクリプト / 実行環境
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いてブローカークライアントを組み立て（paper_trading の場合は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - エンジンスレッドをデーモンで起動し、data/stop_requested.flag による停止検知を実装。
    - 起動 PID を data/execution.pid に保存（Engine 側の pid_file を利用）。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用。
    - DuckDB を利用した接続（duckdb_path）。
    - data/stop_requested.flag による停止検知を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - config: 環境変数読み込み・設定管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env 読み込みは override / protected（OS 環境変数保護）をサポート。
    - 複雑な .env 行パース（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）を実装。
    - Settings クラスを提供し、アプリケーション用設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）を型付け・検証して取得可能に。
    - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - デフォルト値:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
      - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
      - PID_FILE_PATH: data/execution.pid

  - config_setup: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabu API / DB パス / LINE トークン等の入力をサポート。
    - シークレット項目は表示マスク、既存 .env の読み込みと Enter による既存値継承に対応。
    - 生成した .env はテンプレートヘッダ付きで書き出す。

  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数未設定の検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank）で上位 N 件選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア正規化による重み計算（全スコアが 0 の場合は等配分へフォールバック）。

  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは 1.0 でフォールバック、bear=0.3 等）。ログによる警告を出力。

  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて買付株数を算出。
      - risk_based: リスク許容率（risk_pct）と stop_loss_pct でベース枚数を算出。
      - equal/score: ウェイトと max_utilization を使って配分。
      - lot_size（例: 100）で丸め、max_position_pct による per-stock 上限を適用。
      - cost_buffer を用いた保守的コスト見積り、aggregate cap 超過時のスケーリングと残差処理（lot 単位で再配分）を実装。

- ユーティリティ
  - utils.logging_setup:
    - 統一的なロギング設定ユーティリティを追加。
    - stdout（StreamHandler）出力と日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。
    - デフォルト LOG_DIR: logs/、デフォルトログ保持日数: 30 日。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。

  - utils.process_priority:
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX 差分を吸収）。
    - set_process_priority(level: "high" | "normal" | "low") を提供。psutil を使用し、失敗時は警告ログを出力してスキップ。
    - set_cpu_affinity(cpu_count) を提供（指定コア数に固定、失敗時は警告）。

- モニタリング / DB 初期化
  - monitoring.monitoring_db: init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - run_monitoring および run_execution 起動時に sqlite3 / duckdb 接続を確立。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime%), 注文成功率（fill rate）, 送信率（send rate）, API レイテンシ（avg/max/P95）等を算出。
    - P95 計算、期間フィルタ（--from / --to）、PAPER_TRADING_SQLITE_PATH と --db による DB 指定をサポート。
    - 合格基準（閾値）を定義: 稼働率 >= 99.0%、fill >= 90%、send >= 95%、P95 latency <= 200 ms。判定を PASS/FAIL で出力。

- 研究用（research）
  - research.factor_research: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA, ATR, ボラティリティ等）。関数 calc_momentum のインターフェースと設計方針を記載（実装は継続中 / 一部未完）。

### 変更
- なし（初回リリースのため、変更履歴は追加のみ）

### 修正
- なし（初回リリース）

### 注意事項 / 実運用メモ
- .env / OS 環境変数の取り扱い:
  - 自動ロード: プロジェクトルートが特定できる場合に .env/.env.local を自動で読み込みます。OS 環境変数は保護され、.env.local は上書きを行います。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化してください。
- 本番（live）環境時は設定を慎重に確認してください（validate_config にて警告を出すガードを実装）。
- run_monitoring は監視 DB に対して本番 sqlite_path を利用します（環境に関係なく）。
- run_execution は paper_trading 環境時に paper_trading 専用 DB を使うことで本番 DB と完全分離します。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、標準出力のみで動作します。

---

この CHANGELOG は、提示されたソースコードから機能や挙動を推測して作成しています。実際の変更履歴やリリースノートはプロジェクトの Git コミット履歴やリリース管理情報に基づいて追記・調整してください。