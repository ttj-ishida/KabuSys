# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
（注: 以下は提示されたコードベースの内容から機能追加・修正点を推測してまとめたものであり、実際のコミット履歴とは厳密に一致しない可能性があります。）

## [Unreleased]

### Added
- ドキュメント的な補助・ユーティリティを追加
  - パッケージのバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - tools モジュールに Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。期間指定やDBパス指定 (--from / --to / --db) に対応し、稼働率・注文成功率・送信率・レイテンシ（P95）などを算出して PASS/FAIL 判定を出力する。

- AI ニューススコアリング基盤を追加
  - news_nlp モジュールを追加（kabusys.ai.news_nlp）。OpenAI（gpt-4o-mini）を利用したニュースのセンチメントスコアリング機能を実装。バッチ処理、最大トークン対策、429/5xx/タイムアウト等のリトライ（指数バックオフ）、結果検証、±1.0 のクリップ、部分更新（対象銘柄のみの置換）などの設計方針を取り入れている。

- 研究・ファクター計算機能を追加
  - research.factor_research にて Momentum / Volatility / Value ファクターを DuckDB 上の prices_daily / raw_financials テーブルから計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
  - research.feature_exploration にて将来リターン計算、IC（Spearman ランク相関）や統計サマリー等を提供（calc_forward_returns, calc_ic, factor_summary, rank）。
  - research パッケージの公開 API を整理（zscore_normalize の re-export 等）。

- ポートフォリオ構築ロジックを追加
  - portfolio.portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等配分にフォールバックする警告を出す。
  - portfolio.risk_adjustment: セクター集中率制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。未知レジームはフォールバック（1.0）して警告を出す。
  - portfolio.position_sizing: 発注株数算出ロジック（risk_based / equal / score）。単元（lot_size）丸め、銘柄別上限、aggregate cap（利用可能現金を超える場合のスケールダウン）と残差分の再配分を実装。手数料・スリッページ見積り用の cost_buffer を考慮。

- 実行・監視起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（settings.paper_sqlite_path）を使用して本番データと分離。BrokerClientFactory によるブローカー抽象化、デフォルト RiskConfig、ExecutionEngine のスレッド実行と停止フラグによる安全停止処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。

- 設定と .env 自動読み込みの強化
  - config.Settings を追加し、環境変数から各種設定を取得する統一インタフェースを提供。KABUSYS_ENV/LOG_LEVEL のバリデーションや paper_trading 周りの設定（PAPER_FILL_MODE/PAPER_TRADING_SQLITE_PATH）を実装。
  - .env / .env.local の自動ロードを実装（プロジェクトルート検出は .git または pyproject.toml を基準）。export プレフィックス・引用符付き値・インラインコメント等に対応するパーサを実装し、OS 環境変数を保護する仕組みを導入。

- 汎用ユーティリティを追加
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）。Windows / POSIX の差分吸収と権限不足時のフォールバック（警告）対応。

### Changed
- DB 初期化・接続の一貫性
  - run_execution/run_monitoring 内で monitoring テーブルの初期化（init_monitoring_db）を起動時に行うようにして冪等性を確保。

- ログ・挙動の保守性向上
  - 環境変数の不正値・未設定時に明示的な警告や例外を出すよう調整（例: MONITOR_POLL_INTERVAL の不正値でログ警告してデフォルトにフォールバック、PAPER_FILL_MODE の不正値で ValueError）。

### Fixed
- env ファイルパーサの堅牢化
  - export プレフィックスや引用符中のエスケープ、インラインコメントの扱いなどを考慮して .env のパースを改善。既存の OS 環境変数を保護して上書き制御を可能に。

- ポジションサイズ算出の挙動改善
  - aggregate cap 適用時に lot_size 単位での丸め・端数の扱い、残余キャッシュを利用した再配分ロジックを追加してより安定した配分を実現。また price が欠損している銘柄はスキップしログ出力。

- 監視ループの堅牢化
  - monitor.check_once() の例外を個別にキャッチしてログを残し、次のポーリングへ継続するようにしてサービス継続性を向上。

### Security
- OpenAI API キーの必須チェックを追加（news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY が未設定だと ValueError を送出）。

## [0.1.0] - 2026-04-17

初回公開相当のリリース（推測）。上記の主要機能を含む。

### Added
- 初期アーキテクチャとコア機能
  - 基本パッケージ構成（kabusys パッケージ）。
  - コンフィグ管理（.env 自動ロード、Settings クラス）。
  - 実行・監視用スクリプト（run_execution.py, run_monitoring.py）。
  - DuckDB / SQLite を使用したデータアクセス基盤の利用（各種 research / ai / tools が DuckDB/SQLite を参照）。
  - ExecutionEngine 周りの骨格（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の起動フロー）。
  - 監視テーブル初期化ユーティリティ（monitoring_db.init_monitoring_db の呼び出しを起動部に組み込み）。
  - Portfolio 構築ロジック（選定、重み付け、リスク調整、ポジションサイジング）。
  - Research（ファクター計算、将来リターン、IC、統計サマリー）。
  - Paper Trading の分離運用（paper_trading 専用 SQLite をサポート）。
  - ユーティリティ（プロセス優先度、CPU affinity）。
  - Paper Trading 検証レポートツール。
  - ニュース NLP スコアリングの基盤（OpenAI 連携の骨格実装）。

### Changed
- デフォルト値や閾値の定義（監視・リスク管理・レポート基準値等）をコード内に明示。

### Fixed
- （初期版のため既知の TODO や注意事項が散見される。詳細はソース内コメント参照）
  - 価格欠損時のフォールバックロジックは TODO（前日終値や取得原価などを将来的に検討）。

## Notes / Known limitations
- ai/news_nlp.py は堅牢な設計（リトライ・バッチ・検証）を取り入れているが、API の実運用におけるレート制御やコスト管理は環境依存のため注意が必要。
- position_sizing の lot_size は現状グローバル固定（100）を想定している。将来的には銘柄別 lot_map の導入を想定した TODO コメントあり。
- apply_sector_cap は "unknown" セクターを制限対象外とする設計になっているため、マスタの未整備な銘柄に対する挙動に注意。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる。

---

（この CHANGELOG はコードから読み取れる設計意図・機能を元に作成した推測的な変更履歴です。コミット履歴やリリースノートが存在する場合はそちらを正としてください。）