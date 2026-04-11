KEEP A CHANGELOG
=================

すべての重要な変更を記載します。フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-11
-------------------

Added
- パッケージ初期版を追加（バージョン: 0.1.0）。
- 実行／監視用エントリポイントを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動してセッションを実行するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - プロセス起動時にプロセス優先度を "high" に設定。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視（monitoring）用途は環境に関わらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定してから DB を開き、ループで monitor.check_once() を繰り返す。KeyboardInterrupt をハンドルして正常終了処理。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装: export 形式、クォート内エスケープ、インラインコメントの扱いなどに対応。
    - Settings クラスを導入してアプリケーション設定をプロパティとして提供（DB パス、PID/kill フラグ、しきい値、ログレベル、環境判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額／スコア加重配分を実装（スコア全0 の場合は等配分へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の除外ロジック（既存保有時価を用いて上限を超えるセクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト / フォールバック挙動を明記）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた発注株数計算、単元（lot_size）丸め、per-position 上限、aggregate cap スケールダウン、コストバッファ考慮、残差調整ロジックを実装。
  - src/kabusys/portfolio/__init__.py で上記機能を公開。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX を吸収）。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装（最初の N コアに固定、入力検証と例外ハンドリングあり）。
  - src/kabusys/utils/__init__.py（パッケージ化目的の空ファイル追加）

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）等を DuckDB 上で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（過去の最新財務データ選択処理あり）。
    - 設計として DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照、外部 API には依存しない方針を採用。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量サマリを提供。
  - src/kabusys/research/__init__.py で主要関数を公開。
  - 実装方針として外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB を使用。

- AI 関連機能（OpenAI を用いた NLP）
  - src/kabusys/ai/news_nlp.py
    - raw_news を集約して OpenAI (gpt-4o-mini) で銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に書き込む機能。
    - バッチ（1回最大 20 銘柄）・チャンク処理、1銘柄あたり記事件数/文字数上限（トリム）、リトライ（429・ネットワーク・5xx）、レスポンスの厳密バリデーション、スコアの ±1.0 クリップ等を実装。
    - API キーの解決（引数優先、なければ OPENAI_API_KEY 環境変数）。未設定時は ValueError。
    - 書き込みは部分失敗時に既存データを保護するため対象コードのみ DELETE→INSERT を行う（トランザクション）。
    - テスト用フック: _call_openai_api を差し替え可能に実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能。
    - マクロ記事抽出用キーワード群、API 呼び出しのリトライ・フォールバック（失敗時は macro_sentiment=0.0）等を実装。
    - news_nlp の calc_news_window を再利用してウィンドウ計算を統一。

- パッケージ情報
  - src/kabusys/__init__.py にパッケージバージョン __version__ = "0.1.0" を設定。

Changed
- 設定の読み込み優先順を明確化: OS 環境 > .env.local > .env。OS の既存変数は保護され、.env.local は上書き可能。
- 実行スクリプト群で起動直後にプロセス優先度を上げる実装を統一して挿入（set_process_priority("high")）。
- DB 接続方針:
  - 監視 run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視を一元化。
  - 実行 run_execution は paper_trading 環境時は専用 DB を使用し本番 DB と分離。
- DuckDB を分析用途・AI 用集計クエリで積極利用。リサーチ・AI モジュールは DuckDB 接続を受け取る API 設計。

Fixed
- monitoring DB 初期化処理（init_monitoring_db）を起動前に呼び出して監視テーブルの存在を保証（冪等に実行可能）。
- .env パーサで export 付き行、クォート内部のバックスラッシュエスケープ、インラインコメントの扱いを改善。

Security
- 環境変数未設定の必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を Settings._require で検出し、未設定時は ValueError を投げて起動失敗させる設計により誤ったデプロイを防止。
- .env 自動ロード時に OS 環境変数を保護する仕組みを実装。

Notes / Migration
- 環境変数名（代表例）
  - KABUSYS_ENV: development / paper_trading / live のいずれかを指定。paper_trading は DB 分離される。
  - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒）。正の整数で指定。無効値はデフォルト 60 秒にフォールバック。
  - OPENAI_API_KEY: news_nlp / regime_detector で使用。関数引数で上書き可能。
  - PAPER_FILL_MODE: paper_trading 時の MockBroker 動作（instant/partial/never/reject）。
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等を環境変数でカスタマイズ可能。
- OpenAI API 利用部分は外部 API に依存するため、API キーおよびレート制限に注意。失敗時はフォールバック（部分スコア化のスキップや macro_sentiment=0）する設計でフェイルセーフを備えている。

Acknowledgements
- DuckDB を用いた分析向けの SQL 集計、OpenAI を用いた NLP バッチ処理、プロセス優先度制御など、運用面を考慮した実装を含む初版です。

-----
（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はテスト結果やドキュメント等の情報を合わせて調整してください。）