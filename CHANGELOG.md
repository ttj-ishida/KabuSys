# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトの初回リリースとして、v0.1.0 を 2026-04-12 に公開しました。

全体方針: 明確な機能追加と内部実装（純関数群・DBアクセス・CLI 起動スクリプト・外部 API 統合など）を中心にまとめています。

※日付はソースコード解析時点の推定値です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils/process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - `_parse_env_line` による .env の堅牢なパース実装（export 句、クォート、インラインコメント等に対応）。
    - `_load_env_file` によるファイル読み込みと OS 環境変数の保護機構を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。
    - `Settings` クラスを実装し、環境変数の集中管理を提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログ等）。
    - `PAPER_FILL_MODE` の検証（"instant" | "partial" | "never" | "reject"）と `PAPER_TRADING_SQLITE_PATH` のサポート。
    - `KABUSYS_ENV` の有効値検証（development / paper_trading / live）・`LOG_LEVEL` の検証を実装。

- 監視関連
  - monitoring_db 初期化呼び出しを各起動スクリプトで行う（冪等に監視テーブルを確保）。
  - PID ファイル / KILL フラグの設定を Settings で管理。

- ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX（Linux/Darwin/FreeBSD）を吸収するプロセス優先度設定ユーティリティを実装。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。
    - 権限不足や未対応 OS 時は警告ログを出して安全にスキップする実装。

- Portfolio（ポートフォリオ構築）
  - portfolio.portfolio_builder
    - シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告を出す。
  - portfolio.risk_adjustment
    - セクター集中制限の適用（apply_sector_cap）を追加。既存保有のセクターエクスポージャを考慮して候補を除外。
    - レジーム乗数（calc_regime_multiplier）を追加（"bull":1.0、"neutral":0.7、"bear":0.3、未知はフォールバック1.0）。
  - portfolio.position_sizing
    - 株数決定ロジック（calc_position_sizes）を追加。
    - risk_based / equal / score の allocation_method に対応。
    - lot_size（単元）丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング。
    - 利用可能現金を超過した際のスケールダウンと残差処理（lot 単位で再配分）を実装。

- Research（リサーチ・ファクター計算）
  - research.factor_research
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクター計算を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - 欠損データ時の挙動（一定件数未満は None）や計算ウィンドウ（200日 MA 等）を定義。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計要約（factor_summary）を追加。
    - Pandas 等に依存せず標準ライブラリで実装。horizons の入力検証あり。
  - research パッケージ __init__ に主要関数をエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとの ai_score を ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、チャンク毎のリトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（対象コード絞って DELETE→INSERT）を設計。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を明確に計算するユーティリティを実装。
    - OpenAI API キーの取得（引数または環境変数 OPENAI_API_KEY）と未設定時の例外を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加（CLI 実行可能）。
    - 検証基準（稼働率・注文成功率・送信率・P95 レイテンシ等）の定義と閾値を追加。
    - system_status / trade_logs / risk_logs などのテーブルから指標を集計してレポートを標準出力に出力。
    - --from / --to / --db オプション対応。DB が存在しない場合のエラーメッセージを実装。

- DB 接続 / DuckDB
  - DuckDB 接続を多くの研究・AI モジュールで受け取る設計に統一。SQL を利用した高効率な集計処理を実装。

### Changed
- 設計方針の明記（ソース内 docstring）
  - 研究・ポートフォリオ・AI モジュールは副作用を避ける設計（DuckDB や与えられた引数以外へのアクセスを最小化）。
  - datetime.today()/date.today() の直接参照を避け、外部入力（target_date）で処理することでルックアヘッドバイアスを防止する実装を採用。

### Fixed
- 環境変数パースの堅牢化
  - .env のクォートやエスケープ、コメント扱いに対する細かなエッジケースを処理することで、ロード失敗や誤解釈を低減。

### Security
- 外部 API キー取り扱い
  - OpenAI API キーは引数経由または環境変数で取得。未設定時は明示的にエラーとなるため、意図しないクラウド呼び出しを防止。

---

## 既知の注意点 / 今後の改善候補（推定）
- position_sizing の price 欠損時（0.0）に関する注記が残っており、前日終値や取得原価などのフォールバック価格を使う拡張が想定されている。
- apply_sector_cap では "unknown" セクターは上限適用除外となるため、セクター未登録銘柄の扱いに注意が必要。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で動作しないことがあり、運用環境の確認が必要。
- ai/news_nlp の実行は OpenAI API の課金・レート制限の観点から運用面での考慮（バッチサイズやリトライ方針の調整）が必要。

---

参考: Keep a Changelog — https://keepachangelog.com/ja/（本 CHANGELOG は上記形式に準拠して作成しています）