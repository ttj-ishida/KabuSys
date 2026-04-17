CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

v0.1.0 — 2026-04-17
-------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 実行エントリ／ランナー
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（設定: PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。デフォルトのリスク設定（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20）を設定。
    - プロセス優先度を起動時に "high" に設定（set_process_priority を呼び出し）。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）を用いた起動／停止制御を実装。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値（0 以下や非整数）は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用する挙動を明示。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 設定管理
  - config.py
    - .env/.env.local 自動読み込み機能を導入（優先順位: OS 環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を起点に探索して決定。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサは export 文、クォート値（バックスラッシュエスケープ対応）、インラインコメント処理等に対応。
    - 環境変数保護（protected set）を考慮した上書きロジックを実装。
    - Settings クラスを提供し、アプリケーション全体で利用する設定プロパティを整理（J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等）。
    - PAPER_FILL_MODE の検証（instant / partial / never / reject のみ有効）を追加。
    - KABUSYS_ENV / LOG_LEVEL の値検証を追加（有効値を限定）。
    - 監視用の閾値プロパティ（cpu/memory/disk）とファイルパス（pid_file, kill_flag_path）を追加。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 選定ロジック: BUY シグナルを score 降順、同点時は signal_rank の昇順でタイブレークして上位 N を返す select_candidates を実装。
    - 等金額配分 calc_equal_weights とスコア加重 calc_score_weights を実装。スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有（当日売却予定除外）に基づきセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外。unknown セクターは制限対象外として扱う。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull=1.0、neutral=0.7、bear=0.3、未知は 1.0 でフォールバックし警告）。
    - 実装内に将来の拡張（価格フォールバック、セクター判定など）に関する TODO コメントを残す。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - リスクベース計算、単元（lot_size）丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）に合わせたスケーリング、cost_buffer（スリッページ・手数料見積り）の考慮、余り配分（lot 単位）アルゴリズムを実装。
    - price 欠損時のスキップやログ出力を実装。将来的な銘柄別 lot_size への拡張をコメントとして残す。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を実装（Windows と POSIX(Linux/Mac/FreeBSD) を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告ログを出すフェイルセーフ設計。
- リサーチ／因子計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（momentum / volatility / value）。
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離（MA200）を計算。過去データ不足時は None を返す。スキャン幅にバッファを設けて週末・祝日を吸収。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。true_range の NULL 伝播を制御して欠損データを正しく扱う。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER/ROE を計算（EPS が 0 の場合は None）。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（horizons 検証あり）、ランク相関 IC 計算 calc_ic（スピアマン ρ、必要レコード数チェック）、rank、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリで実装。
  - research/__init__.py
    - 利用しやすいトップレベルエクスポートを用意（calc_momentum 等 + zscore_normalize の再エクスポート）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - CLI 引数: --from, --to, --db をサポート。
    - 指標: 稼働率 (uptime_pct), 注文成功率 (fill_rate), 送信率 (send_rate), リスク却下数, レイテンシ（avg/max/P95）を計算して出力。
    - 判定基準（PASS/FAIL）のデフォルト閾値を明記（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）。
    - 空データやテーブル欠損時の例外処理（sqlite3.OperationalError をキャッチして N/A で扱う）を実装。
- AI / ニュースNLP（下書き）
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込む処理フローを実装。
    - ニュース検索ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）、記事集約、1銘柄あたりのトークン肥大化対策（最大記事数・文字数トリム）、バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップを設計。
    - OpenAI API キー解決ロジック（引数または環境変数 OPENAI_API_KEY）と未設定時の ValueError を実装。
    - 設計上は部分成功時に既存スコアを保護するために対象コードを限定して DELETE→INSERT を行う方針。
    - 注意: ファイル末尾が途中で切れており（処理の途中でコードが欠落）、実装が完了していない箇所が存在する（本番運用前に残りの処理とエラーハンドリングを確認する必要あり）。
- パッケージ情報
  - __init__.py にてパッケージ名と __version__ = "0.1.0" を定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

Known issues / Notes
- ai/news_nlp.py が途中で切れているため、news スコアリングの一部処理（記事フェッチの後続・API 送信ループ・DB 書き込み等）が未完。デプロイ前に該当ファイルの未完部分を補完しテストしてください。
- portfolio/risk_adjustment.apply_sector_cap は price の欠損（0.0）の場合にエクスポージャを過少見積してしまう旨を TODO コメントで指摘している。重要な運用ではフォールバック価格（前日終値等）を導入することを推奨。
- calc_position_sizes は現状全銘柄共通の lot_size（デフォルト 100）を想定している。将来的に銘柄別単元対応が望ましい（設計上の注記あり）。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に制御することを推奨。

Contributing
- 貢献・バグ報告はこのリポジトリの Issue / Pull Request を通して行ってください。リリース後の修正は ChangeLog に逐次追記します。