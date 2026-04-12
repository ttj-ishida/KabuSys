CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

現在日付: 2026-04-12

Unreleased
----------

Added
- run_monitoring 起動スクリプトを追加。
  - SystemMonitor のポーリングループを起動するエントリポイント。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用して接続する実装。
  - プロセス優先度を起動時に "high" に設定（utils.process_priority.set_process_priority）。
- run_execution 起動スクリプトを追加。
  - ExecutionEngine を組み立ててセッションを実行するエントリポイント。
  - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
  - BrokerClientFactory 経由でブローカークライアントを抽象化。
  - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動するフローを実装。
  - プロセス優先度を起動時に "high" に設定。
- 環境設定管理モジュール (kabusys.config) を実装。
  - .env/.env.local の自動読み込み（プロジェクトルートの検出に .git / pyproject.toml を使用）。
  - export 形式やクォート・エスケープ、インラインコメントの考慮などを行う堅牢な .env パーサ実装。
  - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/KILL フラグ、閾値など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights。
  - risk_adjustment: セクター制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマップ）。
  - position_sizing: 株数決定 calc_position_sizes（risk_based / equal / score、lot 単位丸め、aggregate cap、cost_buffer 対応）。
  - 全て純粋関数でメモリ内計算（DB に依存しない）。
- 研究系モジュールを追加（kabusys.research）。
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（DuckDB を使用して prices_daily/raw_financials を集計）。
  - feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic、ファクター統計 factor_summary、ランク付け rank。
  - zscore_normalize を data.stats から公開。
- AI ニュース NLP スコアリング (kabusys.ai.news_nlp) を追加（OpenAI 利用）。
  - 指定ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を対象に raw_news を集約し、銘柄ごとにセンチメントを -1.0〜1.0 でスコアリングして ai_scores に書き込む処理を実装。
  - バッチ（最大 20 銘柄）で OpenAI に送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップを行う。
  - 実装はフェイルセーフ（API 失敗時はスキップして継続）を意識。
- utils/process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
  - Windows / POSIX（Linux/Mac/FreeBSD）に対応。権限不足時は警告でスキップ。
- tools/paper_verification_report CLI を追加。
  - Paper Trading 用 SQLite を解析して稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定を出力。
  - P95 計算、閾値（稼働率 99%、注文成功率 90% 等）および期間フィルタ(--from/--to) をサポート。
- パッケージ初期化情報を追加（kabusys.__init__.__version__ = "0.1.0"）。

Changed
- なし（Unreleased に含まれる新規機能の追加が中心）。

Fixed
- なし（現時点では既知のバグ修正は無し）。

Security
- OpenAI API キー未設定時に明示的に例外を投げるようにして誤動作を防止（news_nlp）。

0.1.0 - 2026-04-12
-----------------

Added
- 初期リリース。
  - コア機能: ExecutionEngine 起動スクリプト、Monitoring 起動スクリプト、環境設定ロード、プロセス優先度設定ユーティリティ。
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）。
  - 研究用モジュール（モメンタム/ボラティリティ/バリューのファクター計算、将来リターン・IC・統計サマリ）。
  - AI ニューススコアリングの初期実装（OpenAI を用いた記事集約・スコアリング・DB 書き込み）。
  - Paper Trading 用検証レポート生成ツール（コマンドライン）。
  - DuckDB と SQLite を併用して分析とトラッキングを分離するデータ設計。
  - .env 自動読み込みと堅牢なパーサー。
  - ドキュメントやコード内コメントによる設計指針（PortfolioConstruction.md, StrategyModel.md 等への参照）。

Changed
- なし（初版のため変更履歴はありません）。

Fixed
- なし。

Breaking Changes
- なし。

Notes / Implementation details (抜粋)
- run_execution は KABUSYS_ENV が paper_trading の場合、paper 用 SQLite を使用して本番 DB と完全分離する設計。
- run_monitoring は環境にかかわらず「本番 sqlite_path」を使用して監視データを格納する方針（本番監視が常に有効であることを想定）。
- .env のロード順は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- position_sizing の allocation_method は "risk_based"（損失許容率に基づく）と "equal"/"score" をサポート。単元株（lot_size）、コストバッファ、aggregate cap に対応。
- research モジュールは DuckDB のウィンドウ関数を積極利用して効率的に計算する実装。
- news_nlp は OpenAI API のレスポンス検証・リトライ・スコアクリップ・部分的な DB 更新（コード絞り込みでの置換）など、実運用を想定した安全策を盛り込んでいる。

今後の予定（提案）
- news_nlp のエラーハンドリング・部分成功時のロールバック戦略の追加強化。
- position_sizing の銘柄別 lot_size 対応（stocks マスタ参照）。
- .env パースの追加ユニットテスト。
- ExecutionEngine / Monitoring の単体・統合テスト強化と Docker 化によるデプロイ容易化。

--- 

この CHANGELOG はコードベースの内容から推定して作成しています。実際のリリース方針やバージョン運用に合わせて調整してください。