CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠します。
リリース日付はコードベースから推測して設定しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db, 環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - デフォルトのリスク設定 (RiskConfig) を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - PID ファイルパスと停止フラグの取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - stop_requested.flag による外部停止検知。
- 設定管理
  - config.py
    - .env 自動ロード実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env/.env.local の読み込み順序、既存 OS 環境変数保護（override/protected 機能）。
    - .env パーサーで export 指定、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラスを提供（J-Quants / kabu API / LINE / DB / 監視閾値 / 環境判定 / log level 等のプロパティ、妥当性チェック付き）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など主要環境変数を定義・検証。
- 監視関連
  - monitoring_db 初期化呼び出し（起動時に監視テーブルの存在を保証）。
  - SystemMonitor の呼び出しポイントを実装（run_monitoring から check_once をループ実行）。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定を実装（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値対応）。
    - CPU affinity 固定用 set_cpu_affinity を追加（core 数チェック、権限不足時は警告でスキップ）。
    - 権限不足や未対応プラットフォーム時に安全にフォールバック。
- ポートフォリオ関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順・同スコア時 signal_rank によるタイブレーク）。
    - calc_equal_weights、calc_score_weights（スコア合計 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（既存保有のセクター暴露を計算し、上限超過セクターの新規候補を除外。unknown セクターは除外しない）。
    - calc_regime_multiplier（レジームに応じた投下資金乗数。未定義レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes（risk_based, equal, score の各 allocation_method を実装）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でスケールダウン、スケール後の残差配分ロジックを実装。
    - price 欠損や不正値時のスキップ、コストバッファ（cost_buffer）考慮。
- リサーチ関連
  - research/factor_research.py
    - calc_momentum、calc_volatility、calc_value を実装（DuckDB の prices_daily / raw_financials を使用）。
    - 各ファクターについてウィンドウサイズや必要データ不足時の None 処理を開始。
  - research/feature_exploration.py
    - calc_forward_returns（複数ホライズン対応、入力検証）、calc_ic（Spearman ランク相関）、rank（同順位は平均ランク、丸めにより ties の扱いを安定化）、factor_summary（基本統計量）を実装。
  - research/__init__.py で zscore_normalize を再エクスポート。
- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を対象に OpenAI (gpt-4o-mini) を用いたセンチメントスコアリング設計を実装（ニュースウィンドウ計算、バッチサイズ、トークン抑制、APIリトライ戦略、レスポンス検証、スコアクリップ、ai_scores テーブルへの安全な差替え方針等）。
    - calc_news_window により JST ベースの収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC naive datetime で計算するユーティリティを実装。
    - OpenAI API キー解決（引数 > 環境変数）と未設定時の ValueError を実装。
- CLI / ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - デフォルト DB: data/paper_trading.db、--db オプションで上書き可能。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), P95 レイテンシ、リスク却下数 等を集計。
    - 判定基準と閾値を定義（稼働率 99% 以上等）、P95 計算と表示、データ欠如に対する N/A 表示。
- DB/ファイル操作
  - duckdb を利用した分析／研究ワークロード向け接続を導入（duckdb_path 設定）。
  - SQLite 接続を起動時に確立し監視/実行で使用。

Changed
- 初期バージョンの設計に基づく各種デフォルト値と挙動を定義
  - MONITOR_POLL_INTERVAL デフォルト 60 秒（run_monitoring）。
  - PAPER_FILL_MODE の有効値と検証 ("instant", "partial", "never", "reject") を Settings で導入。
  - Settings.env の妥当性検査（development / paper_trading / live のみ許容）。
  - LOG_LEVEL の妥当性検査。

Fixed
- 設定パーサーの改良により .env の export/, クォート、エスケープ、インラインコメントに適切に対応（解析耐性向上）。
- calc_score_weights が全スコア 0 の場合に落ちる問題を等配分でフォールバックするよう修正（警告出力を追加）。

Security
- OpenAI API キーは引数または環境変数で解決。未設定時は明示的なエラーとし、意図しないキー漏洩を防止。

Notes / Known limitations
- ai/news_nlp.score_news の実装は外部 API 呼び出しの部分が含まれるため、実行環境で OPENAI_API_KEY の設定が必要。
- 一部の関数（例: position_sizing の price フォールバック）は TODO コメントで拡張予定。一時的に price が欠損（0.0）の場合は計算がスキップされ、エクスポージャーが過少見積りされる可能性がある。
- run_monitoring は監視用 DB として常に production 相当の sqlite_path を参照する設計（環境に依存せず監視を行うための仕様）。
- CPU affinity / プロセス優先度設定は OS 権限に依存し、権限がない場合は警告を出してスキップする安全設計。

Breaking Changes
- 初期公開リリースのため該当なし。

References
- ソースコードの各モジュール内 docstring と設計注記に詳細あり。必要に応じて該当ファイルを参照してください。