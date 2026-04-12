# CHANGELOG

全ての変更は Keep a Changelog の形式に準拠しています。  
リリース日: 2026-04-12

## [0.1.0] - 2026-04-12

### Added
- 初回公開リリース。
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を利用したデータアクセスと一部のユーティリティを導入。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - KABUSYS_ENV による paper_trading サポート（paper_trading 時は MockBroker を利用し、SQLite は data/paper_trading.db を使用して本番 DB と分離）。
    - プロセス優先度を起動直後に "high" に設定。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine.run_session() 呼び出しを実装。
    - DuckDB 接続を受け取り分析用 DB を併用。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトへフォールバックして警告を出力）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用（監視 DB を本番と分離しない設計）。
    - 起動時にプロセス優先度を "high" に設定。KeyboardInterrupt による優雅な停止処理と DB 接続クローズを実装。
- 設定管理
  - kabusys.config
    - .env 自動読み込み機構を追加（プロジェクトルートの .env / .env.local を自動読込。CWD に依存せず __file__ からプロジェクトルートを探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - 洗練された .env パーサー実装を追加（コメント・export 形式・クォート・バックスラッシュエスケープなどに対応）。
    - Settings クラスを実装。J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定など多数のプロパティを提供（例: sqlite_path, duckdb_path, paper_sqlite_path, PAPER_FILL_MODE バリデーション、KABUSYS_ENV 検証など）。
    - settings = Settings() を公開。
- ポートフォリオ構築
  - kabusys.portfolio
    - portfolio_builder: 銘柄候補選定 (select_candidates)、等金額・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を実装。score が全て 0 の場合は等配分にフォールバック（WARNING）。
    - risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。unknown セクターの扱い、レジームフォールバックを明記。
    - position_sizing: 各銘柄の発注株数算出ロジック calc_position_sizes を実装。risk_based / equal / score の allocation 方法、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer の考慮等を含む。
- 監視・ユーティリティ
  - kabusys.utils.process_priority
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォームに対する安全なフォールバックとログ出力を実装。
- 研究・リサーチ
  - kabusys.research
    - factor_research: モメンタム・ボラティリティ・バリュー系ファクター計算 (calc_momentum, calc_volatility, calc_value) を DuckDB 上の prices_daily / raw_financials を参照して実装。
      - モメンタム: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
      - ボラティリティ: ATR20、相対 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）。
      - バリュー: PER / ROE（最新財務データ取得ロジックを含む）。
    - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、統計サマリー (factor_summary)、ランク関数 (rank) を実装。外部依存を避け標準ライブラリのみで実装。
    - research パッケージの __all__ を整備し、zscore_normalize を data.stats から再エクスポート。
- AI / ニュース
  - kabusys.ai.news_nlp
    - raw_news テーブルを基に OpenAI API (gpt-4o-mini) を用いたニュースのセンチメントスコアリング機能を実装（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を内部的に UTC に変換）を実装（calc_news_window）。
    - バッチ処理（最大 20 銘柄/リクエスト）、入力トークン肥大化対策（記事数上限・文字数上限）、API エラーに対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時のテーブル保全（対象コードのみ差し替え）などを備える。
    - OpenAI クライアント初期化・API キー解決ロジックを実装（api_key 引数または OPENAI_API_KEY 環境変数）。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用の検証レポート生成コマンドラインツールを追加（python -m kabusys.tools.paper_verification_report）。
    - 検証指標: 稼働率 (uptime), 注文成功率 (fill_rate), 送信率 (send_rate), レイテンシ P95 などを算出。
    - デフォルト DB は data/paper_trading.db。--from / --to / --db オプションで期間・DB を指定可能。
    - 空データ・OperationalError に対する堅牢な扱いと N/A 表示を実装。
    - 判定基準（閾値）を定義: 稼働率 99%、成立率 90%、送信率 95%、P95 200ms。
- その他
  - Monitoring DB 初期化ユーティリティ (monitoring_db.init_monitoring_db) の呼び出しを各起動スクリプトで行い、監視テーブルが存在することを保証（冪等）。
  - 多数の既存関数で詳細なログメッセージとデバッグ情報を追加。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- OpenAI API キー取得は環境変数または明示的引数で行う必要があり、未設定時には ValueError を送出して意図しない API 呼び出しを防止。

---

注:
- この CHANGELOG はリポジトリ内のコードから推測して作成したものであり、実際の変更履歴（コミットメッセージ等）と差異がある可能性があります。必要に応じて日付や詳細をプロジェクトの実際の履歴に合わせて調整してください。