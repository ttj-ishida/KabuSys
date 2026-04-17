# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。
（非破壊的な内部実装や細かなリファクタリングは省略しています。）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-17
初回リリース。自動売買システム KabuSys のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止はプロジェクトデータ配下の stop_requested.flag ファイル検知で行う。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - Monitoring は環境（development/paper_trading/live）に関係なく本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用して完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 実行中は stop_requested.flag を監視し、検知時にエンジン停止を行う。PID ファイルの取り扱いあり。

- 設定管理
  - config.py
    - .env / .env.local による自動環境変数ロード（OS 環境変数が優先されるよう保護）。
    - プロジェクトルートを .git または pyproject.toml から検出するロジックを実装。
    - .env パーサは export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント等の扱いをサポート。
    - Settings クラスで各種設定（DB パス、Paper Trading 用設定、監視閾値、環境種別検証等）をプロパティとして提供。値検証（列挙値／数値変換）を導入。

- 監視・DB 初期化
  - monitoring_db の初期化処理を起動前に確実に行う（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコア全ゼロ時は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。既存保有を基にセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金によるスケール）、cost_buffer による保守的見積りを含む。
    - スケールダウン時は残差を考慮して lot 単位で追加割当てを行うロジックを実装。

- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を追加。
    - CPU affinity を設定する set_cpu_affinity を追加（core 数指定により最初の N コアに固定）。
    - 権限不足や未対応プラットフォーム時は安全にスキップして警告を出力。

- 研究・リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - Momentum, Volatility, Value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials を参照。
    - 長期 MA、ATR、出来高平均などの定量指標を SQL ウィンドウ関数で算出。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応）。
    - IC（Spearman ランク相関）計算 calc_ic、およびランク関数 rank。
    - ファクター統計サマリ factor_summary（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats から）を組み合わせて公開。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加（CLI）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計・判定を実施し、PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - P95 計算、欠測時の N/A 表示などを実装。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py（実装途中、主要ロジックを追加）
    - raw_news と news_symbols を集約し、OpenAI API（gpt-4o-mini + JSON Mode）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores に保存する設計を実装。
    - バッチサイズ、記事・文字数トリム制約、リトライ（指数バックオフ）、レスポンスバリデーション、スコアクリッピング等のポリシーを導入。
    - タイムウィンドウ計算（JST を基準に UTC に変換する calc_news_window）を実装。
    - API キー解決ロジック（引数優先→OPENAI_API_KEY 環境変数）を実装。
    - エラー時フェイルセーフ: API 失敗時はスキップして継続する方針。

- パッケージメタ
  - __init__.py にてパッケージ名・バージョン __version__ = "0.1.0" を設定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーを明示的に渡す/環境変数で管理する仕様とし、未設定時は早期に ValueError を投げることで不正使用を防止。

---

注意事項・既知の制約
- news_nlp.py は大きめの処理を含んでおり、コードの一部が続きで未表示の可能性があります（実装途中のコメントや処理フローがあります）。
- position_sizing の price 欠損時の挙動等、将来的な改善（フォールバック価格の導入）が TODO コメントとして残っています。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特殊な配置環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- プロセス優先度・CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告を出してスキップします。

貢献・バグ報告
- バグや改善提案は issue を作成してください。README やドキュメントに沿って環境変数・DB パス・依存ライブラリ（psutil, duckdb, openai など）を正しく設定のうえ実行してください。