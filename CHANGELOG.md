# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、ソースコードから推測できる機能追加・設計意図・既知の制約をまとめたものです。

全般的注意:
- 日付はソース解析日（2026-04-13）を使用しています。実際の公開日やバージョン管理履歴に合わせて調整してください。
- 記載はソースの実装に基づく推測であり、外部仕様や運用手順は別途ドキュメントをご参照ください。

## [Unreleased]
（今後の変更を記載）

## [0.1.0] - 2026-04-13
初回リリース。以下の主要コンポーネントと機能を実装しています。

### Added
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0"

- 環境設定 / ロード (.env)
  - kabusys.config
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
    - 読み込み時に OS 環境変数を保護（上書き防止）する仕組み。
    - export プレフィックス、クォート文字列、インラインコメント等を丁寧にパースする独自パーサ実装。
    - 必須環境変数取得用の _require() を提供（未設定時は ValueError を送出）。
    - 各種設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須値
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等のデフォルトパス
      - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）
      - KABUSYS_ENV のバリデーション（development|paper_trading|live）
      - ログレベル検証、PID/KILL フラグ関連パス、閾値（CPU/MEM/DISK）等

- 実行エントリ / デーモン系
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト: 60 秒）。
      - 0 以下や不正値はデフォルトにフォールバックし、警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視 DB は環境に依存しない）。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う（utils を使用）。
    - DB 初期化（init_monitoring_db）および DuckDB 接続を確立し、例外時も安全にクローズ。

  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離（data/paper_trading.db がデフォルト）。
    - MockBrokerClient を使用することでペーパートレードを完全に隔離して検証可能（BrokerClientFactory により生成）。
    - 起動時にプロセス優先度を "high" に設定。
    - 依存コンポーネントの組み立てを行い ExecutionEngine.run_session() を起動。
    - RiskManager に既定の RiskConfig を設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。initial_portfolio_value はブローカーの get_available_cash() を使用。
    - 監視テーブルが存在することを保証するため init_monitoring_db を実行（冪等）。

- モニタリング DB ユーティリティ
  - init_monitoring_db を用いて監視用テーブルの初期化を保証（monitoring サブパッケージ）。

- ユーティリティ
  - kabusys.utils.process_priority
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティ。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や非対応環境では警告ログを出して安全にスキップ。

- ポートフォリオ構築
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルを score 降順、タイブレークに signal_rank を使用して最大 max_positions を選択。
    - calc_equal_weights: 等金額配分 (1/N) を計算。
    - calc_score_weights: スコア加重（総和が 0 の場合は等金額にフォールバックし警告を出力）。

  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター別時価を計算し、1 セクターの上限 (max_sector_pct) を超える場合にそのセクターの新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上で 1.0 にフォールバック。
    - 実装は純粋関数（DB 参照なし）。

  - kabusys.portfolio.position_sizing
    - calc_position_sizes:
      - allocation_method = "risk_based" / "equal" / "score" をサポート。
      - risk_based: risk_pct と stop_loss_pct から個別目標株数を算出。
      - equal/score: weight を用いて per-position 上限・aggregate cap 等を考慮して発注株数を算出。
      - 単元（lot_size、デフォルト 100）で丸め、price が無効な銘柄はスキップ。
      - aggregate cap 超過時はスケーリングし、余剰キャッシュで fractional remainder に基づき lot 単位で追加配分するロジックを実装。
      - cost_buffer によりスリッページ/手数料を保守的に見積もる。
      - TODO コメント: 銘柄ごとの lot_size や price のフォールバック改善点を明示。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離率を計算（DuckDB で SQL 実行）。
    - calc_volatility: 20 日 ATR、ATR 比、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算。
    - 各関数は大量データ走査に配慮しスキャン範囲にバッファを持たせている（パフォーマンス考慮）。

  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）で将来リターンを算出。horizons の検証（正整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。レコード不足や分散ゼロは None を返す。
    - rank: 同順位は平均ランクで処理（round(v, 12) による丸めで ties を安定検出）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を算出。

  - リサーチ関数群は DuckDB 接続を受け取り、prices_daily/raw_financials 等のテーブルのみを参照（本番 API にアクセスしない設計）。

- ニュース NLP / AI スコアリング
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI (gpt-4o-mini) を用いたセンチメントスコアを ai_scores に書き込む処理を実装。
    - 処理フロー:
      - target_date ベースのニュースウィンドウ計算（JST 指定 → UTC に変換）。
      - 1 銘柄あたり最大記事数 / 文字数でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄ずつバッチ送信。
      - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフリトライ（_MAX_RETRIES）。
      - レスポンス検証、スコアを ±1.0 にクリップ。
      - 成功分のみ ai_scores に置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）することで部分失敗時の既存データ保護を実現。
    - API キーは引数か環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
    - 設計方針としてルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない実装。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプト（CLI）。
    - コマンド例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
    - 指標と閾値:
      - 稼働率 (uptime) >= 99%
      - 注文成功率 (fill_rate) >= 90%
      - 送信率 (send_rate) >= 95%
      - P95 レイテンシ <= 200 ms
    - P95 計算、各種 SQL クエリ（system_status, trade_logs, risk_logs）に基づく集計、N/A 処理、判定ロジックを実装。
    - 出力は標準出力に整形して印字。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーなどの機密情報は環境変数経由で扱う設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。

### Notes / Known limitations / TODOs
- position_sizing: price が欠損（0.0）の場合にエクスポージャー過小見積りやスキップが発生する旨の TODO コメントが存在。前日終値等のフォールバック導入が想定されている。
- 将来的な拡張点として銘柄別の lot_size やさらに詳細な手数料・スリッページモデルの導入が示唆されている。
- Process priority / CPU affinity の設定は権限不足や未対応プラットフォームではスキップされる（警告）。
- ai/news_nlp の処理は API 呼び出しとコストに依存するため、本番運用ではレート管理・費用管理が必要。

---

この CHANGELOG はソースコード内の実装と docstring コメントに基づいて作成されています。追加のリリース、バグ修正や API 仕様の変更がある場合は、本ファイルに追記してください。