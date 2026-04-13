# Changelog

すべての著名な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

すべての日付はリリース日です。

## [0.1.0] - 2026-04-13

初回公開リリース。

### 追加 (Added)
- パッケージ全体
  - kabusys 初期バージョンを追加。バージョンは __version__ = "0.1.0"。
  - モジュール群（execution / monitoring / portfolio / research / ai / tools / utils 等）を実装。

- 実行エントリポイント
  - run_execution.py を追加。ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient による分離された検証が可能。
    - 実行前にプロセス優先度を "high" に設定（set_process_priority）。
    - DuckDB および SQLite 接続を確立し、監視用テーブルが存在することを保証する init_monitoring_db 呼び出し（冪等）。
    - ExecutionEngine の構成要素（Broker, OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立てて run_session を実行。
    - RiskManager に対するデフォルト設定値を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。

- 監視エントリポイント
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はログ警告の上でデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず「本番」用の sqlite_path を使用する設計。
    - プロセス優先度設定、DB 初期化（init_monitoring_db）、例外ハンドリング（個々の check_once() の例外はログ化して次回ポーリングへ継続）、KeyboardInterrupt による正常終了処理を実装。

- 設定管理
  - config.py を追加。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）と、OS 環境変数の保護（上書き制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント）の堅牢なパーサを実装。
    - Settings クラスで主要な環境変数をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、しきい値など）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（許容値以外は ValueError）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア順ソートと上位 N 選定、タイブレークは signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重配分（全スコアが 0 の場合は等金額配分にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有を基にセクター単位の上限を適用。`unknown` セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返却（未知レジームは警告後に 1.0 フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap・cost_buffer を考慮したスケーリングと残差の再配分ロジックを実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) を吸収し psutil 経由で優先度を設定。権限不足や未対応 OS の場合は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に固定する機能（引数 None で無効化）。エラー時は警告ログでスキップ。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、流動性、PER/ROE 等）を計算する関数を追加。
    - SQL ウィンドウ関数と行数チェックによる欠損制御を行う実装。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズンに対応した将来リターン算出（入力検証あり）。
    - calc_ic / rank / factor_summary: IC（Spearman ランク相関）計算、ランク変換、統計サマリを標準ライブラリのみで実装。ties は平均ランクで処理。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI （gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む一連処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する calc_news_window。
    - API キー未設定時に ValueError を送出、バッチサイズ・トークン制限（記事数・文字数）・最大リトライ・指数バックオフ等の堅牢化を実装。
    - レスポンス検証、スコアの ±1.0 クリップ、部分的失敗時の既存スコア保護（書き込みは対象コードの限定 DELETE → INSERT）を想定した設計。
    - （注）大きな処理フローが含まれるため、外部 API 呼び出し失敗時はフェイルセーフで処理を継続する設計。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95レイテンシ、リスク却下数等の集計を実装。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。デフォルトは環境変数または data/paper_trading.db。
    - P95 算出、N/A 表示、各閾値（稼働率 >= 99% 等）の判定ロジックを実装。

### 変更 (Changed)
- 内部の堅牢性向上
  - .env パーサの強化（クォートされた値のエスケープ処理、インラインコメント処理、export プレフィックス対応）。
  - DuckDB / SQLite のクエリで欠損データ発生時に安全にフォールバックする try/except パターンを tools と research の関数で採用。

### 修正 (Fixed)
- 起動時のプロセス優先度設定の失敗をログ警告で穏やかに扱うように変更（権限不足や未対応 OS で例外を上げない）。
- calc_score_weights: 全スコアが 0 の場合にゼロ除算を回避し、等金額配分にフォールバックするよう修正（警告ログ追加）。

### 注意事項 / 既知の制約 (Notes / Known issues)
- .env 自動ロードはプロジェクトルートが特定できない場合スキップされる。テスト環境等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- news_nlp モジュールは OpenAI API に依存します。API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給する必要があります。
- position_sizing の価格欠損時（price が 0.0 や None）の扱いは現状簡易で、将来的にフォールバック価格（前日終値や取得原価）を導入する余地があります（TODO コメントあり）。
- research モジュールは DuckDB に格納された prices_daily / raw_financials テーブルに依存します。テーブルスキーマやデータが不足する場合は None を返す設計です。

### セキュリティ (Security)
- 特になし（初回リリース）。

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。必要であれば、各変更点について該当ファイル／関数名や行数などのより詳細な参照を追加します。