CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。  
バージョニングは semver に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 基本コア機能を実装し初回リリースを作成。
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 DB（data/paper_trading.db をデフォルト）に分離し、MockBrokerClient の使用を想定する。
    - エンジンは ExecutionEngine をスレッドで起動し、data/stop_requested.flag による停止フラグ検出で安全に終了する。
    - 起動時にプロセス優先度を "high" に設定する処理を最初に行う。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、不正値はデフォルトへフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB 初期化を行う）。
    - 停止フラグ検知でループを終了し、例外時はログ出力して次のポーリングへ回復する設計。
- 設定管理
  - 環境変数読み込みと Settings クラスを実装（src/kabusys/config.py）。
    - .env ファイルの自動ロード機構（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - .env の読み込み優先順位: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサーは export 付き行、クォート文字列（エスケープ対応）、インラインコメントルール等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / Paper Trading 等）。
    - paper_fill_mode のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーションを実装。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を初期作成・更新。既存値の読み込み、シークレットマスク、選択肢・デフォルト表示、保存確認を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検証（PyYAML があれば内容検査）等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - 候補選定 / 重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を基にセクター比率が上限を超える場合に同セクターの新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対応。未知のレジームは警告出力の上 1.0 でフォールバック。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を用いた保守的評価。
    - 利用可能現金を超える場合はスケールと残差処理で lot_size 単位で再配分する実装。
  - モジュールエクスポートを提供（src/kabusys/portfolio/__init__.py）。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler で日次ローテーション（デフォルト logs/、30 日保持）。
    - 既存ハンドラをクリアして二重登録を防止。ログレベル・ログディレクトリの解決順を定義。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。アクセス権限不足時は警告を出してスキップ。
- Paper Trading 検証ツール
  - paper_verification_report CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム安定性、注文成功率、送信率、API レイテンシ（P95）等を集計してレポート出力。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究用ファクター計算（部分実装）
  - duckdb を利用したファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（モメンタム等の計算方針と定数定義を含む）。
    - Momentum / MA200 / ATR / Volume 等の設計方針と計算ウィンドウ定義を含む（実装はファイル内で継続）。

Changed
- n/a（初回リリースのため既存機能の変更はなし）

Fixed
- n/a（初回リリース）

Notes / Implementation details
- 設定・起動関連の安全対策:
  - 起動時にプロセス優先度設定を最優先で行うことで稼働時の安定性を狙う実装。
  - 停止フラグ（data/stop_requested.flag）や PID ファイルの取り扱いを各ランナーで行うことで外部からの停止制御に対応。
  - monitoring の DB 初期化は冪等（init_monitoring_db）で実行されるため既存 DB に対しても安全。
- .env パーサは export プレフィックス、クォート中のエスケープ、インラインコメントの取り扱いなど実運用を意識した堅牢な実装。
- ファイル I/O / ディレクトリ作成に失敗した場合はログや標準出力へ警告を出し、可能な限りフォールバックして動作を継続する設計。

既知の制約 / TODO
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格の導入を検討。
- research/factor_research.py は計算ロジックの一部が未表示/未完（本リリースでは設計と一部実装を含む）。

参考
- 起動スクリプト:
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
- 設定関連:
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
- ユーティリティ:
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
- ポートフォリオ関連:
  - src/kabusys/portfolio/*
- ツール:
  - src/kabusys/tools/paper_verification_report.py

----- 
この CHANGELOG はコードベースの内容から推測して作成しています。必要であればリリース日・カテゴリ分け・文言の修正を指示してください。