# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

### Added
- factor_research モジュールの機能拡張（モメンタム等のファクター計算機能を実装中）。一部実装が途中のため、今後リリースで完了予定。

### Notes
- いくつかのモジュールで追加のテスト・ドキュメント整備を予定。

---

## [0.1.0] - 2026-04-21

初回公開リリース。システム全体のコア機能と運用用ユーティリティを含む最初の安定版です。

### Added
- コアパッケージとバージョン情報
  - パッケージ初期バージョン `__version__ = "0.1.0"` を追加。

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db 既定）と分離して運用。
    - ストップフラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - プロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を調整可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（設計上の振る舞いとして明示）。

- 設定管理
  - config.py: 環境変数/.env の自動読み込み・管理を追加。
    - プロジェクトルート検出（.git または pyproject.toml に基づく）で .env/.env.local を自動ロード（必要に応じて無効化可能）。
    - .env パーサーは export 形式や引用符付き値、インラインコメントに対応。
    - Settings クラスでアプリケーション設定（DB パス、API トークン、閾値、環境判定フラグ等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーションや PAPER_TRADING_SQLITE_PATH 等の設定をサポート。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - シークレット項目はマスク表示、デフォルト/既存値の再利用、確認プロンプトなどを備える。
  - validate_config.py: .env と config/*.yaml の検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の値チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在・パース検証（PyYAML がない場合は警告）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート/上位選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の重み算出（全スコア 0 の場合のフォールバックロジックあり）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター暴露に基づき候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバック1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1銘柄上限・全体投下上限（aggregate cap）を考慮したスケーリング、cost_buffer による保守的見積り、残余キャッシュを用いた端数配分の処理を実装。

- 監視・実行ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。
    - コンソール出力は stdout、ファイルは日次ローテーション（TimedRotatingFileHandler）で最大30日分保持。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac/FreeBSD）を抽象化したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。
    - 実行権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- 実行系コンポーネントの組み立て（run_execution で利用）
  - BrokerClientFactory により環境に応じたブローカークライアント生成（paper_trading/mocked 実装を想定）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てに必要な依存性注入を整備（設定値やリスク閾値を既定値で指定）。

- モニタリング関連
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を利用して監視テーブルの存在を保証（冪等）。
  - SystemMonitor 呼び出しで単一ポーリング（check_once）を実行し、例外はログに記録してループ継続。

- 分析/検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを SQLite（PAPER_TRADING_SQLITE_PATH）から生成するスクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計・判定（PASS/FAIL）する。
    - P95 計算、期間フィルタリング、欠損テーブルの扱い（OperationalError のサニタイズ）を実装。

- 研究用モジュール
  - research/factor_research.py
    - ファクター計算の設計と多くの定数・ユーティリティを導入（モメンタム/Value/Volatility/Liquidity を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する方針。モジュールの一部実装（モメンタム計算等）を提供（実装途中の箇所あり）。

### Changed
- 主要起動点でのプロセス優先度設定を追加（実行開始直後に set_process_priority("high") を呼び出す）。
- ログ設定を全スクリプト共通化し、ログファイル名はアプリ名ベースで logs/<app_name>.log に出力。

### Fixed
- .env 読み込みにおける多様なフォーマット（export 付き、引用符、インラインコメント）への堅牢性を向上。
- ログディレクトリ作成失敗時のアプリケーション崩壊を回避し、コンソールログで継続するように変更。

### Notes / Behaviour
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず設定された sqlite_path（デフォルト data/monitoring.db）を使用する設計になっています。運用時の DB 分離に注意してください。
- Paper Trading は paper_sqlite_path（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可、既定 data/paper_trading.db）に完全に分離して記録します。
- 環境変数自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後も .env 自動読み込みが期待通りに動作するよう設計されています。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE は有効値が限定されており、不正値は ValueError を送出します（instant/partial/never/reject）。

### Known issues / TODO
- research/factor_research.py の一部処理が未完（実装途中の箇所あり）。本番利用前に完成・テストが必要。
- position_sizing の価格欠損時（price=0.0）の扱いに注記（TODO コメントあり）：フォールバック価格（前日終値など）の採用を検討。
- 単元株数 lot_size 固定（現在はグローバルなデフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を予定。

---

## 参考: 既知の環境変数 / 設定
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- SQLITE_PATH（監視用 DB）
- DUCKDB_PATH（分析用 DB）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START（本番注意フラグ）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）

---

（この CHANGELOG はソースコードの内容から推測して記載しています。実際のリリースノートとして使用する際は、コミット履歴やリリース管理ポリシーに合わせて適宜調整してください。）