# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

全般:
- 各ファイルの実装内容はソースコードから推測して記載しています。
- バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-23

### Added
- 初期公開: KabuSys v0.1.0 を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"。

- 実行 / 監視スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading では MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db）と完全に分離して動作する挙動を実装。
    - BrokerClientFactory を介したブローカークライアント生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による停止、data/execution.pid に PID ファイルを出力する運用を想定。
    - SQLite（本番または paper_trading 専用）と DuckDB の接続を行い、監視用テーブルの初期化（init_monitoring_db）を保証。
    - RiskManager のデフォルト設定を内蔵（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。initial_portfolio_value は broker.get_available_cash() から取得。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨の挙動を実装。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
    - check_once() の例外を捕捉してログ出力し次のポーリングへ継続。

- 環境設定 / 検証ツール
  - src/kabusys/config.py
    - Settings クラスを導入し、環境変数・設定値を集中管理。J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定などのプロパティを提供。
    - .env の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。読み込み順: OS 環境 > .env.local > .env。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
    - .env 解析は export プレフィックス、クォート（シングル／ダブル）、エスケープ、インラインコメント等に対応。
    - PAPER_FILL_MODE（paper trading の約定挙動）や PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定を提供。
    - env 値の検証（KABUSYS_ENV, LOG_LEVEL 等）のチェックを実装。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を提供。
    - プロンプト・既存 .env の読み込み・シークレットマスク表示・保存確認などを実装。生成される .env のテンプレートを明記（.env を Git にコミットしない旨の注意も含む）。

  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML が無い場合は警告）、本番環境（live）用の追加ガードチェック等を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - setup_logging 関数を追加。アプリ共通のログ設定（コンソール stdout 用 StreamHandler と 日次ローテートの TimedRotatingFileHandler）をルートロガーへ設定。
    - デフォルトログディレクトリ: logs/、日次ローテーションで 30 日分保持。
    - LOG_DIR / LOG_LEVEL の解決順と、ディレクトリ作成失敗時のフォールバック（コンソール出力のみ）に対応。

  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を追加。Windows と POSIX 系（Linux/macOS 等）を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。権限不足や未対応環境では警告を出しスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を設定（psutil 使用）。不許可時は警告を出しスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights: 等金額配分（各重み = 1/N）。
    - calc_score_weights: スコアに基づく重み付け。全スコアが 0 の場合は等金額配分にフォールバック（警告ログを出力）。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を緩和するため、既存保有のセクター比率が上限（max_sector_pct）を超えるセクターの新規候補を除外するロジック。unknown セクターは制限を適用しない。売却予定銘柄はエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す実装（デフォルト値: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告ログ）。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算する包括的ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）から基準株数を計算。
      - equal/score: 重み（weights）に基づき配分。max_position_pct, max_utilization, lot_size（単元株）などを考慮。
      - 単元株丸め（lot_size）と、全銘柄合計が利用可能現金（available_cash）を超過する際のスケーリング（スケールダウン）・端数配分アルゴリズム（残差に基づく lot_size 単位追加）の実装。
      - cost_buffer による手数料／スリッページ見積りの保守的評価をサポート。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージ API として公開。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を読み、検証レポートを生成する CLI を追加。
    - システム安定性（稼働率 / 総ポーリング数 / エラー数）、注文成功率（Created / Filled / Sent）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - P95 の計算、日付フィルタ（--from/--to）、PASS/FAIL の閾値を定義（稼働率 >= 99%, 注文成功率 >= 90%, 送信率 >= 95%, P95 <= 200 ms）し、判定ロジックを実装。
    - DB が存在しない場合のエラーメッセージと代替方法（環境変数 / --db）を案内。

- リサーチ（ファクター算出）ベース
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを追加。Momentum / Value / Volatility / Liquidity の設計方針と定数（例: 1M/3M/6M、MA200、ATR20 等）を定義。
    - calc_momentum 関数（DuckDB の prices_daily テーブルを想定）を実装する方向で開始（ファイル終端で実装途中の可能性あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Behaviors
- .env 自動読み込みは OS 環境変数を保護するため、既存の OS 環境変数を上書きしないよう配慮（.env.local は上書き可能だが protected set による保護あり）。
- logging_setup は stdout を使用しているため、cron 等で stdout/stderr を一本化してリダイレクトする運用を想定。
- process_priority / cpu_affinity の設定は環境によっては権限が必要。失敗時は警告を出して処理を継続する安全設計。
- 実行・監視スクリプトは DB と DuckDB を両方開く設計（監視データと分析データを分離）。
- run_execution は停止フラグが既に立っている場合にエンジンを起動しない保護機構を備える。

### Security
- .env の取り扱いに関して注意書き（.env を絶対に Git にコミットしない）を config_setup のテンプレートに明記。

---

今後の提案（実装候補・改善点、コード中に TODO 記載あり）
- position_sizing の価格フォールバック（price が欠損する場合、前日終値や取得原価からのフォールバック）を実装すると安全性が向上します。
- factor_research の各ファクター実装（Value / Volatility / Liquidity）と DuckDB 最適化の続き。
- config/*.yaml の完全なパース・スキーマ検証（JSON Schema など）による堅牢性向上。
- テスト（ユニット / 結合）と CI パイプラインの整備（特に env 読み込み、process_priority 周りは環境依存のためモックが必要）。

（以上）