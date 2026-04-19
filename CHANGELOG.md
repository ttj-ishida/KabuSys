# Changelog

すべての重要な変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期実装。KabuSys 自動売買フレームワークのコアモジュールを追加。
  - パッケージメタ情報: __version__ = "0.1.0" を設定。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite (デフォルト: data/paper_trading.db) を使用して本番 DB と完全分離する挙動を実装。
    - ブローカークライアント生成は BrokerClientFactory 経由。
    - ExecutionEngine の起動・停止制御（PID ファイル、stop flag）、スレッド実行を実装。
    - デフォルトの RiskConfig（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を組み込み、initial_portfolio_value を broker.get_available_cash() で初期化。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用。
    - 停止フラグファイル (data/stop_requested.flag) を検知して安全終了。
- 設定管理
  - config.py: 環境変数 / .env 読み込み・管理クラス Settings を追加。
    - .env の自動ロード（プロジェクトルート検出: .git または pyproject.toml）を実装。優先順位は OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース処理は export プレフィックス、クォート、インラインコメント等に対応する堅牢な実装。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の有効値チェック（instant|partial|never|reject）を実装。
    - 環境（KABUSYS_ENV）・ログレベルなどのバリデーション。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。
    - .env の読み込み・更新、秘密値のマスク表示、選択肢提示、保存確認を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの存在チェック（親ディレクトリ）、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向け追加ガード（LINE トークン、KILL_FLAG_CLEAR_ON_START）を実装。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的な logging セットアップを実装。
    - コンソール出力は stdout、さらに TimedRotatingFileHandler による日次ローテーション（30日保持）をサポート。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル / ログディレクトリの解決順序を実装（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level: "high"|"normal"|"low") を提供。psutil の権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) によるコア固定をサポート（利用不可時は警告でスキップ）。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別上限 (max_sector_pct、デフォルト 30%) を適用して候補を除外。
      - "unknown" セクターは上限チェックの対象外。
      - 売却予定銘柄はエクスポージャ計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームはフォールバック 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
      - 単元株丸め (lot_size, デフォルト 100)、1銘柄上限、aggregate cap（available_cash）を実装。
      - cost_buffer を用いた保守的なコスト見積り、スケーリング時の残差処理（lot 単位で追加配分）を実装。
      - price 欠損時のスキップやログ出力を実装。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py: Paper Trading DB を読み取り検証レポートを出力する CLI を追加。
    - 指定期間（--from / --to）で system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数を集計。
    - PASS/FAIL 判定の閾値を定義（稼働率 >= 99%、fill rate >= 90%、send rate >= 95%、P95 latency <= 200ms）。
    - P95 を独自実装、SQL の日付フィルタ組み立てなど堅牢なクエリ実装。
- データアクセス関連
  - monitoring_db 初期化呼び出しを実行スクリプト側で保証（init_monitoring_db を run_monitoring / run_execution の起動処理で呼び出し）。

### 変更 (Changed)
- 起動時に最初にプロセス優先度を "high" に設定することで、監視・実行プロセスの競合を低減する運用方針を導入。
- ログ出力は標準出力へ出す設計に統一（stdout を利用）し、ファイル出力はログディレクトリ確保に依存する柔軟な実装に変更。

### 修正 (Fixed)
- .env パーサーの強化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など、多様な .env フォーマットに対応。
- validate_config: PyYAML が未インストールでもスクリプトが動作するように YAML チェックの有無を条件分岐で扱う。

### 注意事項 (Notes)
- Settings._require は必須環境変数が未設定の場合に ValueError を送出します。CLI ツールやバッチ実行前に validate_config を実行して設定漏れを検出することを推奨します。
- PAPER_FILL_MODE の値が不正な場合は Settings が ValueError を送出します（有効値: instant, partial, never, reject）。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が与えられた場合、自動的にデフォルトの 60 秒にフォールバックし警告を出力します。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を "1" にすることは推奨されません（validate_config で警告を出します）。
- process_priority と CPU affinity の設定は OS・権限に依存します。権限不足の際は警告を出してスキップされます。

### 未完 / TODO
- research/factor_research.py はファイル末尾が途中（calc_momentum の実装途中）で切れている箇所があります。ファクター計算ロジックの完成が今後のタスクです。
- position_sizing の lot_size を銘柄毎にサポートする拡張（stocks マスタ参照等）を検討。

---

（初期リリースのため主に機能追加が中心です。以降のリリースではバグフィックス、性能改善や未完のファクター計算の実装を継続します。）