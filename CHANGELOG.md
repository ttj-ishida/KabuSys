CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and the following semantic versioning.

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース。以下の主要機能・モジュールを追加。
  - 実行用スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て ExecutionEngine.run_session を呼び出す。
      - 起動時にプロセス優先度を "high" に設定（utils/process_priority.set_process_priority を利用）。
      - 監視用テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。
  - 監視用スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動用エントリポイント。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックして警告ログを出力。
      - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB に書き込む設計。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - src/kabusys/config.py
      - .env/.env.local の自動読み込み実装（OS 環境変数優先、.env.local は上書き）。プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - 複雑な .env 行解析を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
      - Settings クラスに多数のプロパティを提供（J-Quants、kabu API、LINE API、DuckDB/SQLite パス、paper_trading 用設定、監視閾値、PID/KILL フラグなど）。
      - PAPER_FILL_MODE の値検証（instant|partial|never|reject）を実装。
      - KABUSYS_ENV / LOG_LEVEL の妥当性検査（許容値以外は ValueError）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナル選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
      - 等金額配分 calc_equal_weights。
      - スコア重み配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限超過時に新規候補を除外する実装（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear を規定、未知の場合は警告して 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各割当方式に対応した発注株数計算。単元株（lot）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックなどを実装。
  - ユーティリティ
    - utils/process_priority.py
      - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度設定を行うユーティリティを追加。
      - CPU affinity を最初 N コアにピン留めする set_cpu_affinity 実装。
      - psutil による権限不足等をハンドリングして警告ログに落とすフェイルセーフ。
  - 研究・リサーチ機能
    - research/factor_research.py
      - Momentum / Volatility / Value ファクター計算。DuckDB 上の prices_daily / raw_financials を参照して、mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等を算出。
      - 長期移動平均やATR 等のウィンドウ不足時の None ハンドリングを実装。
    - research/feature_exploration.py
      - 将来リターン calc_forward_returns（複数ホライズンに対応）、IC（calc_ic）計算（Spearman 相関に基づくランク相関）、factor_summary（count/mean/std/min/max/median）などを追加。外部ライブラリに依存せず純粋 Python 実装。
    - research/__init__.py に主要関数をエクスポート。
  - AI / ニュース NLP
    - ai/news_nlp.py
      - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores に書き込むワークフローを実装。
      - ニュース収集ウィンドウ計算（target_date に対する JST ベースのウィンドウ）と記事集約、1 銘柄あたり最大記事数/文字数トリム、最大バッチサイズ 20 銘柄でのバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードのみ DELETE→INSERT）などを設計。
      - OPENAI_API_KEY 未設定時は明示的なエラーを投げる仕様（api_key 引数での上書きも可能）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツールを実装。system_status / trade_logs / risk_logs を集計し稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を出力。
      - パス/閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）をデフォルト基準にして PASS/FAIL を判定。
      - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数との併用をサポート。
  - パッケージ基礎
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- (初期リリースにつき該当なし)

Fixed
- (初期リリースにつき該当なし)

Notes / Important behaviours
- run_monitoring は監視データの書き込みに本番 sqlite_path を使用するため、監視データは環境に依存せず一貫して本番 DB に保存されます。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の環境で安全に動作）。
- process priority / cpu affinity は権限不足や未対応 OS の場合に警告を出してスキップするため、実行環境に応じて必ず成功するとは限りません。
- ai/news_nlp の OpenAI 呼び出し部分は外部サービスに依存するため、API キー設定やレート制限に注意してください。

References
- 各モジュール内の docstring、ログメッセージ、コメントを変更履歴の根拠として要約しています。