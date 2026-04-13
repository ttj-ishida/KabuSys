# Changelog

すべての項目は Keep a Changelog（https://keepachangelog.com/ja/）に準拠して記載しています。

※ 以下の変更履歴はリポジトリ内のソースコードを解析して推測した内容です（コミット履歴ではありません）。

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションパッケージを追加
  - kabusys パッケージの基本情報（__version__ = 0.1.0）。
- 実行用エントリポイント
  - run_execution.py：ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の run_session 起動を実装。
    - 起動時にプロセス優先度を "high" に設定。
- 監視用エントリポイント
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py：環境変数および .env / .env.local 自動読み込みロジックを追加。  
    - プロジェクトルートを .git / pyproject.toml から探索して .env を読み込む仕組み。  
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - .env パーサーは export 形式やクォート／エスケープ、行末コメント等に対応。  
    - Settings クラスに多数のプロパティを定義（DB パス、API トークン、環境判定、paper_trading 関連設定、監視しきい値等）と検証（有効値チェック、必須チェック）。
- ユーティリティ
  - utils/process_priority.py：クロスプラットフォームのプロセス優先度設定ユーティリティを追加。  
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応。nice() を用いる実装。  
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。  
    - アクセス権限不足等の失敗は警告ログでスキップする安全設計。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder：銘柄選定（select_candidates）・重み計算（calc_equal_weights / calc_score_weights）を実装。  
    - スコアが全て 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment：セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。  
    - セクター未登録コードは "unknown" 扱いで上限の対象外。未知レジームは警告のうえフォールバック。
  - portfolio.position_sizing：発注株数計算（calc_position_sizes）を実装。  
    - risk_based / equal / score の配分方式に対応。単元株（lot_size）、コストバッファ、per-position/aggregate 上限、スケールダウンロジック（残差処理含む）を実装。
- 研究／ファクター計算
  - research.factor_research：モメンタム・ボラティリティ・バリュー等のファクター計算関数を追加（DuckDB を用いた SQL 実装）。  
    - calc_momentum, calc_volatility, calc_value を提供。各関数は target_date を受け取り prices_daily / raw_financials を参照して結果を返す。
  - research.feature_exploration：将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクターサマリ（factor_summary）、ランク付け（rank）を追加。  
    - 外部ライブラリに依存せず標準ライブラリのみで統計処理を実装。
  - research.__init__ で zscore_normalize（data.stats）とファクター関数を公開。
- ニュース NLP（AI スコアリング）
  - ai.news_nlp：raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込む処理を追加。  
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC 変換）を提供（calc_news_window）。  
    - 銘柄ごとに記事を集約、チャンク毎に最大 20 銘柄で API コール、JSON Mode の厳密なレスポンス検証、スコアの ±1.0 クリップ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を想定。  
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
- ツール
  - tools.paper_verification_report：Paper Trading 用の検証レポート生成スクリプトを追加。  
    - SQLite（paper_trading.db）を読み、システム稼働率・注文成功率・送信率・レイテンシ（P95 等）・リスク却下数を算出し PASS/FAIL 判定を行う。  
    - CLI 引数で from/to 日付や DB パスを指定可能。しきい値（稼働率 99% など）はスクリプト内定義。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの冪等な初期化を実施（run_* スクリプトから利用）。

### Changed
- なし（初期リリースのため該当なし）

### Fixed
- なし（初期リリースのため該当なし）
  - ただし各モジュールで入力検証・例外処理・ログ出力を充実させ、失敗時に安全に継続する設計を採用（例: .env 読み込み失敗時の警告、process_priority の権限不足処理、DuckDB/SQLite のテーブル未存在時のハンドリングなど）。

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で指定する設計。ソース内でのハードコーディングは行っていない。

---

今後のリリースで想定される改善点（コードから推測）
- ai.news_nlp の完全実装（_fetch_articles / _score_chunk 等の補完）、および API エラー時の部分書き戻し戦略の詳細実装。
- 各モジュールに対するユニットテスト追加と CI 統合。
- position_sizing の lot_size を銘柄別に持たせる拡張（stocks マスタの導入）。
- .env パーサーのさらなる堅牢化（より複雑なエスケープ/改行/multi-line 値対応）とドキュメント整備。