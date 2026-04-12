# Changelog

すべての変更は Keep a Changelog の形式に従います。  
タグ付けはセマンティックバージョニング (MAJOR.MINOR.PATCH) を採用しています。

現行日付: 2026-04-12

## [Unreleased]

### Added
- run モジュール
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading モード時は専用の MockBroker を利用し、データベースは paper_trading 用（デフォルト: data/paper_trading.db）に切り分ける。起動時にプロセス優先度を高く設定する処理を組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する。
- 設定管理
  - config.py: プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動ロード機能を追加（.env, .env.local 読み込み・優先度管理、OS 環境変数保護）。必須キー取得ユーティリティ `_require`、各種設定プロパティ（DBパス、PID ファイルパス、閾値、KABUSYS_ENV / LOG_LEVEL 検証など）を実装。PAPER_FILL_MODE のバリデーションを実装。
- 監視/ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows / POSIX(nice)対応）。CPU affinity を設定する set_cpu_affinity() も実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額・スコア加重配分の純粋関数を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジーム時はフォールバックの警告ロジックあり。
  - portfolio/position_sizing.py: 株数計算ロジックを実装（risk_based / equal / score の allocation_method、単元株丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り等）。
- 研究（Research）
  - research/factor_research.py: モメンタム / ボラティリティ / バリューのファクター計算を DuckDB に対する SQL + Python 実装で追加（MA200、ATR20、各ホライズンリターンなど）。データ不足時の None 扱い、内部ログ出力を実装。
  - research/feature_exploration.py: 将来リターン計算、Spearman（ランク）による IC 計算（calc_ic）、ランク生成ユーティリティ、ファクター統計サマリを追加。外部ライブラリ非依存で実装。
  - research/__init__.py: 公開関数をエクスポート。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。CLI (--from / --to / --db) により期間指定可能。稼働率・注文成功率・送信率・P95 レイテンシ 等を算出し、閾値判定（PASS/FAIL）を出力。デフォルト DB パスは data/paper_trading.db。
- AI / ニュース
  - ai/news_nlp.py: raw_news テーブルを集約し OpenAI API（gpt-4o-mini）で銘柄別センチメントスコアを取得する処理を追加。バッチ処理、トークン肥大化対策（記事数・文字数トリム）、API リトライ（指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）など、実運用を意識した設計を実装。ニュースウィンドウ計算ユーティリティ calc_news_window を提供。

### Changed
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定（初期バージョン）。
- DB ハンドリング
  - monitoring 周りの DB 初期化を冪等に行う（init_monitoring_db を起動時に呼び出す）ため、監視テーブルの存在を保証するように変更。
- run_* スクリプトの起動処理において、最初にプロセス優先度を設定するようにした（set_process_priority 呼び出しを起動直後に移動）。

### Fixed
- 環境変数のパースロジック強化
  - config._parse_env_line: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い、空行/コメント行の無視などを強化。これにより .env の柔軟な記述に対応。
- MONITOR_POLL_INTERVAL の取り扱い
  - run_monitoring: 環境変数からポーリング間隔を取得する際、0 以下や不正値はデフォルト（60秒）にフォールバックするようにして time.sleep での ValueError を回避。無効値時は警告ログを出力。

### Security
- OpenAI API キーの取り扱いで、引数 api_key が未指定か空文字列の場合は環境変数 OPENAI_API_KEY を参照し、未設定時は明示的に ValueError を送出するようにして誤使用を防止。

---

## [0.1.0] - 2026-04-12

初期リリース。以下の主要機能を含む最初の公開バージョン。

### Added
- 基本インフラ
  - Settings 設定管理（.env 自動ロード・環境変数検証・各種パス/閾値プロパティ）
  - プロジェクトルート検出ロジック（.git / pyproject.toml による）
  - __version__ = "0.1.0"

- 実行 / 監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - SystemMonitor ポーリングループ起動スクリプト（run_monitoring.py）
  - Process priority / CPU affinity ユーティリティ（utils/process_priority.py）

- 注文実行関連（Execution）
  - BrokerClientFactory を介したブローカークライアント切替（paper_trading モードの分離を想定）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと起動フロー（run_execution から実行）

- 監視データ基盤
  - monitoring_db 初期化処理を組み込み（監視用 sqlite DB の初期化）

- ポートフォリオ構築コンポーネント（純粋関数）
  - 候補選定、等金額 / スコア加重配分（portfolio_builder）
  - セクター上限適用、レジーム乗数（risk_adjustment）
  - 発注株数決定（risk_based / equal / score）、単元丸め、aggregate cap スケールダウン（position_sizing）

- 研究（Research）
  - momentum / volatility / value ファクター計算（DuckDB ベース）
  - forward returns（将来リターン）計算、IC（Spearman rank）計算、ファクター統計サマリ

- ツール
  - paper_verification_report.py: Paper Trading 検証レポート（稼働率 / 注文成功率 / レイテンシ等）を CLI で出力

- AI ニューススコアリング
  - raw_news 集約、OpenAI へのバッチ送信、レスポンス検証、ai_scores テーブルへの安全な書き込みのための処理（ai/news_nlp.py）

### Fixed / Known issues
- .env パーサーの改善により特殊文字列・クォート・エスケープに対する取り扱いを安定化。
- apply_sector_cap 内に TODO コメントあり: price が欠損（0.0）の場合のフォールバック価格未実装（潜在的にエクスポージャー過少見積りの可能性）。

### Documentation / Examples
- tools/paper_verification_report のヘルプ・使用例を CLI のヘルプコメントとして実装。

---

注記:
- monitoring は意図的に環境 (KABUSYS_ENV) に関わらず本番用 sqlite_path を参照する設計になっています。paper_trading 用の完全分離を期待する場合は run_execution の paper_trading 専用パス（PAPER_TRADING_SQLITE_PATH）を利用してください。
- 将来的な改善点として、position_sizing の lot_size を銘柄別に設定できるように stocks マスタから取得する拡張や、apply_sector_cap の価格フォールバック（前日終値等）を検討しています。