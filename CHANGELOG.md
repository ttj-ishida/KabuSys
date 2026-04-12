CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
バージョン番号はパッケージ内の __version__（現状: 0.1.0）に基づきます。
日付はコードベースから推測して付与しています。

Unreleased
----------

- なし（現時点では公開済みの初期リリース相当の機能群です）。

0.1.0 — 2026-04-12
------------------

Added
- 基本アプリケーション構成を追加
  - パッケージのバージョンを __version__ = "0.1.0" として定義。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルパーサーを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートのエスケープ処理対応
    - インラインコメントの適切な取り扱い（クォート有無に応じた挙動）
  - Settings クラスを導入し、J-Quants / kabu / LINE / DB /監視/システム設定等をプロパティで提供。
  - 設定値検証:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/...）
    - PAPER_FILL_MODE の有効値検査（instant/partial/never/reject）
  - デフォルトパス:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
    - PID_FILE_PATH / KILL_FLAG_PATH：data 配下のデフォルトを採用
- 実行エントリ / プロセス管理
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化（Mock クライアントを想定）。
    - RiskManager / OrderManager / Reconciler 等の組み立てと ExecutionEngine.run_session の起動。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や parse 失敗）はデフォルトにフォールバックし警告を出力。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
    - 起動時にプロセス優先度を "high" に設定。
- DB 初期化ユーティリティ
  - monitoring 用 DB 初期化を行う init_monitoring_db 呼び出しを run_* スクリプトから実行（冪等性を確保）。
- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates（スコア順で候補選定）
    - calc_equal_weights / calc_score_weights（スコアゼロ時のフォールバックを含む）
  - risk_adjustment:
    - apply_sector_cap（セクター集中制限適用。unknown セクターは制限対象外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数: bull/neutral/bear）
  - position_sizing:
    - calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap のスケーリング、cost_buffer を利用した保守的見積り）
    - risk_based では stop_loss_pct を用いた株数計算
    - 投下額が available_cash を超える場合のスケーリングと残差処理（lot 単位で再配分）
- 研究・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER / ROE、raw_financials の最新レコード取得）
    - DuckDB を用いた SQL + Python の実装（prices_daily / raw_financials 前提）
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターン計算、最大ホライズン取扱）
    - calc_ic（Spearman ランク相関による IC 計算、レコード不足時は None）
    - factor_summary / rank（統計要約、同順位処理は平均ランク）
  - research パッケージの __all__ に主要ユーティリティをエクスポート
- AI ニュース NLP (kabusys.ai.news_nlp)
  - OpenAI（gpt-4o-mini） を用いたニュースセンチメントスコアリング実装を追加。
  - 機能ハイライト:
    - 対象時間ウィンドウの明確化（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
    - 記事の銘柄別集約（記事数・文字数でトリム）
    - バッチ（最大 20 銘柄/コール）での API 呼び出し、JSON Mode 想定の厳密パース
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ、上限回数設定）
    - レスポンスバリデーション、スコアの ±1.0 にクリップ
    - 成功した銘柄のみ ai_scores テーブルに置換で書き込み（DELETE + INSERT の局所化により部分失敗を許容）
    - OPENAI_API_KEY を参照（api_key 引数からの上書きも可）。未設定時は ValueError を送出。
- ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) 実装（Windows / POSIX を吸収、権限不足や未実装 API を安全に扱う）
  - set_cpu_affinity(cpu_count) 実装（最初の N コアに固定、無効時は全コア使用）
  - 例外時は警告ログを出して処理を継続するフェイルセーフ。
- ツール: Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
  - CLI スクリプトを追加（--from / --to / --db オプションをサポート）。
  - 指標と閾値:
    - 稼働率（uptime）閾値 99.0%
    - 注文成功率（fill rate）閾値 90.0%
    - 送信率（send rate）閾値 95.0%
    - P95 レイテンシ閾値 200 ms
  - P95 の計算、各種テーブル（system_status / trade_logs / risk_logs）からの集計を行い、PASS/FAIL 判定を出力。
  - DB が存在しない・テーブル欠損時の保護処理（OperationalError を捕捉して N/A を返す）。
- パッケージ公開用 __all__ 整備（portfolio, research 等で主要関数を再エクスポート）

Changed
- コード設計上の方針明記
  - 研究・AI モジュールは「本番口座・発注 API にはアクセスしない」方針を明示（安全性・検証容易性のため）。
  - 日付参照に関してルックアヘッドバイアスを避ける設計（target_date を明示的に受け取り、datetime.today() を参照しない）。
- DB 周りの取り扱い
  - run_monitoring は常に本番 sqlite_path を使用（監視データは本番 DB に対して取得・記録）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と完全分離。

Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して安全にデフォルト値へフォールバックし、ログで警告を出すよう修正。
- .env パーサーのクォート内エスケープ処理を実装し、複雑な .env 値の読み込み信頼性を向上。
- DuckDB executemany の制約に配慮した事前チェック（空パラメータを渡さない等）を考慮した実装方針を明記。

Security
- 必須シークレットは環境変数から取得する設計（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）。README/.env.example に従って設定する必要あり。
- .env 自動ロードは OS 環境変数を保護するため .env.local を上書きモードで読み込むが、既存の OS 環境変数は上書きされないよう保護される。

Known issues / Notes
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来前日終値などのフォールバック価格を検討する記述が残っています（TODO）。
- news_nlp.score_news:
  - OpenAI 呼び出し失敗時はフェイルセーフでスキップする設計だが、部分的失敗時の観測性（どのチャンクが失敗したか等）は運用ログに依存します。
- set_process_priority / set_cpu_affinity:
  - 権限不足やプラットフォーム未対応時は警告を出してスキップします。期待どおりに動かない場合は実行環境の権限を確認してください。

Migration / Upgrade notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は未設定だと Settings の該当プロパティ参照時に ValueError を投げます。事前に .env を用意するか OS 環境変数を設定してください。
- PAPER_TRADING:
  - paper_trading モードではデータベースが data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に分離されます。既存の監視 DB を誤って参照しないよう注意してください。
- OPENAI_API_KEY:
  - news_nlp を使うには OPENAI_API_KEY を環境変数か score_news に渡す必要があります。

Acknowledgements / References
- 各モジュール内に設計上の参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及があります。実稼働/検証時は該当ドキュメントも参照してください。

（注）本 CHANGELOG は提示されたソースコードから機能追加・設計方針を推測して作成しています。実際のリリースノートはコミット履歴やリリース担当の記録を元に確定してください。