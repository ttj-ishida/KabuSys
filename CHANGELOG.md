# CHANGELOG

すべての重要な変更点を記録します（Keep a Changelog 準拠）。  
フォーマット: 変更が大きい順に Added / Changed / Fixed / Security / ... を記載しています。

※本ファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

### Added
- 全体
  - パッケージの初期機能群を追加（自動売買システムのコア機能群）。
  - Python パッケージエントリポイントやモジュールを整備（kabusys パッケージ）。
- 実行 / 監視
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。実行に必要なコンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てとセッション起動を行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を利用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
- 設定 / 環境変数
  - config.py: 環境変数管理クラス Settings を実装。
    - .env 自動読み込み機能（プロジェクトルート探索: .git または pyproject.toml を基準）を追加。
    - .env 読み込みでは OS 環境変数を保護する仕組み（protected）を導入。.env.local を override=True で読み込む順序を採用。
    - 各種設定プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境種別判定等）。
    - PAPER_FILL_MODE の検証とデフォルト設定（"instant"）を実装。
    - env 値の検証（KABUSYS_ENV / LOG_LEVEL 等）。
- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群）。
    - portfolio_builder: 候補選定（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - position_sizing: 株数決定ロジック（calc_position_sizes）を追加。risk_based / equal / score の配分方式をサポートし、lot_size、max_position_pct、max_utilization、cost_buffer による調整・aggregate cap のスケールダウンを実装。
- 研究（Research）機能
  - research モジュールを追加。
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL＋Python 実装）。
    - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリーなど。外部ライブラリに依存しない実装。
    - zscore_normalize を data.stats から再エクスポートするインターフェースを提供。
- AI / ニュース
  - ai.news_nlp: raw_news の記事を OpenAI API（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込むロジックを追加。
    - タイムウィンドウ計算（JST → UTC 変換）と記事集約、銘柄ごとのトークン肥大対策、バッチ（最大 20 銘柄）での API 呼び出し、リトライ（429/ネットワーク/5xx 用の指数バックオフ）などを実装。
    - 出力バリデーション、スコアの ±1.0 クリッピング、部分更新（該当コードのみ DELETE → INSERT）での保護を実装。
    - score_news は api_key 引数または環境変数 OPENAI_API_KEY を使用する。未設定時は ValueError を送出。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等。
    - DB パスや期間指定の CLI オプション（--from/--to/--db）をサポート。
    - P95 の計算や日付フィルタリング、安全に DB が無い場合のメッセージを実装。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）での差分を吸収。psutil を利用して nice 値や HIGH_PRIORITY_CLASS を設定。
    - 例外（AccessDenied 等）を捕捉してフォールバックログを出す。

### Changed
- DB / 実行分離に関する設計
  - run_monitoring は監視用に常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用する設計を明確化。
  - run_execution は paper_trading 環境時に paper_sqlite_path（data/paper_trading.db）を使用して本番と完全分離するよう実装。
- .env 読み込みの優先順位を明記
  - OS 環境 > .env.local > .env の順で読み込む実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- logging の初期化
  - スクリプト単位で logging.basicConfig(level=logging.INFO) を呼ぶようにし、起動時にログレベルや環境を出力するようにした。

### Fixed
- 環境変数の取り扱いとバリデーション
  - _parse_env_line: export プレフィックスやクォート文字列、インラインエスケープ、コメントの取り扱いを改善し、より忠実に .env をパースする実装に。
  - _load_env_file: ファイル読み込み失敗時に warnings.warn を出すようにして堅牢化。
  - _require / Settings: 必須環境変数未設定時に明確な ValueError を投げるようにした。
  - PAPER_FILL_MODE の不正値検出とエラーメッセージ追加。
  - MONITOR_POLL_INTERVAL の不正値（0 以下・非整数等）を検知してデフォルトにフォールバックする安全策を追加（ログ出力あり）。
- process_priority 周りの堅牢化
  - set_process_priority / set_cpu_affinity でアクセス権限エラーなどを捕捉して警告ログを出すようにし、環境依存で失敗しても起動を継続するようにした。
- position_sizing の端数処理と aggregate cap
  - aggregate スケールダウン時に lot_size 単位での再配分と端数の安定的な処理（残差に基づく追加配分）、および max_per_stock の上限監視を追加してより保守的な発注数量決定を実装。
- research / factor 計算の NULL 安全性
  - calc_momentum / calc_volatility / calc_value でデータ不足時に None を返すようにし、NULL 伝播やウィンドウ内カウント検査による誤った値算出を防止。
- tools.paper_verification_report の耐障害性
  - 対象テーブルが存在しない場合の sqlite3.OperationalError をキャッチして N/A 表示にフォールバックするようにした。

### Security
- OpenAI API キーの扱いに関して、score_news は引数または環境変数のみを使用し、未設定時は明示的にエラーにすることで誤った公開を防止。

## [0.1.0] - 2026-04-13

初期リリース（ベース機能群）。
- パッケージバージョンを 0.1.0 としてリリース。
- 上記 Unreleased の機能群を含む（実行エンジン、監視、設定管理、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ツール類、ユーティリティ）。

---

使用上の注意（抜粋）
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や CWD が異なる場合に無視されることがあります。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は常に本番 sqlite_path を使用します。監視データを分離したい場合は sqlite_path を変更してください。
- run_execution は paper_trading 環境時に別 DB（PAPER_TRADING_SQLITE_PATH）を使用します。Paper 環境の検証では tools.paper_verification_report を利用してください。
- OpenAI の利用には環境変数 OPENAI_API_KEY の設定が必要です（score_news にてチェック）。

既知の改善ポイント / TODO（コード内注釈より）
- position_sizing: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）の導入検討。
- 将来的に lot_size を銘柄ごとに管理する拡張（stocks マスタの lot_size）。
- ai.news_nlp: API レスポンスの堅牢な検証・部分失敗時のリトライ戦略の更なる強化。

--- 

（この CHANGELOG は現行のコードベースから推測して作成しています。実際のコミット履歴や意図と異なる場合がありますので、正確な履歴は VCS のコミットログを参照してください。）