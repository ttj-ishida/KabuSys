CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
主なカテゴリ: Added, Changed, Fixed。

Unreleased
----------

### Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用するよう分離。
    - BrokerClientFactory を使ってブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時にエンジンを安全に停止する仕組みを実装。
    - エンジンの PID を data/execution.pid に書き込む（pid_file を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）を実行。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) 検知によるループ終了、KeyboardInterrupt ハンドリング、接続クローズ処理を実装。

- 環境設定関連ユーティリティを追加/改善
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env 読み込みは OS 環境変数を保護する仕組み（protected）を導入。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 行パーサーを強化（export 形式、クォート内のエスケープ、行内コメント処理に対応）。
    - Settings クラスを導入し、各種設定値（DB パス、LINE、kabu API、監視閾値、環境判定フラグ等）をプロパティで取得できるように。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
  - config_setup.py
    - .env の対話式ウィザードを実装。既存 .env の読み込み・編集、秘密値のマスク表示、保存前確認を提供。
    - デフォルト値、選択肢、説明文付きの項目定義を用意。.env を生成/更新する CLI を追加。
  - validate_config.py
    - 起動前に環境・設定を検証する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）などを行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を一括設定するユーティリティを追加。
    - ログレベル・ログディレクトリの解決順序を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - psutil を用いてプラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（high/normal/low）。
    - Windows と POSIX（Linux/Mac 等）に対応。CPU affinity を設定する set_cpu_affinity 関数も提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢性を実装。

- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順・タイブレーク）、等金額配分、スコア加重配分を実装。スコア全体が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数計算（calc_regime_multiplier）を実装。unknown セクターは上限適用対象外。
  - portfolio/position_sizing.py
    - risk_based / equal / score の各配分方式に対応した株数計算を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer（手数料・スリッページ保守係数）を考慮した見積りを実装。

- 解析/検証用ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。SQLite（デフォルト: data/paper_trading.db）から以下を集計して標準出力にレポートを出力:
      - システム稼働率（system_status）、総ポーリング数、エラー数
      - 注文成功率・送信率（trade_logs）
      - リスク却下数（risk_logs）
      - API レイテンシ統計（平均/最大/P95）
    - 判定基準（閾値）はソース内定義（稼働率 99%、成功率 90% 等）。期間指定（--from/--to）や DB パス指定（--db）に対応。

- research/factor_research.py（ファクター計算の骨組み）
  - Momentum / Volatility / Value / Liquidity 等、StrategyModel に基づくファクターを計算するための下地を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
  - （注）ファイルは途中まで実装されているため、完全実装は今後の作業。

### Changed
- 共通設計・セキュリティに関する改善
  - .env 自動ロード時に OS 環境変数を protected として上書き防止するように変更。これにより CI/OS 環境の既存値を意図せず上書きしない。
  - ログ出力を stdout に統一して StreamHandler を標準で使用するように（cron/Task Scheduler での取り扱いを考慮）。
  - run_monitoring と run_execution の起動時にプロセス優先度を最初に high に設定するフローに統一。
  - Monitoring の DB 初期化（init_monitoring_db）は冪等に実行されるため、Start 時に監視テーブルの存在を保証するように。

### Fixed
- 環境変数/設定の妥当性チェックを強化
  - MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）に対するハンドリングを追加し、警告後にデフォルトへフォールバックするように。
  - PAPER_FILL_MODE の不正値検出時に ValueError を投げることで早期に設定ミスを検出。
  - process_priority と CPU affinity の設定で権限エラーや未実装 API を捕捉し、警告を出して処理を継続するように変更（実行時の致命的な停止を回避）。

0.1.0 - 初期リリース
--------------------

リリースバージョン: 0.1.0
（パッケージ __version__ に基づく初期リリースの概要）

### Added
- パッケージ基盤
  - kabusys パッケージの初期モジュール群を追加。
  - __version__ = "0.1.0" を設定。

- 実行エンジン関連
  - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等の主要コンポーネント（ソース参照箇所）。
  - BrokerClientFactory によるブローカークライアント抽象化。

- 監視機能
  - SystemMonitor と監視データベース初期化（init_monitoring_db）の利用により、system_status テーブル等を用いた稼働監視の基盤を整備。

- 設定管理
  - Settings クラスにより環境変数ベースの設定取得を統一。
  - データベースやログ関連のデフォルトパス（data/ 以下）を提供。

- ポートフォリオ構築（アルゴリズム）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数など、PortfolioConstruction に準拠した純粋関数群を実装。

- ロギング / プロセス管理
  - 統一的なログ設定ユーティリティ（ログ回転/ファイル出力の実装）を提供。
  - プロセス優先度設定と CPU affinity のユーティリティを実装。

- ツール群
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

### Notes
- 多くのモジュールが外部依存（psutil, duckdb, PyYAML 等）を想定しています。実行環境に応じてインストールしてください。
- config/*.yaml の検証は PyYAML の有無に依存します。インストールされていない場合はパースチェックをスキップして警告を出します。
- research/factor_research.py はファクター計算ロジックの骨組みを追加していますが、まだ実装途中の箇所があります。ファクター計算の完全実装は今後のリリースで追加予定です。

履歴の補足
------------
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴がある場合はそちらに合わせて追記・修正してください。