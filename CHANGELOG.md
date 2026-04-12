CHANGELOG.md
=============

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
安定した API バージョンは semantic versioning を想定します。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-12
-----------------

初回リリース — KabuSys の基本機能を纏めた最初の公開バージョン。

追加 (Added)
- パッケージ全体
  - 初期バージョン 0.1.0 を公開。
  - __version__ を 0.1.0 に設定。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
    - KABUSYS_ENV によって paper_trading 用の SQLite DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を介して本番/モックブローカーを切替え。
    - ExecutionEngine / OrderManager / RiskManager / Reconciler の組立てとセッション実行。
    - duckdb 接続を利用。

  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - 例外を安全にキャッチして次ポーリングへフォールバック。
    - KeyboardInterrupt で正常終了し、DB接続をクローズ。

- 設定管理
  - config.py: Settings クラスを追加。
    - .env / .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml に依存）。
    - .env パーサ実装（export 形式、引用符・エスケープ、インラインコメントの取り扱いに対応）。
    - 必須環境変数取得メソッド _require。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。

- モジュール: portfolio
  - portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補抽出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。総スコアが 0 の場合は等金額にフォールバック（WARNING）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（sell_codes を除外可能、"unknown" セクターは制約対象外）。
    - calc_regime_multiplier: market regime に基づく資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知は 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: 発注株数計算ロジックを追加（risk_based / equal / score 対応）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウンと残差配分を実装。
    - cost_buffer による保守的なコスト見積りを考慮。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。権限不足や未サポート OS は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を固定（None で無効化）。入力検証あり。

- リサーチ/特徴量
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200乖離を DuckDB で計算。
    - calc_volatility: ATR(20)、ATR比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組合せて PER/ROE を計算。
    - DuckDB を前提とした SQL + Python 実装。ウィンドウサイズやスキャン範囲を考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（horizons）を一括取得。
    - calc_ic: スピアマンランク相関（IC）計算。有効レコードが 3 未満で None を返す。
    - factor_summary / rank: 統計サマリ、ランクの実装（同順位は平均ランク、丸めで ties 対応）。

- AI ニュース NLP
  - ai/news_nlp.py
    - OpenAI API（gpt-4o-mini, OpenAI client）を用いたニュースセンチメントスコアリング機能を追加。
    - 記事を銘柄ごとに集約し、最大 20 銘柄バッチで API へ送信。
    - リトライ（429/ネットワーク/5xx）用の指数バックオフ、レスポンス検証、スコアの ±1.0 クリップ。
    - 書き込みは対象コードに限定して DELETE→INSERT（部分失敗時に既存スコアを保護）。
    - 必須: OPENAI_API_KEY または api_key 引数（未設定時は ValueError）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドラインから実行可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して人が読めるレポートを標準出力に出力。
    - デフォルト DB パス: data/paper_trading.db。--from/--to/--db オプション対応。
    - 判定基準（閾値）を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

変更 (Changed)
- デフォルト動作・設計上の注記（実装からの決定）
  - monitoring は KABUSYS_ENV に関係なく監視用 DB（settings.sqlite_path）を使用するように設計。
  - .env の自動ロードはプロジェクトルートが検出できる場合にのみ行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Research / AI の関数はルックアヘッドバイアスを防ぐために date.today()/datetime.today() に依存しない設計（target_date を明示して呼ぶ）。

修正 (Fixed)
- .env 読み込み時の IO エラーに対する警告と安全なフォールバックを追加。
- process_priority および set_cpu_affinity は psutil の例外（AccessDenied / NotImplementedError 等）を捕捉して警告を出すようにした。

既知の注意点 (Known issues / Notes)
- position_sizing: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり（TODO にてフォールバック価格の検討を注記）。
- ai/news_nlp: 実行には OpenAI API キーが必須。API 呼び出し回数やコストを考慮のこと。
- DuckDB 関連: executemany 等で空パラメータリストに対する制約に注意（実装中にチェック済み）。
- 一部の機能は外部ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に依存する設計ノートを含む。

セキュリティ (Security)
- なし

リリースノート
- 本リリースはシステムの初期実装をまとめたもので、運用前に環境変数設定（API キー、DB パス等）および権限（プロセス優先度設定や DB ファイル書込み権限）を確認してください。