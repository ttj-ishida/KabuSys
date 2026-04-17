Keep a Changelog
================

すべての重要な変更はこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。
リリースは YYYY-MM-DD 形式の日付付きで記載します。

[0.1.0] - 2026-04-17
-------------------

Added
- 初回リリース: KabuSys 基本機能群を追加。
  - 実行/監視スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB（data/paper_trading.db デフォルト）を使用し、本番 DB と完全分離して動作。
      - 停止フラグ (data/stop_requested.flag) を監視し、安全にエンジンを停止可能。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
      - ExecutionEngine はエンジンの PID を data/execution.pid に書き込む想定。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし、警告を出す。
      - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用（監視 DB の分離方針）。
      - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
  - 設定管理
    - config.Settings を追加。環境変数／.env ファイルから各種設定を取得するプロパティを提供。
      - 自動 .env ロード機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。.env/.env.local の読み込み順序および上書きルールを定義。
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - 各種検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL、PAPER_FILL_MODE（instant/partial/never/reject）などの妥当性チェック。
      - デフォルトパス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等。
      - CPU/MEM/DISK 閾値など監視関連設定用プロパティを追加。
  - .env パーサ/ローダ
    - export プレフィックス対応、クォート／バックスラッシュエスケープ対応、インラインコメント処理など堅牢なパースを実装。
    - override / protected（OS環境変数保護）機能を実装。
  - モニタリング DB 初期化ユーティリティ
    - monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - Portfolio 構築系（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルのソート（score 降順、同点時 signal_rank 昇順）。
      - calc_equal_weights, calc_score_weights: 等分配・スコア加重配分（スコア合計が 0 の場合は等分配にフォールバックして警告）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限ロジック（売却予定銘柄の除外や "unknown" セクター扱い）。
      - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear マップ）。
    - portfolio.position_sizing
      - calc_position_sizes: 発注株数決定（risk_based / equal / score）、単元株丸め、銘柄ごとの上限、aggregate cap（available_cash を超える場合のスケールダウン）や残差の lot 単位での再配分、cost_buffer による手数料・スリッページ見積りを実装。
  - 研究系（DuckDB ベース）
    - research.factor_research
      - calc_momentum, calc_volatility, calc_value: momentum / volatility / value ファクター計算を SQL（DuckDB）+ Python で実装。200 日移動平均や ATR 等を算出し、データ不足時は None を返す設計。
    - research.feature_exploration
      - calc_forward_returns: 複数ホライズンの将来リターン計算（入力検証あり）。
      - calc_ic, rank, factor_summary: IC 計算（Spearman 相関）、ランク付け（同順位は平均ランク）、ファクターの基本統計量算出。
    - research パッケージは zscore_normalize（kabusys.data.stats 由来）もエクスポート。
  - AI ニュース NLP（部分実装）
    - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ保存する設計を追加。  
      - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時のデータ保護方針（対象コードのみ DELETE→INSERT）などを想定。
      - OPENAI_API_KEY を参照。未設定の場合は例外を送出。
      - calc_news_window: JST→UTC 変換によるニュースウィンドウ算出ユーティリティを提供。
  - CLI ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。  
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシ等を算出し、PASS/FAIL を出力。閾値はソース内で定義（稼働率>=99%、P95<=200ms 等）。
      - --from/--to/--db オプション対応。DB 存在チェック、テーブル欠如時のフォールバック処理を実装。
  - ユーティリティ
    - utils.process_priority
      - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。権限不足や非対応 OS は警告でスキップ。
      - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアにピン留めする機能。引数検証と権限例外ハンドリングを実装。
  - パッケージ情報
    - kabusys.__init__ に __version__ = "0.1.0" を設定。

Changed
- 初期設計文書に基づく実装（PortfolioConstruction.md, StrategyModel.md 等の参照をソース内に明記）。DuckDB を主データソースとして SQL ベース処理を多用する設計に集約。
- 環境変数ロードの優先順位: OS 環境 > .env.local > .env を採用。OS 環境のキーは保護され、.env.local は override=True で上書き可能。

Fixed
- .env のパース強化により quoted 値やエスケープ、コメントの解釈ミスを修正。
- run_monitoring の MONITOR_POLL_INTERVAL 不正値処理を明確化（不正値で ValueError を避けるためデフォルトへフォールバックし警告出力）。
- calc_score_weights: スコア合計が 0 の場合に発生し得るゼロ除算を回避し、等金額配分へフォールバックして警告を出すように修正。

Security
- OpenAI API キーや各種シークレットは環境変数経由で取得する設計。未設定時は ValueError を投げる等、キー未設定を明示する挙動により誤ったキー露出を防止。

Notes / Implementation details
- DuckDB 接続を多数の研究/AI/レポート機能で利用します。DuckDB のバージョン互換性（executemany の挙動等）に注意して実装（ソース内にワークアラウンドの注記あり）。
- Paper Trading と本番 DB の分離を厳密に行い、誤って本番 DB にテスト注文を書き込まないよう設計。
- 一部モジュール（ai.news_nlp）は長い処理を伴うため、API レート制限や部分失敗の保護を重視した設計になっています。実運用前に OpenAI の利用制約に合わせた実装検証が必要です。

Acknowledgements
- 本リリースは初期実装をまとめたものです。今後、テスト補強、例外ケースの追加カバレッジ、ドキュメント整備（API 使用例、設定例、運用手順）を進めます。