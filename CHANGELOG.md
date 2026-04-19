Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

（現在なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを追加: __version__ = "0.1.0"

- 起動スクリプト / 実行フロー
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループ起動用スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御に data/stop_requested.flag を使用。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py を追加
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の Mock ブローカ（paper_trading DB）を使用し、本番 DB と分離。
    - スレッドでエンジンを起動し、停止フラグ（data/stop_requested.flag）で停止制御。
    - 実行 PID ファイルを data/execution.pid に出力する仕組み。

- 設定管理 / 検証 / ウィザード
  - config.py を追加
    - .env 自動読み込み（.env, .env.local）機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - .env パースロジック（クォート、export 形式、インラインコメント）を備える堅牢な実装。
    - Settings クラスで環境変数を型付きプロパティとして提供（DB パス、API トークン、監視閾値、環境判定フラグ等）。
    - paper_fill_mode（PAPER_FILL_MODE）のバリデーションを実装（instant/partial/never/reject）。
  - validate_config.py を追加
    - .env と config/*.yaml を事前検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスや YAML ファイルの存在・パース検証を実施。
    - --strict オプションで警告も失敗扱いにできる。
  - config_setup.py を追加
    - 対話式ウィザードで .env を新規作成・更新する CLI。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用に対応。

- ユーティリティ
  - utils/logging_setup.py を追加
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた標準的なログ初期化関数 setup_logging を提供。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順を実装。
    - ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続。
  - utils/process_priority.py を追加
    - psutil を用いたプロセス優先度（Windows/Linux/macOS 対応）と CPU affinity 設定ユーティリティを提供。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を実装。権限不足等は警告でスキップ。

- Execution 系コアコンポーネントの組み立て
  - ExecutionEngine 起動時の依存組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を run_execution.py にてサンプル構成として実装。
  - RiskManager の初期設定（デフォルト値群）をデモ用に設定し、利用可能残高を初期ポートフォリオ値として参照。

- 監視・モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run_monitoring / run_execution の起動時に行い、監視テーブルが存在することを保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）を解析して検証レポートを標準出力に生成。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（平均、最大、P95）等を集計し PASS/FAIL 判定を行う。
    - コマンドライン引数 --from / --to / --db に対応。

- ポートフォリオ構築 / リスク調整 / ポジションサイジング
  - portfolio/portfolio_builder.py を追加
    - シグナルの候補選定（score 降順 + tie-breaker）、等重配分・スコア重み配分の純粋関数を提供。
  - portfolio/risk_adjustment.py を追加
    - セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装。
    - 未知レジームはフォールバック動作（警告ログ）で 1.0 を返す。
  - portfolio/position_sizing.py を追加
    - risk_based / equal / score ベースの株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限・アグリゲート上限（available_cash）に応じたスケーリング、余りの分配ロジックを採用。
    - cost_buffer による保守的コスト見積りを考慮。

- 研究用モジュール（ファクター計算）
  - research/factor_research.py を追加（ファクター計算基盤）
    - DuckDB 接続を受け取り、モメンタム／Value／Volatility／Liquidity 等の指標を計算する設計。
    - モメンタム計算（1M/3M/6M、MA200 乖離など）等を実装する方針を反映。

Changed
- ログの標準化
  - 全起動スクリプトから setup_logging を呼び出すことでログ出力を統一。stdout とローテーティングファイルの二重出力を基本に設定。
- 起動時プロセス優先度
  - run_monitoring/run_execution の起動処理で最初に set_process_priority("high") を呼ぶようにし、CPU リソース確保を優先するようにした。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等を正しく処理するよう強化。
  - .env 自動ロードで OS 環境変数を保護するための override/protected の扱いを導入。

Notes / Known issues
- 一部の TODO / 注意点をコード中に記述
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）だとエクスポージャーが過少見積になる可能性があり、将来的にフォールバック価格（前日終値等）を導入する想定。
  - position_sizing は現段階で銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別単元対応の拡張を検討。
- research/factor_research.py はファクター計算の土台を提供（prices_daily / raw_financials を前提）。詳細なファクター実装とテストは今後の開発課題。

Environment / CLI summary
- 主な環境変数
  - KABUSYS_ENV (development | paper_trading | live)
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔上書き)
  - PAPER_FILL_MODE (paper_trading の fill モード: instant|partial|never|reject)
  - KILL_FLAG_CLEAR_ON_START (起動時の Kill Flag 自動クリア)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (.env 自動読み込みを無効化)

- 代表的な CLI
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.config_setup [--env-file PATH]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Acknowledgements
- 本リリースでは「初期機能群」を一通り実装し、実運用に向けた CLI、モニタリング、実行フロー、ポートフォリオ構築ロジックおよびユーティリティを揃えています。今後は単体テスト、統合テスト、ドキュメント補完、および細かなチューニング（手数料モデル、銘柄別単元、フォールバック価格処理など）を継続して進めます。