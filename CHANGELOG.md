# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 以下はリポジトリ内のソースコードから推測して作成した変更履歴です。

## [Unreleased]

### 追加予定 / 検討中
- なし（現状は初期リリースとして v0.1.0 を記載）

---

## [0.1.0] - 2026-04-24

初期リリース。自動日本株売買システム「KabuSys」の基本コンポーネントを実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを導入（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 多数のコアモジュールと CLI スクリプトを追加。

- 設定管理
  - 環境変数 / .env 自動読み込み機能（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env / .env.local をロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 複雑な .env の行（export プレフィックス、引用符内のエスケープ、インラインコメント）に対応するパーサ実装。
  - Settings クラスで各種設定をプロパティとして提供（DB パス、API トークン、監視閾値、環境判定など）。
  - .env 初期作成・更新を支援する対話式ウィザードを実装（src/kabusys/config_setup.py）。
    - 標準的な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話で作成・保存可能。
    - 秘匿値はマスク表示。

- 設定検証
  - 起動前に環境変数と config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がインストールされている場合）等。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行 / 監視スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite DB を使用して本番 DB と完全に分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を通じて実ブローカーまたは MockBroker を切替可能。
    - Engine をスレッドで動かし、 data/stop_requested.flag による外部停止（Kill Switch）に対応。
    - 実行時にプロセス優先度を high に設定。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）。
    - 環境に関係なく監視は本番用 sqlite_path を参照（monitoring 用 DB を本番 DB に保存する設計）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値時は警告を出してデフォルトにフォールバック。
    - 起動時にプロセス優先度を high に設定。

- ロギング / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして重複を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 系（Linux/Mac/FreeBSD）を抽象化して nice / priority を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足などの状況では安全に警告を出してスキップ。

- ポートフォリオ構築
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順、タイブレークは signal_rank）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア正規化配分、全スコア 0 の場合は等金額へフォールバック）。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター別エクスポージャから上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未定義は 1.0 で警告フォールバック）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）。
    - risk_based、equal、score の allocation_method に対応。
    - lot_size（単元株）考慮、max_position_pct（1銘柄上限）、max_utilization（投下上限）を反映。
    - aggregate cap（合計投資額が利用可能現金を超えた場合のスケールダウン）と残余キャッシュでの端数配分ロジックを実装。
    - 価格未取得時のスキップやログ出力あり。

- 研究 / ファクター
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の計算方針コメント、定数定義、calc_momentum の冒頭設計を含む（calc_momentum は実装途中の箇所あり）。
    - DuckDB を用いた prices_daily / raw_financials 参照の設計。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH（もしくは --db オプション）から SQLite に接続してレポート生成。
    - システム稼働率、注文成功率（Filled/Created 比）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - Pass/Fail 判定基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）を実装。
    - P95 計算、日付フィルタ（ISO8601 UTC 変換）、欠損テーブルへの耐性を備える。

### Changed
- 初期設計上のふるまい（実運用を意識した安全策）
  - 監視コンポーネント（SystemMonitor）は常に本番用 sqlite_path を使用する設計とし、誤って paper_trading 環境で監視データを本番 DB に影響させるリスクを明示的に管理（src/kabusys/run_monitoring.py）。
  - run_execution は paper_trading 時に専用 DB を使用して発注ログ等を完全分離（src/kabusys/run_execution.py）。
  - 起動時にプロセス優先度を最優先で設定することで、実行中の安定性を確保（run_execution, run_monitoring）。
  - logging_setup は stdout（StreamHandler）を標準で利用するように設計。これは Task Scheduler / cron 等でのログリダイレクト運用を考慮した設計。

### Security
- .env ウィザードと validate_config により、秘密情報（API トークン・パスワード等）の設定漏れやプレースホルダ残しを早期検出できるようにした（config_setup.py, validate_config.py）。
- .env の書き出しテンプレートで「.env を Git にコミットしないこと」を明記。

### Notes / Known limitations
- research/factor_research.calc_momentum 等、ファクター計算モジュールは設計の骨格や定数が実装されていますが、一部関数は未完（ファイル末尾で途中）です。
- monitoring_db や SystemMonitor、ExecutionEngine、BrokerClient 等の詳細実装は本ログのコード範囲外（参照はあるがファイル未提示）であるため、本 CHANGELOG は提示されたコードファイルの観察に基づき作成しています。
- process_priority の実行は OS 権限に依存するため、権限不足時は警告ログを出力して処理を継続します。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や CWD が異なる場面でも動作するように設計されているが、検出できない場合は自動ロードをスキップします。

---

追記・修正希望があれば、反映して更新版の CHANGELOG を作成します。