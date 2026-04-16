# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

- （なし）

---

## [0.1.0] - 2026-04-16

初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ本体
  - kabusys パッケージの初期バージョン（__version__ = "0.1.0"）。

- 設定・環境変数管理（kabusys.config）
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得するプロパティを提供。
  - 自動 .env ロード機能
    - プロジェクトルート（.git または pyproject.toml を探索）を検出して .env と .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは `export KEY=val`、引用符付き値、コメント（インライン含む）などの一般的構文に対応。
    - OS 環境変数を保護するための上書き制御（protected キー機能）を実装。
  - 各種設定プロパティを追加（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値, LOG_LEVEL, KABUSYS_ENV 等）。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
  - env 値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）。

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - process priority を高く設定して起動するユーティリティ呼び出しを組み込み（kabusys.utils.process_priority.set_process_priority）。
    - DB 接続:
      - 通常は settings.sqlite_path を使用。
      - KABUSYS_ENV=paper_trading の場合、paper 用専用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - BrokerClientFactory により実環境 / モック（paper_trading）を切り替え可能。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した安全停止処理を実装。
    - RiskManager の初期設定値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）および initial_portfolio_value を broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告出力の上デフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する実装。
    - 停止フラグ検出でループを終了、例外・KeyboardInterrupt に対する安全なクリーンアップ（DB クローズ等）を実装。

- 監視 DB 初期化ユーティリティ
  - monitoring_db の初期化（init_monitoring_db）を呼び出す箇所を run_execution / run_monitoring に組み込み、監視テーブルが存在することを保証（冪等）。

- ユーティリティ：プロセス優先度 / CPU affinity（kabusys.utils.process_priority）
  - set_process_priority(level: "high"|"normal"|"low")
    - Windows と POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。
    - アクセス権限不足などの例外はログ警告に変換して継続。
  - set_cpu_affinity(cpu_count: int | None)
    - 指定コア数にプロセスをピンニング。引数検証と例外処理あり。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、signal_rank でタイブレークして上位 N を選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で重みを計算。全銘柄スコアが 0 の場合は等分割にフォールバック（WARNING）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、超過セクターの新規候補を除外。既知でないセクター ("unknown") は除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 でフォールバック（警告ログ）。
  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method は "risk_based" / "equal" / "score" をサポート。
    - risk_based: risk_pct, stop_loss_pct を用いたポジション算出。
    - equal/score: weight を用いた割当。lot_size（単元株）で丸め。
    - aggregate cap と cost_buffer を考慮したスケールダウンロジックと余剰配分（fractional remainder に基づく lot 単位での再配分）を実装。
    - price 欠損時のスキップや安全弁（_max_per_stock）を実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を DuckDB の prices_daily を使って計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20/atr_pct）、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を適切にハンドル。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS 欠損や 0 は None）。
    - 各関数は DuckDB 接続を受け取り SQL ベースで高速に計算。
  - feature_exploration
    - calc_forward_returns: target_date から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons のバリデーションあり。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。利用可能レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクで処理（丸めで ties の誤検出を軽減）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルへ書き込む設計を実装。
  - 主な仕様（実装済み/設計記載）:
    - ニュース収集ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC で処理）。
    - 銘柄ごとに記事を集約（最新 N 記事、文字上限でトリム）。
    - 最大バッチサイズ 20、JSON Mode を想定した出力形式（{"results": [{"code":"XXXX","score":0.0}, ...]}）。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ（上限 3 回）。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分置換方式で ai_scores を更新（他銘柄のスコア保護）。
    - OpenAI API キー解決（引数優先、未指定は OPENAI_API_KEY 環境変数を参照、未設定時は ValueError）。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン: python -m kabusys.tools.paper_verification_report）。
    - CLI オプション: --from, --to（YYYY-MM-DD）、--db（DB パス）。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB パス指定可（デフォルト data/paper_trading.db）。
    - 指標と閾値:
      - 稼働率 (uptime) 閾値: 99.0%
      - 注文成功率(fill rate) 閾値: 90.0%
      - 送信率(send rate) 閾値: 95.0%
      - P95 レイテンシ閾値: 200 ms
    - system_status / trade_logs / risk_logs から様々な指標（稼働率、注文件数・成功率、リスク却下数、平均/最大/P95 レイテンシ）を算出し、PASS/FAIL 判定を出力。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Security
- OpenAI API キー等の機微情報は Settings 経由で環境変数に依存する設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止可能。

### Notes / Migration
- PAPER_TRADING 環境は paper 用 SQLite を使用し、本番の monitoring DB と完全分離されています。Paper 検証やテストを行う際は適切な環境変数（KABUSYS_ENV=paper_trading）や PAPER_TRADING_SQLITE_PATH を設定してください。
- run_monitoring は常に本番 sqlite_path（settings.sqlite_path）を参照します（監視データは環境に依存しない設計）。
- .env の自動読み込みはプロジェクトルート検出に依存します。配布後やテスト実行時に root が特定できない場合は自動読み込みがスキップされます。必要に応じて環境変数を直接設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して挙動を制御してください。

---

今後の予定（例）
- ai.news_nlp の完全なバッチ送信・DB 更新パスの追加実装とテスト強化
- ExecutionEngine / RiskManager の追加チューニングと単体テスト
- DuckDB を用いた研究モジュールのベンチマークと最適化

もし CHANGELOG に追記したい差分や日付修正、あるいはリリースノートの細分化（セキュリティ修正 / 互換性ブレイク等）をご希望であれば教えてください。