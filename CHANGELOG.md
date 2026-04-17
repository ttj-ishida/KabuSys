# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
慣例: 変更は大まかに Added / Changed / Fixed / Deprecated / Removed / Security に分類しています。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 実行 / 監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、紙トレ用 DB 分離、Broker クライアント生成、依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）組み立て、別スレッドでのエンジン実行と停止フラグ監視を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出時の安全終了処理を実装。

- 設定管理
  - config.Settings: 環境変数ベースの設定管理を追加。
    - .env/.env.local の自動読み込み（プロジェクトルート検出）機能を実装。読み込みの優先度は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメントの扱いをサポート。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定など）。
    - PAPER_FILL_MODE のバリデーションと PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定をサポート。

- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートし tie-breaker（signal_rank）で整列する関数を追加。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバック（警告出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用する純関数を追加。既存保有のセクター別エクスポージャ計算、上限超過セクターの候補除外を実装。unknown セクターは上限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知の値は警告の上 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数計算を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer による保守的見積り、価格欠損時のスキップ等を含む。

- 研究（Research）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB を用いたファクター計算関数を追加。ウィンドウ関数を活用し、データ不足時の None 処理を行う。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（営業日）先の将来リターンを算出。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - factor_summary / rank: ファクター統計サマリーとランク変換ユーティリティを追加。
  - research パッケージは zscore_normalize（kabusys.data.stats から供給）を公開する。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成コマンドラインツールを追加。
    - DB からシステム稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数等を集計して人間向けレポートを標準出力に出力。
    - CLI オプション --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能。
    - P95 算出ユーティリティ、各指標の閾値（稼働率 99% 等）と PASS/FAIL 判定を実装。DB テーブルが存在しない場合に安全に扱う（OperationalError を捕捉しデフォルト値を使用）。

- AI / ニュース
  - ai.news_nlp:
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に格納するための設計と初期実装（ウィンドウ計算、バッチ処理方針、スコアクリップ、リトライ方針、プロンプト定義など）を追加。
    - calc_news_window と score_news の API キー解決・ウィンドウ計算・記事集約フェーズまで実装（ファイル末尾で実装が途切れているため未完の箇所あり）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定するユーティリティを追加。権限不足等の失敗を警告して安全にスキップ。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定機能を追加。引数検証あり。

### Changed
- （初版のため変更履歴はなし）

### Fixed
- （初版のため修正履歴はなし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キー等の機密値は環境変数から取得する設計とし、score_news は API キー未設定時に ValueError を投げることで明示的に失敗するようになっています。

---

注記:
- monitoring / execution の停止制御はファイルベースのフラグ（data/stop_requested.flag）で行われます。運用時は当該ファイルの管理に注意してください。
- ai/news_nlp モジュールは大きな機能を含みますが、ソース末尾で実装が途切れているため本番運用には追加実装・テストが必要です。
- DuckDB / SQLite を併用する設計になっており、paper_trading と本番 DB は分離されています（paper_trading 用 DB: data/paper_trading.db がデフォルト）。
- .env の自動ロードはプロジェクトルート判定を行うため、パッケージ化後も CWD に依存せずに動作する設計になっています。必要に応じて自動ロードを無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD）。