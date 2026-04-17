# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
バージョン番号はパッケージ内の __version__（現状: 0.1.0）に対応します。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-17

初回リリース。主要機能と実装の概要を記載します。

### Added（追加）
- 基本パッケージ情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 実行系・エンジン
  - run_execution 起動スクリプトを追加。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - Engine はスレッドで実行され、data/stop_requested.flag による外部停止制御をサポート。
    - デフォルトのリスク設定値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を導入。
    - PID ファイルパス管理（data/execution.pid）をサポート。

- 監視（Monitoring）
  - run_monitoring 起動スクリプトを追加。
    - プロセス優先度を "high" に設定してから監視を開始。
    - 監視ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は環境に関わらず本番 sqlite_path を使用して monitoring DB を初期化。
    - data/stop_requested.flag による停止制御をサポート。

- 設定・環境変数管理
  - Settings クラスを追加（kabusys.config）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定等）。
    - PAPER_FILL_MODE（paper_trading の MockBroker の挙動）を検証し、許容値（instant, partial, never, reject）以外は ValueError を送出。
    - 環境（KABUSYS_ENV）は development / paper_trading / live のみ許可。
    - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。優先順位: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パースの強化:
    - export プレフィックス対応、単/二重クォートの取り扱い（バックスラッシュエスケープ考慮）、インラインコメントの扱い（クォート有無での違い）をサポート。

- ユーティリティ
  - process_priority ユーティリティを実装（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加（アクセス権限や未サポート環境では警告を出してスキップ）。

- ポートフォリオ構築（Portfolio）
  - portfolio モジュールを追加（純粋関数群: DB 参照なし）。
    - portfolio_builder:
      - select_candidates: スコア降順で候補選定（同点は signal_rank 昇順でタイブレーク）。
      - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等配分へフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（max_sector_pct デフォルト 0.30）。"unknown" セクターは上限対象外。
      - calc_regime_multiplier: 市場レジームに応じた乗数（bull=1.0, neutral=0.7, bear=0.3、未知のレジームは警告の上 1.0 でフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、lot_size（単元）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積りと残余キャッシュ配分ロジックを実装。

- リサーチ（Research）
  - research モジュールを追加（DuckDB を使用、prices_daily / raw_financials テーブル参照、外部 API へアクセスしない設計）。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（MA200）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。真の true_range の NULL 伝播制御あり。
      - calc_value: raw_financials と結合して PER / ROE を計算（EPS が 0 または NULL の場合 PER は None）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
      - calc_ic: スピアマンのランク相関（IC）計算（有効レコードが少ない場合は None）。
      - factor_summary: count/mean/std/min/max/median を算出。
      - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸めで ties を安定検出）。

- AI / ニュース NLP
  - ai.news_nlp モジュールを追加（OpenAI を用いたニュースのセンチメントスコアリング）。
    - gpt-4o-mini を想定した JSON 出力形式で銘柄ごとのスコア（-1.0〜1.0）を生成。
    - スコアは ±1.0 にクリップ。
    - バッチ処理（1 回あたり最大 20 銘柄）と、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC 変換して使用）。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report を追加（コマンドラインツール）。
    - paper trading 用 SQLite（デフォルト data/paper_trading.db）から検証指標を抽出しコンソール出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルトの合格閾値を定義（例: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - --from / --to / --db オプションをサポート。

### Changed（変更）
- なし（初回リリース）

### Fixed（修正）
- なし（初回リリース）

### Notes（備考 / 実装上の注意）
- DB:
  - duckdb はリサーチ / analytics 用に使用。SQLite は監視 / execution 用に使用（paper_trading 環境では paper_sqlite_path に分離）。
- エラーハンドリング:
  - run_monitoring のループ内で check_once() が例外を投げてもループ継続し、ログを残して次ポーリングまで待機する設計。
  - process_priority / set_cpu_affinity は権限不足や未対応 OS では警告を出して静かにスキップ。
- セキュリティ:
  - .env を自動的に読み込む仕様だが、環境変数で上書きされる（OS 環境優先）。自動ロードを無効化するフラグを提供。

今後の予定（例）:
- ai.news_nlp の API 呼び出し部分の追加実装完了（スニペットは途中で切れているため、フル実装を予定）。
- Strategy / Execution のより詳細なユニットテストとシミュレーション整備。
- 単元株（lot_size）を銘柄毎に持つ拡張や、価格フォールバックロジックの追加（TODO コメントあり）。

---
参照: パッケージ内の各モジュール（kabusys/config.py, run_execution.py, run_monitoring.py, portfolio/*, research/*, ai/news_nlp.py, tools/paper_verification_report.py, utils/process_priority.py）に基づき作成。