Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

フォーマット方針:
- 重要な機能追加は "Added"
- API 仕様・挙動変更は "Changed"
- バグ修正・頑健化は "Fixed"
- 廃止予定・セキュリティ関連は該当があれば記載

[Unreleased]

[0.1.0] - 2026-04-19
--------------------

Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が paper_trading の場合は専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）をサポート。停止フラグ検知で安全に停止。
    - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立て例とデフォルト RiskConfig を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず production の sqlite_path を使用して監視 DB を開く（監視用テーブルの初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。

- 設定 / 環境変数管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml を探索）。
    - .env パース機能を実装（export プレフィックス、クォートとバックスラッシュエスケープ、インラインコメント処理に対応）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - Settings クラスを提供し、以下の設定をプロパティで取得可能に:
      - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL, LINE_*（オプション）
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject" の検証を追加）
      - PID/KILL フラグ / 各種閾値（CPU / Memory / Disk）
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - settings = Settings() のインスタンスをモジュールレベルで提供。

- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成 / 更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）とデフォルト表示、シークレット扱いをサポート。
    - 既存 .env の読み込み・再利用、確認プロンプト、ファイル書き込みを実装。
    - .env テンプレート書き込み（.env に絶対にコミットしない旨のヘッダーを含む）。

- 設定検証 CLI
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の基本チェックを行う CLI を追加。
    - 必須 / 任意環境変数の検査、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML 利用可の場合）、本番向けガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険値など）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（stdout を使用）と、日次ローテート（TimedRotatingFileHandler, 30 日保持）のファイルハンドラをルートロガーに設定。
    - ログディレクトリ自動作成を試み、失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"）。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定関数を追加。
    - Windows と POSIX（Linux, Darwin, FreeBSD）差分を吸収する実装（psutil に依存）。
    - アクセス拒否や未実装 API を安全にスキップする警告処理を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補抽出。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重の重み計算（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存保有比率に基づく候補除外ロジック（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数の計算（未知のレジームは警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に対応した発注株数計算。
    - 単元株（lot_size）での丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した安全弁を実装。
    - 多数の安全チェック（価格取得不可、ゼロ除算回避、上限チェックなど）を実装。

- 研究/分析ツール
  - research/factor_research.py（骨格）
    - DuckDB を使ったファクター計算モジュールの骨格を追加（モメンタム/MA/ATR 等、設計方針と定数定義を含む）。
    - prices_daily/raw_financials を前提として SQL+Python で計算する設計。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、API レイテンシ（avg/max/P95）等を抽出・判定。
    - パス/フェイル基準（閾値）を定義し期間指定（--from/--to）でレポート出力。
    - DB パスの解決順: CLI --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト。

Changed
- 初期リリースとして多数の機能を統合。主な設計方針として以下を採用:
  - 監視（monitoring）と実行（execution）は DB を分離可能（paper_trading 用 DB を別途指定）に設計。
  - ログは stdout に出力しつつファイルへ日次ローテーションで保存（運用時のログ運用を容易化）。
  - .env の自動読み込みはプロジェクトルート探索に基づき CWD に依存しないよう改善。

Fixed
- 設定読み込み/ファイル IO や環境依存処理に対して堅牢性を向上
  - .env 読み込み失敗時に警告を出してスキップするようにし、テスト等で自動読み込みを無効にするオプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。
  - logging_setup: ログディレクトリ作成に失敗した場合、ファイルハンドラ作成をスキップしてもコンソール出力を継続するフォールバックを追加。
  - process_priority: 権限不足や未サポート環境で例外にならないようキャッチして警告するように変更。
  - calc_score_weights / calc_regime_multiplier 等でフォールバックや警告を追加してゼロ除算や未知値による誤動作を防止。
  - paper_verification_report: P95 計算や日付フィルタの取り扱い、DB 存在チェックの文言を整備。

Removed
- （該当なし: 初期リリース）

Security
- 環境変数ファイル (.env) に対して「絶対に Git にコミットしないこと」を README ヘッダに明記（config_setup が生成する .env ヘッダ内に記載）。

Notes / Usage Tips
- 実行スクリプト:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
- 設定ウィザード / 検証:
  - .env の作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の主なキー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV (development|paper_trading|live)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - MONITOR_POLL_INTERVAL（監視のポーリング秒数）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリア注意）
  - LOG_DIR / LOG_LEVEL

今後の TODO（記録）
- research/factor_research.py の詳細実装（各ファクターの SQL 実装・正規化ユーティリティ連携）。
- 銘柄ごとの lot_size や前日終値等のフォールバック価格を取り扱う拡張（position_sizing の注記に記載）。
- より詳細な単体テストと CI 設定（環境変数依存テストの隔離）。

----