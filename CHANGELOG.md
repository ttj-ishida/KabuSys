CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠しています。
リリース日付は提供されたコードベースの最終更新日を基に記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-21
--------------------

Added
- 全体
  - 初回リリース。日本株自動売買システム "KabuSys" の基本コア機能を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - ブローカークライアント生成（BrokerClientFactory）／OrderRepository／OrderManager／RiskManager／Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）を検知して安全停止する仕組みを実装。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行い SystemMonitor.check_once() をポーリング実行。停止フラグで終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視は常に本番 DB を確認する方針）。

- 設定・CLI
  - config: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）を実装し、.env/.env.local を自動ロード（OS 環境変数を保護して上書き制御）。
    - .env の自動ロードを無効にするための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 各種設定プロパティを提供（DB パス、PID/kill フラグ、閾値、env 判定、paper_trading 関連など）。
    - `PAPER_FILL_MODE` の入力検証（有効値: instant|partial|never|reject）。
  - config_setup: 対話式 .env 作成・更新ウィザードを追加。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を対話的に設定し .env を生成。
    - シークレット項目はマスク表示、選択肢/デフォルト提示、既存 .env の読み込み対応。
  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用、ファイル出力は日次ローテーション（TimedRotatingFileHandler）・30日保持。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル／ログディレクトリは引数→環境変数→デフォルトの順で解決。
  - utils.process_priority: プロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応。`set_process_priority("high"|"normal"|"low")` と `set_cpu_affinity(n)` を提供。
    - psutil の API 呼び出し失敗時は警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder:
    - 銘柄選定（select_candidates）・等金額／スコア加重重み算出（calc_equal_weights / calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出力。
  - portfolio.risk_adjustment:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャを計算して上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。不明レジームは 1.0 でフォールバックし警告を出力。
  - portfolio.position_sizing:
    - 各銘柄の発注株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ）を考慮したスケールダウンロジックを実装。
    - スケーリング後は端数を lot_size 単位で再配分するアルゴリズムを実装。
    - price が取得できない場合はスキップする旨のログ出力あり。将来的な価格フォールバックは TODO コメントで記載。

- リサーチ
  - research.factor_research: ファクター計算モジュールを追加（モメンタム / Value / Volatility / Liquidity 計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計（関数は date, code ベースの dict を返す想定）。
    - ファイルはモメンタム計算関数のヘッダまで実装が確認できる（ファイル末尾は提供コードで途中切れ）。

- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成 CLI を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定する。
    - デフォルトの合格閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して出力。

Changed
- なし（初回リリースのため変更履歴はなし）。

Fixed
- なし（初回リリースのため修正履歴はなし）。

Deprecated
- なし。

Removed
- なし。

Security
- 設定ウィザードおよび .env 書き込みでシークレット項目はマスク表示する等、秘匿に配慮した設計。

Notes / Caveats / TODO
- research.factor_research のファイル末尾が提供コードで途中までしか含まれておらず、関数実装が未完の可能性あり（今後の実装継続が必要）。
- position_sizing や risk_adjustment 内に価格欠損時のフォールバックについて TODO コメントあり（前日終値や取得原価を用いる等の拡張を想定）。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や特定配置環境では自動ロードがスキップされる場合がある。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用可。
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。運用上の意図に沿わない場合は注意。

参考
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/