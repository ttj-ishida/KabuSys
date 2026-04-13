KEEP A CHANGELOG — 日本語訳準拠

すべての変更は "Unreleased" ではなく初回公開としてまとめられています。

v0.1.0 — 2026-04-13
Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 設定 / 環境変数ローダー（src/kabusys/config.py）
  - .env 自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う機能を追加。  
    - 読み込み順: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーを実装（export 付き行、クォート付き文字列、インラインコメント対応）。
  - 必須環境変数取得ヘルパー _require() を追加（未設定時は ValueError）。
  - Settings クラスを導入し、J-Quants / kabuステーション / LINE / DB パス /監視閾値 / システム設定 等のプロパティを提供。
  - PAPER_FILL_MODE の検証、paper_trading 用 sqlite パス、pid/kill フラグ等の設定をサポート。

- 実行・監視起動スクリプト
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager（初期設定値付き）, Reconciler を組み合わせて ExecutionEngine を起動するワークフローを実装。
    - 起動時にプロセス優先度を High に設定。
    - DuckDB 接続を併用。
  - src/kabusys/run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう明示。
    - 起動時にプロセス優先度を High に設定し、SQLite / DuckDB をクリーンにクローズ。

- 監視 DB 初期化
  - monitoring_db 初期化呼び出しの利用（run_execution/run_monitoring で冪等に監視テーブルを確実に生成）。

- ユーティリティ: プロセス優先度 / CPU affinity（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装。Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定を行う。
  - 権限不足や未サポート環境では警告を出して安全にスキップする。
  - set_cpu_affinity(cpu_count) を追加。指定が None の場合は変更せず、異常値は ValueError。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights を実装（全スコア 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用するフィルタ関数（売却予定銘柄の除外、"unknown" セクターは上限除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップし未知レジームは警告とフォールバック）。
  - position_sizing.py
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分に対応した発注株数決定ロジック。
    - 単元株丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を使った保守的見積り、スケール時の残差処理（lot 単位での追加配分）などの実装。

- 研究 / ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER/ROE を算出（最新の報告日までの財務を銘柄毎に取り出す）。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（デフォルト 1/5/21 日）をまとめて取得するクエリ実装。ホライズン検証あり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。要件: 有効レコード >= 3。
    - rank, factor_summary: ランク変換・基本統計量計算を実装（外部依存なし、標準ライブラリのみ）。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize を data.stats から再輸出）。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出し、ai_scores テーブルへ書き込む処理を実装。
  - 特長:
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を計算する calc_news_window。
    - 1 銘柄あたりの最大記事数 / 最大文字数でトークン膨張対策。
    - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限 _MAX_RETRIES）。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分失敗時に他銘柄の既存スコアを保護するため置換対象 code を限定して DELETE→INSERT の安全な置換を行う方針。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得（未指定の場合は ValueError）。

- 管理用ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成ツールを追加。コマンドライン実行可能。
    - 指定期間（--from/--to）で paper_trading DB を読み、以下を算出:
      - システム稼働率（system_status）、総ポーリング数、エラー数
      - 注文成功率 / 送信率（trade_logs から）
      - リスク却下数（risk_logs）
      - API レイテンシ（平均・最大・P95）
    - P95 は独自実装で計算、閾値を満たさない場合は FAIL としてレポートに示す。
    - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
    - DB が存在しない場合はエラーメッセージを出力して終了。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes
- DB の扱いについて:
  - 監視は「本番用 sqlite_path（settings.sqlite_path）」を常に使用するよう設計されている点に注意。
  - paper_trading 環境では実行スクリプトが paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使って本番 DB と分離するため、テスト・検証が安全に行える。
- 外部依存:
  - DuckDB（duckdb パッケージ）をデータ分析に利用。
  - psutil を優先度・CPU affinity 設定に使用。
  - OpenAI Python SDK（OpenAI）をニュース NLP に使用（API キー必須）。
- 安全設計:
  - process priority / cpu affinity は権限不足や OS 非対応時に警告ログを出力してスキップするため、起動が失敗しにくい設計。
  - AI スコア処理は部分失敗時に既存のスコアを不必要に消さないよう配慮。

今後の予定（例）
- ポートフォリオ構築の拡張: 銘柄別 lot_size マスタ導入や、価格フォールバック戦略の追加。
- AI モジュールのバッチ最適化とエラーハンドリング拡張（長期的にはレート制限適応の改善）。
- ExecutionEngine のテストカバレッジ強化および broker のモック実装の充実。

参考: 各実装ファイルは src/kabusys 以下に配置されています。必要であれば各ファイル毎の詳細な変更点（関数シグネチャ、引数説明、返り値、例外挙動等）を別途追記します。