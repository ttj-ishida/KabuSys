# Changelog

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" 準拠です。  
このファイルは、ソースコードから推測できる機能追加・振る舞い・修正点をまとめたものです（実装上の挙動に基づく推測を含みます）。

注: パッケージバージョンは src/kabusys/__init__.py の `__version__` に合わせています。

## [Unreleased]

- 今後の改善候補や未実装の拡張（例: price フォールバックロジック、銘柄別 lot_size サポート、research モジュールの続き実装など）。

---

## [0.1.0] - 初期リリース
リリース日: (初回リリース)

### Added
- 全体
  - Python パッケージ "KabuSys" を追加。自動売買システムのコアユーティリティ群を含む最初のリリース。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による挙動分岐:
      - paper_trading 環境では MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを追加。
    - 停止フラグ (data/stop_requested.flag) を監視し、安全にエンジン停止。
    - 実行中 PID を data/execution.pid に書き出す（Engine 側で pid_file を受け取る設計）。
    - ExecutionEngine の依存コンポーネント（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててスレッドで実行。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視データを記録。
    - stop フラグ検出でループ終了、例外発生時は例外をログに記録して次ポーリングに継続。

- 設定管理
  - config.py: Settings クラスを導入。
    - .env 自動読み込み（プロジェクトルートに基づく .env / .env.local の読み込み、OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 必須変数取得ヘルパー、各種環境変数のデフォルト値と検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や PID / kill flag 関連設定を提供。

  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - 複数の設定項目を対話的に入力（シークレットマスク、選択肢、デフォルト提示）。
    - 生成された .env のフォーマットと注意書き（.env を絶対にコミットしない等）を出力。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML があれば内容も検証）。
    - KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定や Kill Switch 自動クリア設定の警告）。
    - --strict オプションで警告を FAIL として扱う。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定関数 setup_logging を追加。コンソール（stdout）および日次ローテーションのファイルハンドラをルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数や引数で上書き可能。
    - 日次ローテーション・30日分保持をサポート。

  - utils/process_priority.py:
    - set_process_priority(level) を追加し、Windows / POSIX を吸収してプロセス優先度（nice / Windows priority class）を設定。
    - set_cpu_affinity(cpu_count) を追加: 指定コア数への CPU affinity 設定（権限不足や未対応 OS では警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で上位 N を選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による配分（全スコアが 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に新規候補を除外（unknown セクターは無視）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知は 1.0 でフォールバック）。ログに警告を出す場合あり。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方式 ("risk_based"/"equal"/"score") に対応した発注株数算出を実装。
      - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct による position size 計算。
      - equal/score: weight に基づく配分と per-position 上限、lot_size による丸め処理。
      - aggregate cap: 全銘柄合計が利用可能現金を超える場合にスケールダウンし、端数調整のための残差順再配分を行う。
      - lot_size（単元株）や cost_buffer（手数料・スリッページ見積り）を考慮。

  - portfolio/__init__.py: 上記の関数群を公開するパッケージエントリを追加。

- 解析 / レポートツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - 基準値（閾値）を定義して PASS / FAIL を判定（デフォルト閾値: 稼働率 99.0%、成功率 90%、送信率 95%、P95 200ms）。
    - 日付フィルタ（--from/--to）と DB パスの引数/環境変数サポート。P95 の計算実装あり。

- 研究モジュール（途中実装）
  - research/factor_research.py:
    - ファクター計算の設計と一部定数・ docstring を実装（モメンタム、MA200、ATR、出来高関連の計算方針を記述）。
    - DuckDB 経由で prices_daily / raw_financials を参照する想定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の取り扱い:
  - config_setup.py において .env を生成するが、.env を絶対にコミットしない旨の注記を含める（シークレットはマスクして表示）。

### Notes / Implementation Details（補足）
- .env 読み込み:
  - .env/.env.local のパースは export プレフィックス、引用符付き値（バックスラッシュエスケープ対応）、コメント取り扱い（クォートなしでの '#' の扱い）に対応。OS 環境変数は保護され、.env.local は上書き可能。
- DB 接続:
  - 監視（monitoring）は常に settings.sqlite_path（本番監視 DB）を使用する設計。Execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離。
- 停止制御:
  - data/stop_requested.flag による外部停止制御を全起動スクリプトで使用（監視・実行の両方）。kill flag 周りの設定は Settings で提供。
- ログ:
  - ログは stdout に出力し、ファイル出力は日次ローテーションで保存。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
- プロセス優先度:
  - Windows と POSIX (Linux, macOS, FreeBSD) に対応する値マッピングを持ち、設定に失敗した場合は警告を出してスキップする安全設計。

---

この CHANGELOG はソースコードからの推測に基づいて作成されています。実際のリリースノートとして利用する場合は、コミット履歴やリリース計画に基づく追補を推奨します。