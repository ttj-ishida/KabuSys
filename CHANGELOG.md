# Changelog

すべての注目すべき変更はここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーション初期実装を追加。
  - パッケージメタデータ:
    - kabusys.__version__ = 0.1.0
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト/data/stop_requested.flag ファイルで制御。
    - モニタリング処理は例外をキャッチして次回ポーリングへ継続するフェイルセーフ。
    - 監視用 DB 初期化（init_monitoring_db）および DuckDB 接続を行う。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て。
    - スレッドで実行し、停止フラグ検知で Graceful stop を行う。
    - 実行用 PID ファイルの利用（data/execution.pid 等）。
- 設定 / 環境読み込み:
  - config.Settings を実装。
    - .env / .env.local の自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env パーサの強化（export プレフィックス、クォート文字列、エスケープ、インラインコメント処理、保護された OS 環境変数）。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグパス / Paper Trading 関連 / 監視しきい値 / ログレベル / 環境判定）。
    - 設定値のバリデーション（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL など）。
- ユーティリティ:
  - utils.process_priority
    - set_process_priority(level) を実装（Windows と POSIX を吸収）。
    - set_cpu_affinity(cpu_count) を実装（利用可能なコアにプロセスをピン留め）。
    - アクセス拒否や未対応プラットフォームは警告を出してスキップする安全設計。
- ポートフォリオ構築関連（純粋関数群、DB 非依存）:
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア順ソート / 上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限の適用（既存保有を考慮、売却予定銘柄除外可）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数算出（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株丸め（lot_size）、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積り、端数配分ロジックを実装。
- リサーチ / ファクター計算（DuckDB を使用）:
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
    - DuckDB 上のウィンドウ関数を利用した効率的な実装。
  - research.feature_exploration
    - calc_forward_returns: 各ホライズンの将来リターンを計算（複数ホライズンを同時取得、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。十分な有効レコードがなければ None を返す。
    - factor_summary: count/mean/std/min/max/median を計算（None 値除外）。
    - rank: 同順位は平均ランクで処理するランク関数。
  - research.__init__ で必要関数をエクスポート。
- AI / ニュース NLP:
  - ai.news_nlp（ニュースの OpenAI によるセンチメントスコアリング）
    - target_date に対するニュース時間窓の計算（JST ベース -> UTC 変換）。
    - raw_news + news_symbols を銘柄ごとに集約し、最大記事数/文字数でトリム。
    - バッチ（最大 20 銘柄）で OpenAI (gpt-4o-mini) に JSON 形式で送信、429/5xx/タイムアウトに対して指数バックオフでリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ・ai_scores テーブルへの置換的書き込みを設計。
    - OpenAI API キーの解決と未設定時の ValueError。
    - （注）実装はフェイルセーフ設計で、API 失敗時は他処理へ影響を与えない。
- ツール:
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（P95）を集計。
    - 合否基準（稼働率・成功率・送信率・P95 レイテンシ）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数対応。
- 監視 DB 初期化ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- その他:
  - パッケージエクスポート（portfolio/、research/ 等の __all__ 設定、tools パッケージ初期化）。

Changed
- .env の自動ロード挙動を導入:
  - OS 環境変数を保護しつつ .env/.env.local を読み込む。`.env.local` は既存 OS 変数以外を上書きする。
- 監視プロセスの仕様:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（設計上、監視データは本番 DB に集約）。
- プロセス優先度設定:
  - 起動スクリプトは開始時に set_process_priority("high") を呼び出し、重要プロセスの優先度を上げるようにした。

Fixed
- （現時点で明確なバグ修正履歴は無し。初期リリース）

Notes / 注意事項
- Paper Trading と本番 DB は明確に分離する設計（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）。
- .env の自動読み込みはプロジェクトルートが検出できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合はスキップされる。
- ai.news_nlp モジュールは外部 OpenAI API に依存するため、API キーの設定（OPENAI_API_KEY）と通信環境に注意してください。
- DuckDB を使用するクエリは prices_daily / raw_financials 等のスキーマを前提としているため、適切なデータ投入が必要です。

以上。今後の変更は本 CHANGELOG に追記してください。