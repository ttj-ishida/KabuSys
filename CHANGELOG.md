# CHANGELOG

全ての重要な変更はここに記載します。形式は "Keep a Changelog" に準拠します。

なお、このリリースはソースコードから推測して作成した変更点の要約です。実際の変更履歴と差異がある場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本モジュール群を追加。
- 環境設定／管理
  - Settings クラス（kabusys.config）を導入し、環境変数から設定を取得・検証する API を提供。
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパース機能を強化：export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings が公開する主要設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（development / paper_trading / live）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（paper_trading 用の fill モード。instant/partial/never/reject の検証あり）
    - 各種監視閾値、PID / kill flag パス、LOG_LEVEL など
- 設定関連 CLI
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式で .env を作成・更新するウィザードを実装。デフォルト・既存値の取り込み、シークレットのマスク表示、保存確認をサポート。
  - 設定検証ツール（kabusys.validate_config）
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL の検証、DB パスや config/*.yaml の存在チェック、live 環境向けの追加ガードを実装。
    - --strict オプションで警告も失敗扱いにするオプションを追加。
    - PyYAML がインストールされていない場合は YAML の内容検証をスキップして警告を出力。
- 実行・監視プロセス起動スクリプト
  - run_execution（kabusys.run_execution）
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - stop フラグファイル（data/stop_requested.flag）の監視により安全停止を実装。
    - 実行中は execution.pid（data/execution.pid）を利用。
  - run_monitoring（kabusys.run_monitoring）
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下や不正値はデフォルトにフォールバックして警告）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、duckdb 接続も確立。監視は環境に関わらず本番 sqlite_path を使用する点に注意。
    - stop フラグ（data/stop_requested.flag）検知でループを終了。check_once() の例外はログ出力して次のポーリングまで継続。
- 監視 DB 初期化フック
  - init_monitoring_db 呼び出しを実装（冪等に監視テーブルを保証）。
- Execution コンポーネントの組立て
  - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み合わせて稼働可能に。
  - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 設定, max_drawdown など）を導入。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: シグナル並べ替え（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコア 0 の場合は等配分へフォールバック）を追加。
  - risk_adjustment: apply_sector_cap（セクター集中制限の除外ロジック。unknown セクターは上限適用対象外）、calc_regime_multiplier（regime に応じた投下資金乗数）。
  - position_sizing: calc_position_sizes を実装。allocation_method に応じた株数計算（risk_based / equal / score）、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）でのスケールダウン、cost_buffer による保守的見積り、残差の lot 単位分配ロジックを提供。
- リサーチ / ファクター計算（kabusys.research.factor_research）
  - DuckDB 接続を受け取り、prices_daily 等のテーブルからモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20）、流動性（20日平均売買代金、出来高比率）を計算する関数群を追加。計算時のデータ不足時は None を返す設計。
- ツール
  - paper_verification_report（kabusys.tools.paper_verification_report）
    - Paper Trading の SQLite DB から各種指標（稼働率、注文成功率、送信率、リスク却下、レイテンシ（avg/max/P95））を集計し、PASS/FAIL 判定付きのテキストレポートを生成。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - --from / --to / --db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数でも DB を指定可。
- ユーティリティ
  - utils.process_priority: set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。psutil を用い、Windows と POSIX を吸収。失敗時は警告ログでスキップ。

Changed
- n/a（初期リリースのため過去の変更は無し）

Fixed
- n/a（初期リリース）

Security
- n/a

Notes / Migration / 注意事項
- run_monitoring は「監視」に対して常に settings.sqlite_path（本番用）を使用します。環境変数 KABUSYS_ENV に関わらず監視 DB は本番パスを使う設計になっていますので、テスト時は注意してください。
- run_execution は paper_trading モード時に paper 専用 DB を使用して本番データと分離します。ペーパーモードでの発注は MockBroker により記録されます。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup の出力ヘッダに注意喚起あり）。
- MONITOR_POLL_INTERVAL は正の整数を指定してください。不正な値または 0/負値は 60 秒にフォールバックします（警告ログあり）。
- PAPER_FILL_MODE の有効値は instant / partial / never / reject のいずれかです。不正値は ValueError を発生させます。
- live 環境での実行時は LINE 通知トークン（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定に注意してください（validate_config で警告が出ます）。
- process priority / cpu affinity 設定は権限や OS に依存し、失敗すると警告を出してスキップします。

貢献・開発者向けメモ
- 主要なエントリポイント:
  - python -m kabusys.config_setup         （.env ウィザード）
  - python -m kabusys.validate_config     （設定検証）
  - python -m kabusys.run_execution       （ExecutionEngine 起動）
  - python -m kabusys.run_monitoring      （SystemMonitor 起動）
  - python -m kabusys.tools.paper_verification_report（Paper レポート生成）
- バージョンは kabusys.__version = "0.1.0" に設定。

--- 

（以降の変更はここに追記してください）