# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ定義 (kabusys.__version__) に合わせています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-16

初回リリース。本リリースでは自動売買システム「KabuSys」のコア機能群をまとめて追加しました。監視・実行ランタイム、ポートフォリオ構築ロジック、リサーチユーティリティ、AI ニューススコアリングの骨組み、設定ローダー、ユーティリティなどを含みます。

### Added
- 基本パッケージ情報
  - kabusys.__version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) の検知により安全にループ終了。
    - 常に本番用 sqlite_path を使用して監視データを記録（KABUSYS_ENV に依存しない）。
    - 起動時にプロセス優先度を設定（set_process_priority("high") を呼び出し）。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - paper_trading 環境では専用の MockBrokerClient と paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - 停止フラグ／PID 管理（data/stop_requested.flag, data/execution.pid）。
    - ExecutionEngine を周辺コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）と組み立てて起動。

- 設定管理
  - config.Settings クラスを追加
    - .env/.env.local 自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
    - OS 環境変数を保護する読み込みロジック（protected keys）。
    - .env パース機能強化（export プレフィックス、クォート内エスケープ、インラインコメント扱いなど）。
    - 各種プロパティ: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH）、PID/kill フラグ、閾値（CPU/MEM/DISK）等。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルを冪等に準備。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルのソート・上位選択（スコア降順、タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中制限に基づく候補除外。sell_codes（当日売却予定）除外対応。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - position_sizing
    - calc_position_sizes: リスクベース／等分配／スコア配分に基づく株数算出、単元株（lot_size）丸め、個別・合計上限（max_position_pct, max_utilization）、コストバッファ適用、リソース不足時のスケーリングと端数補正ロジックを実装。

- 研究（research）モジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算（DuckDB を使用）。
    - calc_volatility: ATR(20)・相対ATR・20日平均売買代金・出来高比率の計算。
    - calc_value: EPS/ROE から PER/ROE を計算（raw_financials の最新レコード参照）。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンの計算（可変ホライズン対応、入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - factor_summary / rank: ファクター統計要約・ランク変換ユーティリティ。
  - research.__init__ によるエクスポート（zscore_normalize を含む）。

- AI ニュース NLP（骨組み）
  - ai.news_nlp
    - raw_news から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む設計。
    - バッチ送信（最大 20 銘柄／回）、記事・文字数上限、429/ネットワーク/5xx に対する指数バックオフリトライ、結果検証、スコアクリップの方針を実装。
    - ニュース集計ウィンドウ計算（JST ベース → UTC 変換: 前日 15:00 JST 〜 当日 08:30 JST）。
    - API キーの解決ロジック（引数 / 環境変数 OPENAI_API_KEY）。
    - ※ 現状ファイル末尾が未完の可能性があり、完全なバッチ送信ロジック／テーブル書き込みの一部が実装途中の箇所が存在します（次バージョンで完了予定）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）。
    - 指標: 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - 判定基準（初期値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows と POSIX を吸収してプロセス優先度（high/normal/low）を設定。権限不足時は警告を出しスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を固定するユーティリティ（権限や非対応環境で警告を出しスキップ）。
  - utils パッケージ構成を追加。

### Changed
- .env 自動ロードの挙動を明確化
  - 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - 読み込み順序: OS 環境 > .env.local > .env（OS 環境は保護され上書きされない）。

### Fixed
- なし（初回リリース）

### Security
- 環境変数保護
  - .env 読み込み時に既存の OS 環境変数を protected として上書きを防止（意図しない資格情報の上書きを回避）。

### Notes / Migration
- データベース:
  - 監視用（monitoring）テーブルは init_monitoring_db により起動時に冪等的に作成されます。既存データベースがある場合でも安全に呼べます。
  - Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に分離して記録されます。PAPER_TRADING_SQLITE_PATH でパスを変更可能です。
- 監視ループ:
  - MONITOR_POLL_INTERVAL が無効値（0 や非整数）の場合はデフォルト 60 秒にフォールバックし、警告ログを出します。
- OpenAI API:
  - ai.news_nlp は API キーが必須。api_key 引数が与えられない場合は環境変数 OPENAI_API_KEY を参照します。
  - 大量/外部 API 呼び出しに関わるため、API 利用料やレート制限に注意してください。
- 実行優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限がない環境では警告が出ますが処理は継続します。

### Known issues / TODO
- ai/news_nlp モジュールの末尾が未完の部分があるため、完全なテーブル書き込みやエラーハンドリングの詳細は次リリースで確定予定。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価を利用する等）は TODO コメントとして残っています。
- 将来的に単元株数 lot_size を銘柄別に持たせる設計（stocks マスタ追加）を予定。

---

署名: KabuSys 開発チーム