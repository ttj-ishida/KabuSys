# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-13

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
- 実行エントリ
  - run_execution: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV により paper_trading モード時は専用の MockBroker と paper_trading 用 SQLite DB を使用する。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - Settings クラスを実装し、.env / .env.local / OS 環境変数から設定を読み込む自動ロード機能を提供。プロジェクトルート検出（.git または pyproject.toml）に基づく安全な自動ロード。
  - .env パーサを実装（コメント、export プレフィックス、クォートやエスケープ処理対応）。読み込み順序は OS 環境変数 > .env.local > .env。
  - 各種設定プロパティを提供（DB パス、PID / kill flag パス、paper trading 設定、しきい値など）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定（スコア降順、同点時 tie-breaker）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - risk_adjustment: セクター集中制限の適用（既存ポジションのセクター比率を計算して新規候補を除外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - position_sizing: 各銘柄の発注株数計算（risk_based / equal / score の allocation_method、単元株丸め、per-stock 上限・aggregate cap のスケーリング、コストバッファ考慮）。
- 研究・ファクター計算
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装。DuckDB の prices_daily / raw_financials を想定した SQL ベースの高速集計。
  - research.feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー。pandas 等に依存しない純標準ライブラリ実装。
  - research パッケージのエクスポート（zscore_normalize を含む）。
- AI ニューススコアリング
  - ai.news_nlp: raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得、ai_scores テーブルへ書き込む処理を実装。チャンク処理、最大記事・文字数トリム、スコアクリップ、API リトライ（指数バックオフ）などを実装。
  - ニュース収集ウィンドウ計算（JST 基準 → UTC 変換）を実装し、ルックアヘッドバイアス回避の設計を反映。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（P95）などを集計して PASS/FAIL 判定を出力。CLI オプション（--from/--to/--db）を提供。
- 監視データベース初期化
  - monitoring.monitoring_db.init_monitoring_db（実行前に監視テーブルが存在することを保証する冪等関数）を利用する仕組みを導入（execution と monitoring の両方で呼び出し）。
- プロセス制御ユーティリティ
  - utils.process_priority: Windows / POSIX（Linux/macOS/FreeBSD）を吸収するプロセス優先度設定と CPU affinity 設定を実装。権限不足や未対応 OS の場合は警告ログを出してフォールバック。

### Changed
- データベース設計方針
  - Paper Trading（KABUSYS_ENV=paper_trading）は本番データベースと完全分離されるよう paper_sqlite_path を採用。run_execution は環境に応じて専用 DB を使用。
- ログ・起動メッセージを整備して起動環境情報（KABUSYS_ENV）を出力するようにした。

### Fixed
- MONITOR_POLL_INTERVAL の解析時に不正値（0 以下や非整数）が与えられた場合にデフォルト値へフォールバックし、time.sleep での ValueError を回避する処理を追加。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合に等金額配分へフォールバックするようにして、ゼロ除算や不適切な重み付けを防止。
- position_sizing の aggregate cap スケーリングで端数処理時に単元株（lot_size）単位で再配分するアルゴリズムを実装し、投下資金超過時の安全な縮小を保証。
- .env ファイル読み込みにおいてファイルが読み込めない場合の警告を追加（warnings.warn）。

### Documentation / Notes
- モジュール docstring に設計方針・参照テーブル・前提を明記（研究モジュールは prices_daily / raw_financials のみ参照するなど）。
- 各処理は外部 API を直接叩かない設計が基本（research 系・portfolio 系は DB/メモリ内のみ）。AI スコアリングは明示的に OpenAI API キーが必要。

### Known limitations / TODO
- position_sizing: 価格が欠損（0.0）の場合のフォールバック価格未実装（TODO コメントあり）。
- 将来的に銘柄別単元（lot_size）を stocks マスタで扱う設計への拡張を想定。
- ai.news_nlp: OpenAI レスポンスの堅牢なバリデーションと部分失敗時のテーブル保護は実装方針としてあるが、実運用上の微調整（リトライ戦略のチューニング等）が必要。

---

（補足）本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリース履歴や日付・バージョンポリシーがある場合はそれに合わせて適宜修正してください。