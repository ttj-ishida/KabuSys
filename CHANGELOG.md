CHANGELOG
=========

すべての重要な変更をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （なし）現在のリポジトリは v0.1.0 リリース相当の状態です。将来の変更はここに記載してください。

0.1.0 - 2026-04-12
------------------

Added
- 基本アプリケーション初期実装を追加。
  - パッケージ情報: kabusys/__init__.py に __version__ = "0.1.0"。
- 設定管理 (kabusys.config)
  - 環境変数および .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパースを堅牢化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 環境変数の保護（OS 環境変数は protected として上書きを防止）を実装。
  - Settings クラスを提供し、各種設定値（DBパス、PIDファイル、監視閾値、PAPER_FILL_MODE 等）の取得とバリデーションを行う。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェックを実装。
    - paper_trading 用 DB パス PAPER_TRADING_SQLITE_PATH の取得をサポート。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装。
    - プロセス優先度を最初に "high" に設定する仕組みを組み込み（utils/process_priority 経由）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行。
    - リスク管理のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値に broker.get_available_cash() を使用。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼び出して監視テーブルが存在することを冪等に保証（monitoring 用テーブルの準備）。

- プロセスユーティリティ (kabusys.utils.process_priority)
  - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows は psutil の HIGH_PRIORITY_CLASS、POSIX 系は nice 値を使用）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
  - 権限不足や未実装環境では警告を出してフォールバックする安全設計。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: シグナル選定・重み計算を実装
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバックして警告）
  - risk_adjustment: セクター集中制限・レジーム乗数
    - apply_sector_cap: 既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外（unknown セクターは制限対象外）。
      - 当日売却予定の銘柄をエクスポージャー計算から除外できるオプションを提供。
      - 価格欠損時の注意点（TODO コメントとしてフォールバック価格提案）を含む。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックして警告。

  - position_sizing: 発注株数計算・制限ロジック
    - allocation_method ("risk_based", "equal", "score") をサポート。
    - risk_based: 損切り率 stop_loss_pct と risk_pct からポジションサイズを算出し、max_position_pct や lot_size（単元）で丸める。
    - equal/score: ウェイトに基づく割当て、max_utilization（ポジション内上限）を考慮。
    - aggregate cap: 全銘柄の合計投資額が available_cash を超えた場合はスケールダウンし、端数を lot_size 単位で再配分するロジックを実装（fractional remainder に基づく再配分で再現性確保）。
    - cost_buffer による手数料・スリッページ保守見積りをサポート。

- 研究モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（cnt_200 に基づく十分データ判定）を DuckDB 上で高速取得。
    - calc_volatility: ATR(20), 相対ATR, 20日平均出来高、出来高比率を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から最新財務データを結合して PER / ROE を算出（EPS が 0 の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一度のクエリで取得。horizons のバリデーション（正の整数かつ <=252）を行う。
    - calc_ic: スピアマンのランク相関（IC）を実装。欠損や ties を考慮し、有効レコードが 3 未満なら None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - research.__init__ から主要関数をエクスポート（zscore_normalize は data.stats から取り込み）。

- ニュース NLP（AI）スコアリング (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析して ai_scores テーブルへ書き込む処理を実装。
  - 処理フロー:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
    - 記事を銘柄ごとに集約（最大記事数・文字数でトリム）。
    - 最大 _BATCH_SIZE=20 銘柄ずつ API へバッチ送信。429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライする仕組み（上限あり）。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、成功した銘柄のみ ai_scores に置換（DELETE→INSERT）して部分失敗時に既存スコアを保護。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
  - JSON モードや出力フォーマット（厳密な JSON）に関するプロンプト制約を採用。

- コマンドライン / ツール
  - tools/paper_verification_report.py を追加。paper_trading DB を読み取り、以下指標を算出してコンソール出力する。
    - システム稼働率（system_status テーブル）、注文成功率 / 送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）。
  - レポートには Pass/Fail 判定基準を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
  - コマンドライン引数 --from/--to/--db をサポート。DB 存在チェックや SQLite の OperationalError に対するフォールバック処理を含む。

Changed
- なし（初回リリース）

Fixed
- 監視ループで time.sleep に渡すポーリング間隔が 0 以下だと ValueError になる問題を想定し、_get_poll_interval で 1 未満の値を不正としてデフォルトにフォールバックする実装を追加。
- DuckDB に対する executemany の引数が空配列だと失敗する制約を考慮し、書き込み前のパラメータ空チェックに言及（news_nlp にコメントとして注意点を保持）。

Notes / Known issues / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過少見積りとなり期待するブロックが機能しない可能性がある（TODO：前日終値や取得原価でのフォールバックを検討）。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS 上では警告を出してスキップする実装。実際の環境では適切な権限での実行を推奨。
- news_nlp は OpenAI API に依存するため、API レートやコスト、レスポンス安定性に注意が必要。部分失敗時にスコアの保護を行うが、完全な成功の保証はない。
- research モジュールは DuckDB の prices_daily / raw_financials を前提としている。データ品質（欠損・行数不足）に応じて None を返す設計になっている。
- 現状の単元ロジックは全銘柄共通の lot_size を想定している（将来的には銘柄別 lot_map を受け取る設計へ拡張予定）。

Security
- 重要な API キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）は Settings で required にしており、未設定時に ValueError を投げることで誤った起動を防止します。環境変数の取り扱いには注意してください。

Authors
- 初期実装: 開発者（リポジトリ内コメント・コード構成に基づく）

―――

今後のリリースでは、各モジュールのテストカバレッジ、エラー処理の強化、価格フォールバック、銘柄別単元対応、OpenAI 呼び出しの耐障害性強化（バッチの永続化/再試行等）を予定してください。