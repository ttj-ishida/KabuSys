CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-13
------------------

Added
- 初期リリース: KabuSys のコア機能群を追加。
  - 実行・監視エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、Paper Trading 用に data/paper_trading.db を使用する（本番 DB と分離）。
      - 実行前にプロセス優先度を設定（utils.process_priority.set_process_priority）。
      - SQLite / DuckDB 接続を扱い、engine.run_session() を実行後にクリーンアップ。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 設定管理
    - config.Settings を追加。.env/.env.local の自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml 基準）。  
    - OS 環境変数の保護（.env 読み込み時に既存キーを protected として扱う）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 各種設定プロパティを提供（DB パス、PID/KILL フラグ、監視閾値、環境種別判定等）。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH のサポート。
  - ポートフォリオ構築（pure functions）
    - portfolio.portfolio_builder: シグナルの候補選定（select_candidates）、等分配・スコア重み（calc_equal_weights / calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市況レジーム乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）。  
      - risk_based / equal / score の配分方式、単元（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応。
  - 研究（research）
    - research.factor_research: Momentum / Volatility / Value ファクター計算関数（DuckDB を用いた SQL ベース実装）。
      - calc_momentum, calc_volatility, calc_value を提供。欠損データの扱いと行数条件（例: MA200 が 200 行未満は None）を明示。
    - research.feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクタ要約統計を提供。
      - calc_forward_returns（可変ホライズン）、calc_ic（ランク相関）、factor_summary、rank ユーティリティ。
    - research パッケージは外部解析ライブラリに依存せず標準ライブラリ + DuckDB で実装。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に保存する機能を追加。  
      - タイムウィンドウ計算（JST ベース→UTC 変換）、記事／銘柄ごとの集約、バッチ（最大 20 銘柄/回）での API 呼び出し、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 でのクリップ、部分失敗時の既存スコア保護（部分的 DELETE + INSERT）などを実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。  
      - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計・表示。閾値（稼働率 99% 等）を定義し PASS/FAIL 判定を出力。コマンドライン引数 --from/--to/--db をサポート。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows 用定数・POSIX nice 値を吸収）、CPU affinity 設定ユーティリティを追加。  
      - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

Changed
- 初版のため過去からの変更点はなし（新規追加）。

Fixed
- 各モジュールで実運用上の堅牢化を実施（初版実装の想定事項）。
  - .env パーサーはクォート・エスケープ・インラインコメント・export プレフィックス等を扱うように実装し、不正行を無視することで読み込み耐性を向上。
  - process_priority/set_cpu_affinity は AccessDenied 等の例外を捕捉してログに警告を出しつつ処理を継続するように実装。
  - paper_verification_report や research の各クエリはデータ欠損やテーブル未存在時に安全にフォールバック（OperationalError ハンドリング）する。  
  - position_sizing の aggregate cap スケーリングや remainder による lot 単位での再配分ロジックを実装し、利用可能現金を保守的に扱う。

Security
- 環境変数の取り扱いに関する注意: OpenAI API キー等の必須値は明示的に要求し、未設定時は ValueError を発生させて早期に検出する実装を採用。

Notes / Known limitations
- デフォルトの単元株数 lot_size は全銘柄共通（100）としている。将来的に銘柄別 lot_size へ拡張予定（コード内に TODO を記載）。
- 一部の計算（例: apply_sector_cap の price が 0 の場合）は過少推定を招く可能性があり、価格フォールバックの追加が想定されている。
- research / ai モジュールは DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）に依存するため、適切なデータ投入が必要。
- run_monitoring は常に本番 sqlite_path を参照する設計（監視は本番 DB ベース）。Paper Trading の監視分離が必要な場合は設定の見直しが必要。

Authors
- コード内コメントに基づく初期リリースのまとめ。