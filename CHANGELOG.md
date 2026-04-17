# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載しています。  
（コードベースから推測して作成しています）

## [Unreleased]

## [0.1.0] - 2026-04-17
### Added
- 全体
  - 初回公開相当の実装を追加。モジュール構成は実運用向けの自動売買/研究/監視/ユーティリティ群をカバー。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止検知はプロジェクト直下の data/stop_requested.flag ファイルで行う。
    - Monitoring は KABUSYS_ENV にかかわらず production 相当の sqlite_path（監視 DB）を使用して起動する。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と完全分離して動作。
    - 停止フラグ、PID 管理、スレッドによる実行制御を実装。

- 設定/環境変数
  - config.Settings
    - .env / .env.local 自動ロード機能（プロジェクトルートの自動検出：.git または pyproject.toml 基準）。
    - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env 行パーサーを実装（コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープに対応）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別等）。
    - 値検証を行うプロパティを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の妥当性チェック）。
    - settings インスタンスをモジュールレベルで公開。

- 監視
  - monitoring モジュール初期化呼び出し（init_monitoring_db）を各起動スクリプトから行い、監視テーブルが存在することを保証（冪等）。

- Execution 関連
  - BrokerClientFactory を使ったブローカークライアントの生成をサポート。paper_trading モード時は MockBrokerClient を想定。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行可能に。
  - RiskManager に対するデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - ExecutionEngine はデイリーの target_date を使う EngineConfig をサポートし、PID ファイル管理・停止処理を実装。

- ポートフォリオ構築（portfolio）
  - portfolio_builder
    - select_candidates: スコア降順で候補選定、タイブレークは signal_rank。
    - calc_equal_weights, calc_score_weights: 等分配・スコア加重配分を実装。全スコアが 0 の場合は等分へのフォールバックと警告。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補除外。売却予定銘柄の除外や unknown セクターの扱いも明示。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出してフォールバック。
  - position_sizing
    - calc_position_sizes: risk_based / equal / score 各方式で発注株数を計算。lot_size 単位で丸め、per-stock および aggregate のキャップ/スケールダウンロジックを実装。
    - 手数料・スリッページ考慮用の cost_buffer、単元株丸め、available_cash に基づくスケーリングなどを実装。

- 研究用モジュール（research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上で計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新レポート取得ロジック）。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21 営業日）で将来リターンを一括取得。入力検証（ホライズン制約）あり。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を実装。サンプル数不足時は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計ユーティリティ。
    - rank: 同順位は平均ランクにするランク変換を実装（丸めによる ties 判定対策あり）。
  - research パッケージはデータ処理を DuckDB 上の SQL と純 Python で完結する設計（pandas 等外部依存なし）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成ツールを追加。
    - システム稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、P95 レイテンシ等を集計して標準出力へレポート出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定し、Pass/Fail 判定を行う。
    - コマンドライン引数で期間(from/to) と DB パスを指定可能。DB が存在しない場合はエラーメッセージを出力。

- AI / ニュース NLP（ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込む設計を追加。
  - 設計上の特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装。
    - 銘柄ごとに記事を集約し、1 銘柄あたりの記事数・文字数をトリム（max articles / max chars）。
    - 最大バッチサイズ・JSON Mode を使った API 呼び出し、429/5xx/ネットワーク断等に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コード絞り込み更新）などを想定した堅牢設計を実装。
    - OpenAI API キー未設定時は明示的なエラーを返す。

- ユーティリティ（utils）
  - process_priority
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）に対応してプロセス優先度を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め。引数検証と失敗時の警告を実装。

### Changed
- （初回リリース相当のため変更履歴はなし。各モジュールは設計方針・デフォルト値・バリデーションを明記して実装されています。）

### Fixed
- （初回リリース相当のため修正履歴はなし。）

### Security
- OpenAI API キー等の機密情報は Settings を経由して取得する設計。自動 .env ロード時も OS 環境変数を保護する仕組み（protected キー）を導入。

注記
- ai/news_nlp.py は設計・処理フローが詳細に記載されており堅牢化（バッチング／リトライ／検証）を意識した実装となっていますが、API 呼び出し周りや DB への最終書き込みロジック等は外部依存部分があるため、実運用前に API キー・テーブルスキーマ・実行環境での検証が必要です。
- Portfolio・Research モジュールは DuckDB / prices_daily / raw_financials 等の前提データが存在することを想定しており、データ欠損時のフォールバックやログ出力が組み込まれています。
- run_monitoring/run_execution は stop/kill フラグ・PID 管理・優先度設定など実運用運用を考慮した制御を実装しています。実行時は data ディレクトリの権限・パス・環境変数の確認を推奨します。

（以上）