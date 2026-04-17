# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初回リリース（KabuSys 0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定 / ロード
  - Settings クラス（src/kabusys/config.py）を導入。環境変数から各種設定を取得する共通インターフェイスを提供（J-Quants、kabuAPI、LINE、DBパス、監視閾値、実行環境判定等）。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。読み込み順は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化をサポート。
  - .env のパースはクォートや export 形式、インラインコメント等に対応する堅牢な実装を提供。
  - 新しい環境変数 / 設定項目:
    - PAPER_FILL_MODE（paper_trading 用の MockBroker の約定モード。valid: "instant" | "partial" | "never" | "reject"）
    - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 SQLite のパス、デフォルト: data/paper_trading.db）
    - MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒単位で上書き可能、デフォルト 60 秒）
    - KILL_FLAG_CLEAR_ON_START（起動時に kill flag を自動クリアするか）
    - その他: DUCKDB_PATH / SQLITE_PATH / LOG_LEVEL など既存設定の明示化と検証

- CLI ユーティリティ
  - 環境設定ウィザード（src/kabusys/config_setup.py）
    - 対話式に .env を生成・更新するウィザードを提供。項目説明、シークレット入力、既存値の再利用、保存確認を実装。
    - デフォルト値や選択肢表示、保存フォーマット（.env のテンプレート）を提供。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の存在・形式チェック、必須環境変数の未設定チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML が無い場合は YAML 検証をスキップし警告を出す。
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の SQLite DB から稼働率、注文成功率、送信率、レイテンシなどを集計して PASS/FAIL を判定するレポートを標準出力に出力。
    - CLI オプション: --from, --to（YYYY-MM-DD）、--db（DB パス）。デフォルト DB は環境変数または data/paper_trading.db。
    - P95 計算や各種閾値（稼働率 99%、注文成功率 90% 等）を組み込んだ判定ロジック。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine 起動用のエントリポイント。プロセス優先度を最初に設定（set_process_priority("high")）。
    - Paper Trading（KABUSYS_ENV=paper_trading）の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite DB に記録し、本番 DB と分離。
    - Broker クライアントの生成を BrokerClientFactory で抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動（スレッド実行）。停止フラグ（data/stop_requested.flag）を検知したら安全に停止。
    - execution.pid ファイルの扱い（PID ファイルパス）を組み込み。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を組み込み。initial_portfolio_value は broker.get_available_cash() を利用。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動用。プロセス優先度設定、SQLite（監視用 DB）と DuckDB の接続初期化を行う。
    - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（不正値はログを出してデフォルトにフォールバック）。
    - 停止フラグ検知によりループを終了。例外発生時はログ出力して次回ポーリングへ移行。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計（監視は常に本番 DB を参照）。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順 + signal_rank タイブレークで選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは警告の上 1.0 にフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリングと端数処理を実装。
    - risk_based モードではリスク許容率（risk_pct）と損切り率（stop_loss_pct）でベース株数を算出。
    - 入力価格欠損時のスキップやログ出力を行う。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily テーブルから算出。ウィンドウ行数不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR の相対値、20日平均売買代金、出来高比などを計算。true_range の NULL 伝播を考慮して正確に計算。
    - DuckDB 接続を受け取り SQL と Python で計算する設計。外部 API 非依存。
    - 大きめのスキャンバッファ（例: MA200 用に 400 calendar days）を採用し週末・祝日を吸収する設計。

- プロセス優先度 / CPU アフィニティユーティリティ
  - src/kabusys/utils/process_priority.py を導入。
    - set_process_priority(level) で Windows/Linux/macOS の差分を吸収して優先度を設定。psutil を使用し、権限不足や未対応環境では警告を出してスキップ。
    - set_cpu_affinity(cpu_count) による CPU ピン留め機能。利用可能コア数より大きい指定があっても全コア使用にフォールバック。エラー時は警告。
    - サポートする優先度レベル: "high", "normal", "low"。

- DB / 初期化
  - run_* スクリプト内で監視テーブルの存在を保証するための init_monitoring_db 呼び出しを組み込み（冪等に動作することを想定）。
  - 実行系と監視系で SQLite / DuckDB を組み合わせて利用する設計を採用。

### 変更（設計・仕様）
- 監視（Monitoring）は起動環境にかかわらず本番の sqlite_path を参照する仕様に決定（run_monitoring.py）。
- run_execution.py は KABUSYS_ENV=paper_trading 時に paper_trading 専用 DB を使用して本番 DB と分離する仕様。

### 注意点 / 既知の挙動
- .env 自動読み込み:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（配布後の挙動を安全にするため）。
  - OS 環境変数は保護され、.env.local の override でも上書きされない。
- PROCESS 優先度設定や CPU affinity は OS と実行権限に依存するため、設定に失敗した場合はログ警告を出してスキップする実装。
- position_sizing で価格データが欠損（0 や None）の場合、該当銘柄はスキップされる。将来的にフォールバック価格の導入を検討する旨の TODO が残されています。
- Paper Trading の検証レポートは対象 DB のテーブル（system_status, trade_logs, risk_logs など）が存在しない場合でも OperationalError を捕捉してデフォルト値にフォールバックする堅牢性を持つ。

---

今後の予定（想定）
- portfolio / position_sizing の lot_size を銘柄別にサポートするための拡張（stocks マスタから lot_size を取る）。
- monitoring / reporting の追加メトリクスや通知（LINE）統合の強化。
- DuckDB を用いた追加の分析クエリ・ETL ユーティリティの整備。