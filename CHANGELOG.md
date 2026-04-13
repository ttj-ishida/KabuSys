# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  

なお、本ファイルはコードベースの内容から推測して作成した初期リリース記録です。実際のコミット履歴に基づくものではありません。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-13

Added
- コア
  - パッケージ初期版を追加。パッケージメタ情報は `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたデータパイプラインを前提とした設計。
  - 環境変数ベースの設定管理を `kabusys.config.Settings` で提供。
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）。
    - `.env` の行パーサは quote や export 形式、インラインコメント処理に対応。
    - 必須環境変数未設定時は明確なエラーを発生（`_require`）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（有効値チェック）。
    - デフォルトのファイルパス設定:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
      - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
      - PID_FILE_PATH: data/execution.pid
      - KILL_FLAG_PATH: data/kill.flag

- 実行・監視スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（本番 DB と分離）を使用するロジックを組み込み（コメントに MockBrokerClient の利用方針を明記）。
    - 起動時にプロセス優先度を設定（`kabusys.utils.process_priority.set_process_priority("high")`）。
    - Execution エンジンの構成要素（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てとセッション実行。
    - RiskManager に初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）を渡す例を提供。

  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視（monitoring）では環境にかかわらず本番の sqlite_path を使用する旨を明記。
    - 監視ループ内で `monitor.check_once()` の例外を捕捉してログ出力し、次回ポーリングへ継続するフェイルセーフ設計。
    - KeyboardInterrupt による終了処理と DB 接続クローズを実装。

- モジュール: portfolio
  - `portfolio_builder.py`
    - 銘柄候補選定（スコア降順、同点タイブレークに signal_rank）: `select_candidates`。
    - 等金額配分: `calc_equal_weights`。
    - スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING）: `calc_score_weights`。
  - `risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap`（当日売却予定銘柄はエクスポージャー計算から除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた資金乗数を返す `calc_regime_multiplier`（bull/neutral/bear のマッピング、未知のレジームは警告を出して 1.0 でフォールバック）。
  - `position_sizing.py`
    - 複数の配分方式に対応する株数決定ロジック `calc_position_sizes`（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金でスケーリング）、手数料・スリッページを考慮する cost_buffer を実装。
    - スケールダウン時に残差を lot 単位で再配分するアルゴリズムを実装。

- 研究（research）
  - `research.factor_research`
    - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`。DuckDB の prices_daily / raw_financials を利用してモメンタム、ATR、平均売買代金、PER/ROE 等を計算。
    - 長期 MA200 や ATR のウィンドウサイズ等は定数で定義され、ウィンドウ不足時には None を返すことで堅牢化。
  - `research.feature_exploration`
    - 将来リターン計算 `calc_forward_returns`（複数ホライズンをサポート、入力検証あり）。
    - スピアマンランク相関で IC を計算する `calc_ic`（欠損や十分なサンプル数がない場合に None を返す）。
    - ランク付けユーティリティ `rank`（同順位は平均ランク）。
    - ファクター統計サマリ `factor_summary`（count/mean/std/min/max/median）。

- AI / NLP
  - `ai.news_nlp`
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - 処理の特徴:
      - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
      - 1 銘柄当たり最大記事数・最大文字数でトリム（トークン肥大化対策）。
      - 最大 20 銘柄 / チャンクで API を呼び出す（_BATCH_SIZE=20）。
      - レスポンスのバリデーション、スコアを ±1.0 にクリップ。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ (リトライ上限) を備える設計（概念的に説明あり）。
      - OpenAI API キー未設定時は明確に ValueError を送出。
      - DuckDB 側で部分失敗時に既存スコアを保護するため、対象コードに対して置換（DELETE→INSERT）する方針を明記。

- ツール
  - `tools.paper_verification_report.py`
    - Paper Trading 検証レポート生成ツール。
    - SQLite（paper_trading）データベースを読み、システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計して標準出力へ整形出力。
    - パスや期間指定用 CLI 引数を提供（--from / --to / --db）。
    - パスが存在しない場合やテーブルがない場合に安全に "N/A" 等で扱うフォールバック処理。
    - 合格基準（阈値）を定義:
      - 稼働率 >= 99%
      - 注文成立率 >= 90%
      - 送信率 >= 95%
      - P95 レイテンシ <= 200 ms

- ユーティリティ
  - `utils.process_priority`
    - Windows / POSIX（Linux / macOS / FreeBSD）間の違いを吸収してプロセス優先度設定 `set_process_priority(level)` を提供。
    - CPU affinity 設定 `set_cpu_affinity(cpu_count)` を提供（必要に応じて N コアにピン止め）。
    - 権限不足や未対応 OS の場合には警告を出して失敗をスキップする堅牢性を持つ。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / 注意事項
- OpenAI を使う機能（ai.news_nlp）は API キーを必要とし、キー未設定時は ValueError を投げて処理を中断します。実運用では環境変数 OPENAI_API_KEY の設定を忘れないでください。
- `run_execution` は paper_trading 環境で paper 用 DB に書き込むよう設計されており、本番データと分離されます。テストや検証時に誤って本番 DB を上書きしないよう注意してください。
- .env 自動読み込みはプロジェクトルートを基準に行われます。プロジェクト配布後に期待通りに動作させるには .git または pyproject.toml が存在するか、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化してください。
- 一部関数は DuckDB や SQLite のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）を前提としています。実行前にスキーマ準備を行ってください。

ライセンス、貢献、リリース手順などは別途ドキュメントに記載してください。