CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
- なし

[0.1.0] - 2026-04-16
-------------------

Added
- 全体
  - 初期リリース。モジュール群を一通り実装し、自動売買・研究・検証・監視に必要な基盤機能を提供。
  - バージョン情報をパッケージルートに __version__ = "0.1.0" として格納（src/kabusys/__init__.py）。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動ロードを実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - export KEY=val 形式やクォート、コメントなどを考慮した堅牢な.envパーサ実装。
  - 環境変数による設定値アクセス用 Settings クラスを提供（J-Quants / kabu / LINE / DB / 監視閾値 / システム設定など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH など paper trading 関連設定の追加。

- 実行スクリプト
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - 実稼働/ペーパートレーディングを区別して専用SQLiteを使用（paper_trading時は data/paper_trading.db をデフォルト）。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading なら MockBroker が利用される想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル path による制御。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定。
  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB の初期化（monitoring 用テーブルを保証）と DuckDB 接続。
    - 停止フラグによる安全停止処理と例外ハンドリングでログ出力後に次のポーリングへ継続。

- 監視 / DB 初期化
  - init_monitoring_db を利用して監視テーブルの冪等な初期化を行う（run_* スクリプト両方で呼び出し）。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - マルチプラットフォーム向けプロセス優先度設定ユーティリティを提供（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
  - CPU affinity 設定関数 set_cpu_affinity を提供。
  - 権限不足や未対応 OS の際は安全に警告してスキップする実装。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - 候補選定 / 重み計算 (portfolio_builder.py)
    - select_candidates: スコア降順・タイブレークに signal_rank を用いる。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分へフォールバックし警告を出す。
  - セクター制限・レジーム乗数 (risk_adjustment.py)
    - apply_sector_cap: 既存保有を考慮したセクター集中上限チェック（"unknown" セクターは除外し上限を課さない挙動）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を返す（未知レジームは警告して 1.0 でフォールバック）。
  - ポジションサイズ計算 (position_sizing.py)
    - risk_based / equal / score の allocation_method に対応。
    - 単元株(lot_size)丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - cost_buffer による手数料・スリッページ保守見積りや残差を用いた追加配分ロジックを実装。
    - 価格欠損時のスキップやログ出力を考慮。

- 研究 (src/kabusys/research/*)
  - ファクター計算 (research/factor_research.py)
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け prices_daily / raw_financials を参照。
    - 200日移動平均、ATR、出来高指標、過去リターン（1M/3M/6M）などを計算。
    - ウィンドウ不足時の None 返却やデータスキャン範囲の最適化（calendar-day バッファ）を実装。
  - 特徴量探索 (research/feature_exploration.py)
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank / factor_summary: ties を平均ランクで扱うランク付けや、count/mean/std/min/max/median を算出する統計要約を提供。
  - research パッケージは zscore_normalize を外部モジュールから再エクスポート。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などの集計から稼働率・成功率・送信率・レイテンシ（P95）等を算出して標準出力へ整形レポートを出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 latency 200ms）に基づく PASS/FAIL 判定を実装。
    - DB が存在しない・テーブルがない場合に対する堅牢な例外処理を実装。
    - --from / --to / --db 引数で期間・DBを指定可能。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を集約して OpenAI API (gpt-4o-mini) へバッチ送信し銘柄別センチメントを ai_scores テーブルへ保存する設計を追加。
  - 実装上の特徴:
    - バッチサイズ、トークン肥大対策（記事数・文字数トリム）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、結果検証、スコアクリッピング（±1.0）、部分失敗時の局所的な置換戦略などを設計。
    - ニュース時間ウィンドウ計算ユーティリティ calc_news_window を実装（JST基準の前日15:00～当日08:30相当をUTCで計算）。
  - 注意: score_news 関数の続き実装が途中で切れている（コード断片が存在）ため、現状では未完成／実行不能な状態の箇所がある。実運用時は該当部分の完成・検証が必要。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- API キー（OpenAI 等）は環境変数から読み込む設計。コードにハードコードしないことを前提。

Notes / Migration / Known issues
- news_nlp.score_news がコードスニペットの途中で切れており（不完全）、ファイルをそのまま実行すると構文エラーまたは機能欠落が発生します。AI ニュース機能は設計は整っているものの、実装の続き（記事集約後の処理・API呼び出し・DB書き込み）を追加してください。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布パッケージや特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い手動で env を設定することを推奨。
- run_execution / run_monitoring は stop flag（data/stop_requested.flag）によるファイルベースのプロセス制御を行います。運用環境では data ディレクトリのパーミッション・存在を確認してください。
- process priority / cpu affinity は権限によって失敗する場合があり、その場合は警告ログを出して処理を継続します（失敗が致命的にならないよう配慮）。
- Paper Trading と Live 環境の DB は分離（paper_trading 用 SQLite を使用）されるため、検証データと本番データが混ざらないようになっています。

Environment variables（主なもの）
- KABUSYS_ENV (development | paper_trading | live)
- KABUSYS_DISABLE_AUTO_ENV_LOAD
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- PAPER_FILL_MODE (instant | partial | never | reject)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- OPENAI_API_KEY (news_nlp の API キー)

今後の予定（提案）
- news_nlp.score_news の未実装部分を完成させ、エンドツーエンドのテストを追加。
- パフォーマンス・ロギングの拡張（DuckDB クエリ時間計測、ExecutionEngine の詳細ログ等）。
- 単体テスト・CI の追加（特に portfolio/position_sizing のスケーリングロジックや research の SQL）、
  .env パーサの追加ケース（複雑なエスケープケース）を網羅するテスト。
- stocks マスタに単元株情報を持たせる等、position_sizing の lot_size を銘柄毎に対応する拡張。

もし CHANGELOG に追記してほしい項目（例えばリリース日変更、追加の既知問題、リリースノートの分割など）があれば教えてください。