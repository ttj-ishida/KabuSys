# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
初回リリースとして v0.1.0 を記載しています（リリース日: 2026-04-13）。

全般的な注記
- 本リリースはパッケージ初版相当の機能群を実装しています。
- DuckDB / SQLite を用いたデータ処理・分析、実行エンジンと監視処理、ポートフォリオ構築ユーティリティ、研究/分析モジュール、OpenAI を用いたニュース NLP 連携などを含みます。
- 環境変数は .env / .env.local / OS 環境変数から読み込まれます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Unreleased
- （なし）

v0.1.0 — 2026-04-13
- Added
  - 実行関連
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite (PAPER_TRADING_SQLITE_PATH / default: data/paper_trading.db) を使用し、MockBrokerClient を利用する設計を想定。
      - プロセス優先度を高（"high"）に設定してから起動する処理を追加（psutil による抽象化）。
      - 依存コンポーネントの組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の連携）。
      - duckdb 接続を ExecutionEngine に渡す。
  - 監視関連
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は本番 DB を参照）。
      - 起動時にプロセス優先度を "high" に設定。
  - 設定管理
    - config.py: Settings クラスを追加。
      - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
      - 複数の設定プロパティを実装（データベースパス、PID/kill フラグパス、しきい値、環境種別判定、paper_trading 用設定、PAPER_FILL_MODE 等）。
      - .env パースは export プレフィックス・クォート・インラインコメント等に対応する独自ロジックを実装。
  - ポートフォリオ構成
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順選定（signal_rank によるタイブレーク）。
      - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバック。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存保有のセクター露出を計算して候補をフィルタリング）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返すユーティリティ。
    - portfolio/position_sizing.py
      - calc_position_sizes: 各配分方式（risk_based / equal / score）に応じた発注株数算出。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を考慮した保守的見積り、端数処理ロジックを実装。
  - 研究/分析モジュール
    - research/factor_research.py
      - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー系ファクター計算を実装（MA200, ATR20 等）。
    - research/feature_exploration.py
      - calc_forward_returns: 将来リターン（複数ホライズン）計算。
      - calc_ic: スピアマンランク相関（IC）計算。データが不足する場合のガード。
      - factor_summary, rank: 基本統計量とランク付けユーティリティ（外部ライブラリに依存しない実装）。
    - research/__init__.py に必要エクスポートを追加。
  - AI / ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルに書き込む処理を実装。
      - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC ベースで計算する calc_news_window。
      - 銘柄ごとに記事を集約し、1 銘柄あたり最大記事数・最大文字数でトリム。
      - 最大 20 銘柄を一度に送るバッチ処理、429/ネットワーク/5xx に対する指数バックオフリトライ。レスポンス JSON のバリデーション、スコアの ±1.0 クリッピング、部分失敗時の DB 保護（対象コードのみ delete→insert）などフェイルセーフ設計。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
  - ユーティリティ
    - utils/process_priority.py
      - set_process_priority(level): Windows と POSIX を抽象化してプロセス優先度を設定（psutil 利用）。サポート外 OS ではスキップして警告。
      - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を最初の N コアに固定するユーティリティ。権限や未サポート環境では警告してスキップ。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。
      - 指定期間の system_status, trade_logs, risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計して人間向けレポートを出力。
      - 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を実装。DB が存在しない場合やテーブル欠損時の耐障害性あり。
  - パッケージメタ
    - __init__.py に __version__ = "0.1.0" を追加。

- Changed
  - （初回リリースのため変更履歴はありません）

- Fixed
  - config._parse_env_line: export プレフィックス、引用符付き値内のバックスラッシュエスケープ、インラインコメント扱いの改善など、.env の実用的なパースを実装（既存の問題の回避目的で堅牢化）。
  - position_sizing / risk_adjustment: 価格欠損時のスキップやログ出力を追加して誤った計算を防止。

- Security
  - OpenAI API キー等の秘密情報は環境変数経由で扱う設計。自動ロード時に OS 環境変数を .env の上書きから保護する仕組み（protected set）を導入。

注記（運用者向け）
- 監視プロセスは run_monitoring.py により起動し、MONITOR_POLL_INTERVAL でポーリング間隔を制御できます（無効値はデフォルト 60 秒にフォールバック）。
- run_execution.py は KABUSYS_ENV により paper_trading と live を区別し、paper_trading 時にはデータ・注文処理を本番と分離します（PAPER_TRADING_SQLITE_PATH を利用）。
- config.Settings の以下の主要な環境変数に注意してください（一部抜粋）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - OPENAI_API_KEY
  - MONITOR_POLL_INTERVAL
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - LOG_LEVEL
- DuckDB 側のテーブル（prices_daily, raw_financials など）と SQLite のスキーマ（monitoring / trade_logs / risk_logs / ai_scores 等）は、運用前に初期化しておく必要があります。run_execution/run_monitoring の起動は、これらの DB ファイルが適切に配置されていることを前提とします。

今後の予定（例）
- 戦略・エンジンの統合テスト追加
- 銘柄ごとの lot_size を銘柄マスタで管理する拡張
- ai/news_nlp の並列化最適化とエラーハンドリング強化
- モニタリング・ロギングの構成改善とメトリクス外部送信（Prometheus 等）

--- 
（本 CHANGELOG は現行コードベースから推測して作成しています。実際のリリースノートとして公開する際は日付や項目をプロジェクト方針に合わせて調整してください。）