CHANGELOG
=========

すべての注目すべき変更をこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注: 以下の変更履歴は、リポジトリ内のソースコードから実装内容を推測して作成しています。実際のコミット履歴に基づくものではありません。

Unreleased
----------

（現在のところなし）

0.1.0 - 2026-04-18
------------------

Added
- 基本パッケージの初期実装を追加
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し、MockBrokerClient を利用する設計をサポート。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag によるグレースフル停止を実装。
    - 起動時に実行優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下含む）はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨（注意点として設計に明示）。
- 設定・環境管理
  - config.py: Settings クラスを実装。環境変数の取得・検証ロジックを提供。  
    - 自動 .env 読み込み機構: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込む。OS 環境変数は保護され、.env.local は上書き可能。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視しきい値、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject" のみ許容）。
- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を作成/更新するツールを追加。シークレット項目のマスク表示、既存値の再利用、保存時の案内をサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）、本番時のガードチェックを実装。--strict オプションで警告を FAIL 扱いに変更。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 → 環境変数 LOG_LEVEL → デフォルト INFO。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度・CPU affinity を設定するユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）に対応し、権限エラー時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークに signal_rank を使用）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中の上限適用（既存保有のセクター比率が閾値を超える場合に新規候補を除外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マップ、未知のレジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に基づいて発注株数を計算するロジックを実装。  
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（スリッページ/手数料見積）考慮、残差配分アルゴリズムを搭載。
  - portfolio/__init__.py: 上記関数のエクスポートを提供。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite ログに基づく検証レポート生成ツールを追加。  
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出し、PASS/FAIL を判定する閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - 日付フィルタ、DB パス引数/環境変数サポート、出力フォーマットを実装。
- リサーチ（ファクター計算）の骨組み
  - research/factor_research.py: モメンタム、MA200 乖離、ATR、流動性等のファクター計算方針と一部実装下地を追加（DuckDB で prices_daily / raw_financials を参照する想定）。（注: ファイル末尾で未完の実装箇所あり）

Changed
- デフォルト設定とファイルパスを明確化
  - DuckDB デフォルト: data/kabusys.duckdb
  - SQLite 監視 DB デフォルト: data/monitoring.db
  - Paper Trading SQLite デフォルト: data/paper_trading.db
  - PID / フラグファイルのデフォルトパス（data/*.pid, data/stop_requested.flag など）を統一的に使用
- ログ出力は stdout をデフォルトに（stderr ではなく）。cron や Task Scheduler 等でのリダイレクト運用を想定。
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い、空行/コメント行のスキップ等。

Fixed
- 環境変数読み込みの保護動作を実装
  - OS 環境変数は .env によって意図せず上書きされないよう protected set を用いた読み込みを行う。
- DB 初期化の冪等性（監視テーブルの初期化を ensure する init_monitoring_db の呼び出し）を run_execution/run_monitoring 起動時に追加。

Security
- J-Quants と kabu API のシークレットは .env 対話ウィザードでシークレット扱い（画面表示はマスク）。ただし .env ファイルは「絶対に Git にコミットしない」旨の注意を明記。

Notes / Important points
- run_monitoring は「監視用途の DB として環境にかかわらず sqlite_path（本番パス）を使用する」実装です。テストやペーパートレード用に監視 DB を分離したい場合は運用上の注意が必要です。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し、本番 DB とペーパートレード DB を分離する設計になっています。
- Settings は KABUSYS_ENV の値を validation し、無効値は ValueError を送出します。起動前に validate_config を実行して設定を確認することを推奨します。
- process_priority/set_cpu_affinity は権限がない環境では警告を出してスキップする挙動です（安全性優先）。
- research/factor_research.py は計算方針と一部ロジックを含みますが、ファイル末尾に未実装の箇所が存在するため、本格運用前に実装完了・テストが必要です。
- Paper Trading 検証レポートはデータベースのスキーマに依存します（system_status / trade_logs / risk_logs 等）。DB スキーマが存在しない場合は該当クエリは安全に N/A を返すようになっています。

Acknowledgements / Recommendations
- 初回セットアップ手順:
  1. .env を作成（python -m kabusys.config_setup）
  2. 設定検証（python -m kabusys.validate_config）
  3. 実行/監視ログ用ディレクトリの確認（logs/）
  4. run_monitoring/run_execution を起動

以上。今後のリリースでは factor_research の完成、Strategy/Execution の具体的実装（Engine の詳細、Broker の具体実装）や自動テスト・CI の追加などを予定してください。