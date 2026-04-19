# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本 CHANGELOG はソースコードの内容から機能追加・振る舞いを推測して作成しています。

## [Unreleased]

### Added
- 開発時点で把握されている未リリースの軽微な改善・ドキュメント修正（詳細は各コミット参照）。

### Known issues / TODO
- research.calc_momentum モジュールの実装が一部途切れている箇所が存在する（実装継続予定）。
- position_sizing / apply_sector_cap などにおける価格欠損時のフォールバックロジックは今後改善予定（TODO コメントあり）。

---

## [0.1.0] - Initial release

### Added
- パッケージ基盤
  - kabusys パッケージを導入。バージョンは `__version__ = "0.1.0"`。
  - パッケージ公開に向けた基本モジュール群を実装（portfolio / execution / monitoring / utils / config / tools / research 等のサブパッケージ）。

- 実行スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は環境変数 KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient 等で本番システムと分離。
    - 停止フラグや実行 PID 管理（data/execution.pid）をサポート。
    - ExecutionEngine を別スレッドで起動し、外部フラグで安全に停止可能。

- 設定・環境管理
  - config.Settings クラスを実装し、環境変数経由で各種設定（DB パス、API トークン、監視閾値、環境種別など）を取得可能に。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を検出し、`.env` と `.env.local` を読み込む。OS 環境変数は保護。
    - .env パーサは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
  - config_setup: 対話式 .env 作成ウィザードを実装。
    - 必須項目のプロンプト、シークレット項目のマスク、デフォルト値や選択肢の提示、保存（.env 書き込み）機能を提供。
  - validate_config: 起動前チェック CLI を実装。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があれば検証実施）、本番用ガード（LINE 通知設定や Kill Switch 設定の危険検出）を行う。
    - --strict オプションで警告をエラー扱いにできる。

- 監視・モニタリング
  - monitoring_db 初期化ユーティリティを導入（起動時に監視用テーブルが存在することを保証・冪等）。
  - SystemMonitor による単回チェック API（monitor.check_once()）を利用するポーリングループを実装。

- Execution / ブローカー抽象化
  - BrokerClientFactory により設定に応じた BrokerClient を生成（本番 / Mock を透過的に切り替え）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine 等の構成要素を組み立てて実行可能に。
  - RiskManager に対する初期設定（max_position_pct、max_utilization、rate_limit_per_sec 等）を定義し、初期ポートフォリオ現金をブローカーから取得して使用。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順に並べ上位 N を選定。
    - calc_equal_weights: 等金額配分ウェイト計算。
    - calc_score_weights: スコア正規化配分（全銘柄スコアが 0 の場合は等配分にフォールバックし警告出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づき投下資金乗数を返却（未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。lot_size（単元）で丸め、aggregate cap（available_cash）を超える場合はスケールダウンと余剰分の分配ロジックを実装。
    - cost_buffer（手数料・スリッページ推定）を考慮して保守的に試算。

- ユーティリティ
  - logging_setup:
    - ルートロガー設定ユーティリティ。コンソール出力は stdout（stderr ではない）を使用し、日次ローテーション（TimedRotatingFileHandler）でログファイルを保存。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - 既存ハンドラをクリーンに置換するため、再呼び出しでも二重登録を防止。
  - process_priority:
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（high/normal/low）を提供。実行スクリプトから起動直後に high に設定するよう使用。
    - set_cpu_affinity による CPU ピン固定機能も提供（未指定なら全コア）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計し検証レポートを標準出力に生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均/最大/P95）。
    - デフォルト閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）し、PASS/FAIL 判定を出力。
    - --from / --to で期間フィルタ、--db で DB パス指定可能。

- リサーチ
  - research.factor_research: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を設計。DuckDB による SQL + Python 組合せで prices_daily / raw_financials を参照して計算する方針を実装（calc_momentum の実装開始）。

### Changed
- ログ出力の標準化:
  - logging_setup で stdout を使用する方針を明示（cron/task scheduler 環境でのリダイレクト取り扱いを考慮）。
- DB 初期化の冪等性:
  - Execution 起動時に monitoring テーブルの初期化を行い、paper_trading モードでも監視テーブルが存在することを保証。

### Fixed
- .env パーサの堅牢化:
  - export PREFIX、クォート・エスケープ、インラインコメントの取り扱いなど、実運用で見かける .env 文法差を考慮して実装。

### Removed
- なし（初回リリース）。

### Security
- 環境変数の扱いに注意喚起（.env を絶対に Git にコミットしない旨の注記を config_setup の出力に追加）。

---

開発・運用に関する補足
- 本リリースは「本番（live）」「ペーパートレード（paper_trading）」「開発（development）」を明確に分離して設計されています。特に発注周り（BrokerClient）は環境で挙動を切り替え、DB も分離可能です。
- 一部モジュールに TODO コメントや改善余地が記載されています（価格のフォールバック、銘柄ごとの lot_size 対応、研究モジュールの完全実装など）。引き続き改善を推奨します。