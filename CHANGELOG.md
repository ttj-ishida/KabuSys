# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（今後の変更・追加予定を記述）

---

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能群を実装しました。以下は主な追加・仕様のポイントです。

### Added
- コア設定・起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag の存在で検知。
    - Monitoring は環境（KABUSYS_ENV）に関係なく production の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアントの抽象化（BrokerClientFactory）を利用し、RiskManager / OrderManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 停止は data/stop_requested.flag を監視、実行中は data/execution.pid に PID を書き込む想定（Engine による）。
    - スレッドでエンジンを実行し、安全に停止・待機するロジックを実装。

- 設定管理・検証・ウィザード
  - config.py: Settings クラスを実装。環境変数、.env/.env.local 自動読み込み機能を備える。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。
    - .env の読み込みルール:
      - OS 環境変数を保護（protected）し、.env.local は .env を上書きする。
      - export KEY=val 形式、クォートやエスケープ、行内コメントに対応したパーサ実装。
    - 各種設定プロパティ（DB パス、PID/kill フラグ、閾値、paper_trading 用パス/モードなど）を提供。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実施。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの存在警告、config/*.yaml 存在チェックと（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告を FAIL 扱いにできる。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。
    - J-Quants / kabu API 情報やログ/DB パス、KABUSYS_ENV などを対話的に入力して .env を生成・上書き。
    - シークレット項目はマスクして表示。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗してもコンソールだけで継続する耐性を持つ。デフォルト logs/、30 日分バックアップ。
    - LOG_LEVEL の解決順、LOG_DIR 指定対応。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）を設定するユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収。アクセス権限不足等は警告ログを出してスキップ。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクターの既存保有比率が上限（デフォルト 30%）を超える場合、新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームはフォールバック 1.0 として警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に基づく発注株数算出。
    - 単元株調整（lot_size）、1 銘柄上限、aggregate cap（available_cash を超える場合はスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した安全なサイズ割当。
    - risk_based では stop_loss_pct/risk_pct を使用したポジションサイズ算出。price 欠損時のスキップ挙動をログで記録。

- 監視・モニタリング関連
  - monitoring DB 初期化を行う関数（init_monitoring_db）を利用（実装ファイルは別）。
  - run_monitoring は SystemMonitor.check_once() を周期的に呼び出し、例外はログ出力の上でループ継続。

- Execution 周辺
  - Execution 側で RiskManager のデフォルト設定を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - BrokerClientFactory を使ったブローカ抽象化（paper_trading の MockBrokerClient を容易に差し替え可能）。

- ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加（DB を読み取り、稼働率・注文成功率・送信率・レイテンシ等を算出）。
    - CLI オプション: --from / --to（日付フィルタ）、--db（DB パス指定）。環境変数 PAPER_TRADING_SQLITE_PATH に対応。
    - デフォルト閾値（例: 稼働率 >= 99%、P95 レイテンシ <= 200ms）を用いた PASS/FAIL 判定を実装。
    - P95 はメモリベースで簡易算出。

- 研究 / ファクター計算（部分実装）
  - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）骨子を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計。モメンタム計算関数の雛形あり（未完の箇所あり）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### Changed
- （初回リリースのため変更履歴は無し）

### Fixed
- （初回リリースのため修正履歴は無し）

### Security
- （現時点で既知のセキュリティ修正は無し）

---

## 使用上の注意 / 既知の制約
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB として settings.sqlite_path（本番パス）を常に使用します。テスト目的で別 DB を使う場合は設定を上書きしてください。
- process_priority / cpu_affinity の設定は OS 権限に依存します。権限不足時は警告を出してスキップします。
- research/factor_research.py のモメンタム計算は実装途中の箇所があり、完全な計算ロジックは今後追加予定です（該当関数内に未完のコメントや TODO あり）。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）は現状未実装（TODO コメントあり）。

---

開発者向けの参考:
- ログ: デフォルトは logs/<app_name>.log、日次ローテーション・30日保管。
- 停止制御: data/stop_requested.flag ファイルを置くことで run_* スクリプトを安全に停止できます。
- Paper Trading: KABUSYS_ENV=paper_trading を設定すると実トレードと分離された DB に記録されます。

今後の予定:
- research/factor_research の完全実装（各ファクター計算の完成）
- テストケースの追加（unit/integration）
- CI/CD、パッケージ化、ドキュメント整備（API リファレンス・デプロイ手順）

[0.1.0]: 0.1.0