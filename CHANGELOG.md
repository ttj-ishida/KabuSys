# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
各リリースの要約はコードベースから推測して記載しています。

## [0.1.0] - 2026-04-19

### Added
- 基本コア実装を追加（KabuSys 初回リリース相当）。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV により paper_trading の場合は専用の MockBroker を使用し、Paper Trading 用 DB（data/paper_trading.db）に完全分離して記録する挙動をサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止用フラグファイル（data/stop_requested.flag）と PID 管理（data/execution.pid）による clean stop 処理を実装。
    - ExecutionEngine の起動前に monitoring テーブルの初期化を行う（冪等処理）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効としてデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検出によるループ終了処理と例外ハンドリングを実装。

- 設定・環境変数管理
  - config.py
    - Settings クラスを実装し、アプリの設定（各種 API トークン、DB パス、監視閾値、環境種別など）を環境変数から取得する仕組みを提供。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）を実装。
    - KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - 自動 .env ロード機能を追加（.env / .env.local をプロジェクトルートから読み込む）。OS 環境変数は上書きされないよう保護。KABUSYS_DISABLE_AUTO_ENV_LOAD にて無効化可能。
    - settings = Settings() によりモジュールレベルで利用可能に。

- 設定支援ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。
    - シークレット項目はマスク表示、既存 .env の読み込み、保存前確認、ファイル生成ロジックを提供。
  - validate_config.py
    - 起動前チェック用 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml の存在確認・PyYAML を用いたパース検証（PyYAML 未インストール時は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを実装。コンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log、30日保持）をルートロガーにセットアップする。
    - LOG_DIR / LOG_LEVEL 環境変数や引数で上書き可能。既存ハンドラはクリアして重複を防止。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）をクロスプラットフォーム（Windows / POSIX）で設定する機能を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（例外は警告で無効化して継続）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates: スコア降順、signal_rank でタイブレーク）を実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算し、閾値超過セクターの新規候補を除外するロジックを提供（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）を実装（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告後 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ想定）を考慮したスケーリング、残差分の配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポートを出力。
    - CLI 引数 --from / --to / --db に対応。P95 計算や各種閾値（稼働率 >=99%、成立率 >=90% 等）を使った PASS/FAIL 判定を実装。

- 研究用モジュール（基盤）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの骨格を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計方針を採用（実装の続きを想定）。

- パッケージメタ情報等
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" と主要サブパッケージ列挙を追加。
  - portfolio などの __all__ エクスポートを整理。

### Changed
- （初版）主要コンポーネント設計に合わせた設定/ログ/プロセス制御の仕様を確定。
  - .env 自動読み込みの挙動: OS 環境変数を保護しつつ .env/.env.local を読み込むロジックを実装（.env.local は .env を上書き）。
  - ログハンドラの振る舞い: 既存ハンドラを明示的にクリアしてから再設定することで二重出力を防止。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line: export プレフィックス、クォート値内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮して .env 行のパースを実装・修正。
- run_monitoring における MONITOR_POLL_INTERVAL の不正値処理を追加（不正な値は警告してデフォルトにフォールバック）。

### Security
- .env 作成ウィザードの注意書きに「.env は絶対に Git にコミットしないこと」を明記。

### Notes / Known limitations
- research/factor_research.py はファクター計算の設計を含むが、一部実装（ファイル末尾の計算開始部分など）が続きの実装を要する可能性があることをコードから推測しました。
- 実際の ExecutionEngine / Broker クライアント等の内部実装（発注ロジック、監視ロジックなど）は本差分では表に出ておらず、上記はエントリポイントや設定周り、純粋関数群の実装に関する記述が中心です。
- 動作には外部パッケージ（psutil, duckdb, PyYAML など）が必要です。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告します。

---

変更はソースコードの内容から推測して作成しました。必要であれば各機能ごとにより詳細な変更点（関数・引数の仕様、既知のチケット番号など）を追記できます。