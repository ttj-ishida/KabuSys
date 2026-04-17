# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

現在のリリース:
- [Unreleased]
- [0.1.0] - 2026-04-17

---

## [Unreleased]

（将来の変更や修正をここに記載します）

---

## [0.1.0] - 2026-04-17

初回公開リリース。日本株自動売買システム "KabuSys" の基本コンポーネント群を実装しています。以下の主要機能・改善点を含みます。

### 追加（Added）
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時に MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定管理
  - config.py: .env/.env.local 自動ロード機能（プロジェクトルート検出）を追加。export 形式・引用符付き値・インラインコメント処理などをサポート。OS 環境変数を保護する仕組みを実装。
  - Settings クラスで各種環境変数をラップ（DB パス、paper_trading 用パス、PID/フラグパス、閾値、PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の検証など）。
- ポートフォリオ構築モジュール（純関数群）
  - portfolio.portfolio_builder: 候補選定（スコア順）・等金額／スコア加重の重み計算を実装。
  - portfolio.position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金に応じたスケーリング）、コストバッファ対応を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- Execution コンポーネント（基盤）
  - run_execution から起動される ExecutionEngine の組み立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、Reconciler など）を行うスクリプトを追加（設定の一例やデフォルトパラメータを含む）。
- 監視 / DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を利用して監視用テーブルの冪等初期化を行う仕組みを導入。
- ユーティリティ
  - utils.process_priority: Windows / POSIX の差を吸収するプロセス優先度設定ユーティリティ（set_process_priority、set_cpu_affinity）を追加。アクセス権限や未対応 OS の場合は安全にスキップしてログ出力。
- Research（調査用）モジュール
  - research.factor_research: Momentum / Volatility / Value のファクター計算関数（DuckDB を用いた SQL 実装）を追加。MA200、ATR20、各種リターン等を計算。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）・ランク関数・ファクター統計要約（factor_summary）を追加。外部ライブラリに依存せず純粋 Python 実装。
  - research.__init__: zscore_normalize（data.stats から）等を再エクスポート。
- AI / ニュース NLP
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルに書き込むためのパイプラインを実装。ターゲット時間窓計算、記事トリミング（件数・文字数上限）、バッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリッピング（±1.0）、部分失敗時の既存スコア保護（対象コードのみ置換）などを含む。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定する CLI（--from/--to/--db オプション対応）。
- パッケージ初期化情報
  - kabusys.__init__ にバージョン情報 __version__ = "0.1.0" を追加。

### 変更（Changed）
- DB 挙動・分離
  - 監視（run_monitoring）は環境にかかわらず本番の sqlite_path を使用する仕様に明示（監視データは本番 DB で一元管理する意図）。
  - run_execution は paper_trading 環境であれば paper_sqlite_path を使用することで本番 DB と完全分離。
- 環境変数読み込みの優先順位を OS 環境 > .env.local > .env に確立。OS 環境変数は保護され .env.local で上書き可能。

### 修正（Fixed）
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート付き値でのバックスラッシュエスケープ対応、インラインコメントの扱い（クォートあり/なしでの挙動差）を修正。
- run_monitoring のポーリング間隔取得で不正値（0 や負、非整数）を検出した場合にデフォルトへフォールバックし警告を出す実装を追加（time.sleep に渡される不正値による ValueError を予防）。
- process_priority と CPU affinity の失敗時には警告ログを出して処理を継続するようにし、例外でプロセスを終了しないように改善。

### 既知の注意点（Notes / Known issues）
- utils.process_priority: 権限不足（psutil.AccessDenied）や未サポート OS の場合は設定をスキップして警告ログを出します。運用環境では適切な権限確認が必要です。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に 0.0（欠損）を与えた場合にエクスポージャーが過小評価される可能性があり、将来的に前日終値や取得原価を用いたフォールバックを検討予定（TODO コメントあり）。
- position_sizing:
  - 現状は全銘柄共通の lot_size（デフォルト 100）で丸めを行う設計。将来的には銘柄別 lot_size を導入する余地あり（TODO コメントあり）。
- ai.news_nlp:
  - OpenAI API 利用のため OPENAI_API_KEY の設定が必須。API 呼び出しは課金対象・レート制限に注意。部分的な API 失敗は他銘柄のスコア保持に配慮して処理されます。
- research モジュールは DuckDB の prices_daily / raw_financials 等のスキーマに依存します。データの前処理・スキーマ整合は利用者側で準備してください。

### セキュリティ（Security）
- 外部 API キー（OpenAI 等）は環境変数経由で読み取る想定。秘密情報は .env に保存する場合は取り扱いに注意してください（リポジトリにコミットしないこと）。

---

メジャー / マイナー / パッチの観点では、本リリースは初期機能群の公開に相当します（0.1.0）。今後の変更では、AI スコア集約の堅牢化、単元株設定の拡張、価格フォールバックロジック、より詳細なモニタリング指標の追加などを予定しています。