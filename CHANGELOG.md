# Changelog

すべての変更は Keep a Changelog の慣例に従い記載しています。  
重大な後方互換性の破壊は特にありません（明示した場合を除く）。

最新の変更
==========

Unreleased
----------

（現在の開発中の変更はここに記載します）

リリース履歴
==========

0.1.0 - 2026-04-13
-----------------

Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。起動時にプロセス優先度を "high" に設定し、必要なコンポーネント（BrokerClient、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立ててセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化する。

- 環境設定/ロードの改善（kabusys.config）
  - プロジェクトルートの自動検出（.git / pyproject.toml を探索）に基づき .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを実装：クォート、export プレフィックス、行内コメントの扱い、上書き制御（override/protected）に対応。
  - Settings クラスを提供し、環境変数の取得・検証・型変換を集中管理（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
  - PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL の値検証を実装。

- Paper Trading サポート
  - run_execution が KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離する仕組みを追加。
  - paper_verification_report ツールを追加。Paper Trading DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し、PASS/FAIL 判定（閾値はソース内で定義）を出力する CLI を提供。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等額配分へフォールバック。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
  - position_sizing: 各種配分方式（risk_based / equal / score）に対応した発注株数計算ロジック（calc_position_sizes）を実装。lot_size 単位で丸め、aggregate cap により利用可能現金を超えた場合は縮小・端数調整を行う。コストバッファ対応（cost_buffer）。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research: DuckDB を用いたモメンタム、ボラティリティ、バリューファクター計算（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials テーブルを参照。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）およびファクター統計サマリ（factor_summary）とランク関数（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約し OpenAI (gpt-4o-mini) を利用して銘柄ごとのセンチメントスコアを ai_scores テーブルに書き込む処理（score_news）を実装。JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）を正しく UTC に変換して集計。
  - バッチ処理（最大 20 銘柄/コール）、記事数・文字数トリム、JSON Mode を前提とした出力検証、スコアを ±1.0 にクリップ、失敗時はフェイルセーフで継続する設計。
  - API エラー（429、ネットワーク断、5xx、タイムアウト等）に対する指数バックオフのリトライ処理を実装。
  - API キー未設定時は明確なエラーを返す（ValueError）。

- ユーティリティ（kabusys.utils）
  - process_priority: クロスプラットフォームでプロセス優先度を設定する set_process_priority を追加（Windows / POSIX に対応）。アクセス権限失敗時は警告を出してスキップするフェイルセーフ。
  - CPU affinity を設定する set_cpu_affinity を追加（最初の N コアに固定。引数検証あり）。失敗時は警告を出してスキップ。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として追加。

Changed
- DB 接続の扱い
  - 監視系（run_monitoring、init_monitoring_db）では環境に関わらず Settings.sqlite_path（本番）を使用して監視テーブルを初期化する仕様に決定。
  - run_execution は paper_trading 環境のとき専用 DB を使用するよう変更（本番データと完全分離）。

- ロギング／フェイルセーフの改善
  - 各所で予期しない例外発生時に logger.exception や logger.warning を用いてエラーを記録し、メインループやバッチ処理は継続するようにした（監視ループ・AI スコア処理等）。

- 環境変数のデフォルトと入力検証
  - MONITOR_POLL_INTERVAL の不正値（0以下や非整数）に対してデフォルト（60秒）へフォールバックし警告を出すようにした。
  - PAPER_FILL_MODE 等の enum 的環境変数は不正値で例外を投げるよう検証を強化。
  - KILL_FLAG 関連・PID ファイルパスの設定を Settings に集約。

Fixed
- DB スキーマの初期化を冪等に（init_monitoring_db を起動時に呼び出し、テーブル未存在時に作成することで複数起動や paper_trading の DB 分離に対応）。
- DuckDB への executemany 等の制約に配慮した書き込みロジック（空 params を避ける等）を考慮。

Security
- 環境変数自動読み込み時に既存 OS 環境を保護する protected セットを導入（.env の上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト時の安全策）。

Notes / Developer hints
- 多くのモジュール（portfolio/*、research/*）は「純粋関数」を志向しており、DB に直接アクセスしない設計（副作用なし）となっています。これによりユニットテストの容易化を意図しています。
- ドキュメント参照：各モジュール内に PortfolioConstruction.md, StrategyModel.md 等を参照する旨のコメントがあります。設計思想やパラメータの意味はソース内コメントを参照してください。
- news_nlp は OpenAI の利用前提であり、実運用では API キー管理と利用量の監視が必要です。

今後の予定（予定機能）
- 銘柄ごとの lot_size を銘柄マスタから取得する拡張（position_sizing の TODO）。
- news_nlp の一部レスポンス検証や保存戦略の更なる堅牢化（部分失敗時のロールバック/トランザクション戦略等）。
- research モジュールの追加ファクターや最適化（パフォーマンスチューニング、並列化）。

以上。