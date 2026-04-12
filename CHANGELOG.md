CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。
バージョニングは SemVer を想定しています。

Unreleased
----------

Added
- 全体
  - 新しいパッケージ初期実装を追加。自動売買システム "KabuSys" の各主要モジュールを収録。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db）および MockBrokerClient 経由で完全分離された動作を行う。
- 設定管理
  - config.py: 環境変数/.env 読み込みユーティリティを実装。プロジェクトルートの自動検出（.git または pyproject.toml）に基づいて .env / .env.local を自動ロード（OS 環境変数優先）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、各種設定（DB パス、PID ファイル、監視閾値、Paper Trading 用設定、ログレベル等）をプロパティ経由で取得可能にした。PAPER_FILL_MODE のバリデーション実装。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを追加。Windows / POSIX 間の差分を吸収し、権限不足や未対応プラットフォーム時に警告を出して安全にスキップする。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) の純粋関数を追加。スコアが全て 0 のとき等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を追加。unknown セクターはセクター上限の対象外にする等の挙動を定義。
  - portfolio/position_sizing.py: position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を使った保守的見積り、残差処理による lot 単位での追加配分を含む。
- 研究・リサーチ
  - research/factor_research.py: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER/ROE）等のファクター計算関数を DuckDB 接続を受け取る形で実装。
  - research/feature_exploration.py: 将来リターン計算、スピアマン IC（rankベース）実装、ファクター統計サマリを実装。pandas 等に依存せず標準ライブラリのみで実装。
- AI / ニュース
  - ai/news_nlp.py: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルへ書き込む処理を実装。バッチ処理、トークン肥大対策（記事数・文字数上限）、429/5xx/タイムアウト等に対する指数バックオフリトライ、レスポンスの厳密 JSON バリデーション、スコアの ±1.0 クリップを実装。API キーは引数または環境変数 OPENAI_API_KEY を使用。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する（閾値はファイル内定義）。--from/--to/--db オプションをサポート。

Changed
- DB 接続方針
  - run_monitoring.py: 監視用プロセスは環境に依らず本番 sqlite_path を使用する挙動を明示。
  - run_execution.py: Paper Trading 時は専用 DB を使用し、本番 DB と完全分離する方針を明確化（settings.is_paper による分岐）。
- .env ロードの優先順位を明確化: OS 環境 > .env.local > .env。既存 OS 環境変数は保護される実装（.env.local の override は OS 変数を上書きしない）。

Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line(): export 句、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォートなしでのコメント判定などを考慮して .env をより安全にパースするようにした。
- MONITOR_POLL_INTERVAL の検証強化
  - run_monitoring._get_poll_interval(): 0 以下や非整数の値を検出してデフォルト（60 秒）にフォールバックし、警告を出すようにした（time.sleep に渡す不正値による例外回避）。
- PAPER_FILL_MODE のバリデーションを追加
  - Settings.paper_fill_mode: 有効値 (instant|partial|never|reject) 以外は ValueError を発生させるようにした。
- process_priority の安全化
  - utils/process_priority.py: 未対応 OS や権限不足時に警告を出して操作をスキップするようにして、起動失敗のリスクを低減。

Performance
- research モジュール
  - DuckDB を活用して集計を SQL 側で可能な限り実行することで、大量銘柄のファクター計算を効率化（ウィンドウ関数を多用）。

Security
- OpenAI API キーの取り扱い
  - ai/news_nlp.score_news() は引数での api_key 指定を受け付けるとともに、環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させ、無設定での誤った API 呼び出しを防止。

Removed
- なし（初期導入段階のため該当なし）

v0.1.0 — 2026-04-12
-------------------

初回リリース。上記の機能群をパッケージとして公開。

Added
- 基本的なアーキテクチャとコア機能
  - 起動スクリプト: run_monitoring, run_execution
  - 設定管理: 自動 .env ロード、Settings
  - DB 初期化ヘルパ: monitoring_db 初期化フック（各スクリプトから呼び出し）
  - Execution/Order 関連基盤: BrokerFactory/ExecutionEngine/OrderManager/OrderRepository（起動ロジックからの組み立て実装）
  - ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算（単元丸め・aggregate cap 等）
  - リスク調整: セクター上限、レジーム乗数
  - 研究モジュール: ファクター計算（momentum/volatility/value）、特徴探索ユーティリティ（forward returns/IC/summary）
  - AI ニューススコアリング: OpenAI を用いたニュースセンチメント処理（バッチ・リトライ・検証）
  - 開発用ツール: Paper Trading 検証レポート生成
  - ユーティリティ: process priority / cpu affinity 設定
- ドキュメント的注記・設計コメントを各モジュールに追加（関数の振る舞い・前提・制約を明記）

Security
- 初期リリースにおける既知の注意点をドキュメント化（API キー管理、.env 自動ロードの無効化フラグなど）

Notes / 今後の課題（含む TODO）
- position_sizing: price 欠損時のフォールバック価格（前日終値や取得原価）を導入してエクスポージャー算出の精度を上げる予定。
- ai/news_nlp: 部分失敗時のトランザクション的置換戦略は基本実装済みだが、更なる堅牢化（失敗ログや再試行スケジュールの導入）を検討。
- research: 大規模データセットでのパフォーマンスチューニング、および追加ファクター（PBR、配当利回りなど）対応を予定。
- テストカバレッジ: 主要ロジック（ポートフォリオ算出、position sizing、AI パイプライン等）に対するユニットテストの拡充。

ライセンス
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください。

問い合わせ
- 不具合報告・改善提案は issue を作成してください。