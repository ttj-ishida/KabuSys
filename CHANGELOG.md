# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベース（src/ 以下）の内容から推測して作成したリリースノートです。

フォーマット:
- 変更はセクション毎に分類（Added, Changed, Fixed, Removed, Deprecated, Security）
- バージョン/日付はパッケージの __version__（src/kabusys/__init__.py）および現在の推定日付を使用しています。

## [Unreleased]

（現在のスナップショット時点で未リリースの差分はありません）

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ初期リリース。
- 実行・監視用エントリポイントを追加:
  - run_execution.py — ExecutionEngine の起動スクリプトを提供。Broker クライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler を組み立て、実行セッションを開始するワークフローを実装。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能。
- 設定・環境変数管理:
  - config.py — .env 自動読み込み（.env, .env.local、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）、環境変数の堅牢なパース、設定取得用 Settings クラスを追加。
  - Settings による多くの設定プロパティ（DB パス、PID/kill フラグ、閾値、env/log_level のバリデーション、paper trading 関連設定など）を実装。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額/スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 各銘柄の発注株数決定ロジック（risk_based / equal / score）、単元（lot）丸め、aggregate cap によるスケーリング、コストバッファ考慮。
  - portfolio パッケージの __all__ エクスポートを提供。
- リサーチ / 特徴量モジュール:
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた prices_daily / raw_financials 参照）。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、rank, factor_summary 等の統計ユーティリティ。
  - research.__init__ で zscore_normalize を再エクスポート。
- AI ニュース NLP:
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント分析して ai_scores に書き込むスコアリング処理を実装。バッチ処理、文字数・記事数のトリム、リトライ（429/ネットワーク/5xx/タイムアウトに対する指数バックオフ）、レスポンス検証、スコアクリッピングを備える。ニュース収集ウィンドウ（JST→UTC 変換）ユーティリティを提供。
- ツール:
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプト。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。
- ユーティリティ:
  - utils.process_priority: プロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値を吸収）、CPU affinity 設定ユーティリティ（set_cpu_affinity）。両 API のアクセス拒否や未実装へのフォールバック処理あり。

### Changed
- 実行/監視プロセスの起動時にプロセス優先度を "high" に上げる処理を追加（run_execution.py, run_monitoring.py）。
- run_execution は paper_trading 環境を分離して専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用するように実装。監視 (run_monitoring) は環境にかかわらず production 用 sqlite_path を使用する旨を明記。
- config.py の .env ロード:
  - プロジェクトルートを .git または pyproject.toml から探索する実装に変更。これにより CWD に依存しない自動ロードが可能。
  - .env のパースを堅牢化（export プレフィックス、クォート付き文字列のバックスラッシュエスケープ、インラインコメントルール等）。
  - .env.local は .env を上書き（override=True）する仕様。OS 環境変数は protected として上書きされない。
- position_sizing の配分アルゴリズム:
  - aggregate cap が available_cash を超えた場合のスケールダウン時に lot_size 単位で再配分する実装を追加。残差扱いの安定化ロジック（fractional remainder に基づく追加割当）を導入。
- research / feature_exploration:
  - calc_forward_returns はホライズンの妥当性チェック（正整数かつ 252 以下）、1 クエリで複数ホライズンを取得する最適化を導入。
- ai.news_nlp:
  - OpenAI クライアント生成時に api_key の引数優先 → 環境変数 OPENAI_API_KEY の順で解決。キー未設定時は明示的な ValueError を送出。
  - 処理のフェイルセーフ化（API エラー時は部分スキップして継続、書き込みは対象コードに限定して既存データ保護）。

### Fixed
- config._parse_env_line のクォート付き値処理でバックスラッシュエスケープを正しく扱うように修正（.env 内の引用符/エスケープに対応）。
- factor_research / calc_momentum 等でウィンドウ不足時に None を返す取り扱いを明確化（データ不足時の NULL 伝播制御）。
- volatility の true_range 計算で high/low/prev_close のいずれかが NULL の場合に true_range を NULL にして行数カウントを正しく扱う修正（ATR 計算の過大評価回避）。

### Removed
- なし（初期リリース）

### Deprecated
- なし

### Security
- なし特記事項

---

注記:
- 本 CHANGELOG はコードから推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
- バージョン番号は src/kabusys/__init__.py の __version__ (0.1.0) に基づいています。