# CHANGELOG

すべての重要な変更を保持するために Keep a Changelog の形式に従います。  
日付は本リリース作成日（2026-04-20）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回公開リリース。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離して動作。
    - プロセス優先度を高く設定（set_process_priority("high")）。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた起動/停止制御。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知時に安全に停止する仕組みを実装。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる。
    - RiskManager のデフォルト設定値を明示（max_position_pct 等）。

  - 監視（Monitoring）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視は実行環境に関わらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグファイルでループを終了、例外時はログ出力して次ポーリングに進む。

- 設定管理
  - 環境変数 / .env 自動ロード機能を追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装。
    - .env / .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き）および自動無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を実装。
    - 複数種の設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading 設定 / 監視閾値 / ログ設定等）。
    - PAPER_FILL_MODE の検証、有効値チェックを追加。
    - env 値検証（KABUSYS_ENV, LOG_LEVEL）のバリデーションを実装。

- 設定ユーティリティ / CLI
  - .env を対話的に生成・更新するウィザードを追加（src/kabusys/config_setup.py）。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定等）を用意。
    - 既存 .env 読み込み、シークレットマスク表示、確認後に .env を安全に出力。
    - デフォルトテンプレートを書く _write_env を実装。

  - 起動前設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml 存在および YAML パース検証（PyYAML がインストールされている場合）。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーへ設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - 既存ハンドラを安全にクローズして二重登録を防止。

  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS の差分を吸収して niciness / priority を設定。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順、タイブレークは signal_rank）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア正規化、スコア合計が 0 の場合は等金額へフォールバックと警告）。

  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap：既存ポジションのセクター時価から上限を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier：market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知の値は 1.0 でフォールバック（警告）。

  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）。
    - calc_position_sizes：allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・総投下上限（available_cash）を考慮したスケーリング、cost_buffer を使った保守的見積り。
    - aggregate cap 超過時のスケールダウンと残差配分アルゴリズムを実装（再現性確保のため安定ソート）。

  - ポートフォリオパッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- 研究 / ファクター計算（雛形）
  - ファクター計算モジュールの骨子を追加（src/kabusys/research/factor_research.py）。
    - モメンタム/MA/ATR 等の設計方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する想定。
    - （ファイル末尾で実装途中でトランケーションあり。将来的にモメンタム計算を実装予定。）

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計してレポート出力。
    - デフォルトの検証閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能。
    - P95 計算ロジック、欠損データ時の N/A 表記を実装。

### Changed
- .env / 環境変数の読み込みロジックを改善（src/kabusys/config.py）
  - export KEY=... 形式をサポート。
  - クォートされた値のバックスラッシュエスケープと閉じクォート解釈に対応。
  - クォートなしの値はインラインコメント（#）を値中のスペース直前にのみコメントとして扱う等、より堅牢なパースを採用。
  - 自動ロードの優先順位を明確化（OS 環境 > .env.local > .env）。

### Fixed
- モニタリングポーリング間隔の安全化（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL に不正（非整数や 0 以下）が指定された場合、警告を出してデフォルト（60 秒）にフォールバックするよう修正。time.sleep に渡す値での ValueError を防止。

- ロギング初期化の堅牢化（src/kabusys/utils/logging_setup.py）
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソールログのみ継続するフォールバックを追加。これにより Docker/権限の異なる環境でも起動しやすくなった。

- プロセス優先度設定の安全化（src/kabusys/utils/process_priority.py）
  - 未対応 OS や権限不足での例外をハンドリングして警告出力し、アプリケーションのクラッシュを防止。

### Notes / Implementation details
- DB 関連
  - 監視情報は SQLite（settings.sqlite_path）に格納し、解析は DuckDB（settings.duckdb_path）で行う設計。Monitoring の初期化関数 init_monitoring_db を用いて必要テーブルの冪等初期化を行う。
  - 実行（execution）は paper_trading モード時に別 SQLite（settings.paper_sqlite_path）を使用することで本番 DB と完全分離。

- Safety / Ops
  - 停止フラグ（data/stop_requested.flag）や PID ファイルによる外部制御を想定。
  - 本番環境（KABUSYS_ENV=live）での注意喚起や Kill Switch 設定（KILL_FLAG_CLEAR_ON_START）の危険性を validate_config で検出できるようにした。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（ただし、シークレット（トークン・パスワード）を .env に保存する際は Git にコミットしないよう明示的に注意を促す文言を config_setup に記載）。

---

開発者向け補足:
- research/factor_research.py はモジュール実装の途中で終端しているため、モメンタム計算の実装を続行する必要があります。
- ExecutionEngine / Monitoring の具体的な内部実装（engine.run_session, monitor.check_once 等）は別モジュールに定義されている前提です。これらのユニットのテストと統合試験を推奨します。