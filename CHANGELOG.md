# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングに基づき記載しています。  

- 既知のバージョン: 0.1.0
- 日付はこのCHANGELOG作成時点（2026-04-17）を用いています。

なお、記載内容はリポジトリ内のソースコードから推測してまとめたものであり、実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

### Added
- なし（当面の開発は v0.1.0 までの機能を基準とします）。

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-17

初回リリース。自動売買システム KabuSys のコア機能群を提供します。

### Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を追加。
  - export KEY=val 形式やシングル/ダブルクォート、エスケープ、行内コメントに対応した .env パーサを実装。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 実行環境フラグ 等）。
  - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
  - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL 等）を追加。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを提供。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClientFactory 経由でブローカークライアントを生成。
    - paper_trading 環境では paper_sqlite_path を用いて本番 DB と分離。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag を確認して安全に停止するロジックを実装。
    - エンジンの PID ファイル出力（data/execution.pid）を想定。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor チェックをポーリングで回す簡易デーモン。ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（環境に依らず本番監視を行う設計）。
    - stop フラグファイルによる停止検知を実装。

- 実行ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority(level) を実装（high/normal/low）。
  - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（1 以上の値を検証）。
  - 権限不足や未実装 API に対するフォールバック（警告ログ）を実装。

- Execution サブシステム（実装の組立を示すファイル群）
  - BrokerClientFactory によるブローカ抽象化（paper_trading と live の切替を想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立フローを run_execution で示す。
  - RiskConfig でリスク制限パラメータを定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - RiskManager の初期化においてブローカーの get_available_cash() を初期ポートフォリオ値として使用。

- 監視 DB 初期化ユーティリティ（monitoring.monitoring_db）
  - run_* スクリプト内から監視テーブル存在を冪等に保証する init_monitoring_db を呼び出す。

- Portfolio モジュール（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - シグナル選別 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等重み calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合等重みへフォールバック）。
  - risk_adjustment.py
    - セクター上限適用 apply_sector_cap（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。
    - レジームに応じた投下資金 multiplier を返す calc_regime_multiplier（bull/neutral/bear、未知は警告して 1.0 フォールバック）。
  - position_sizing.py
    - 複数の配分方式に対応した calc_position_sizes（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、手数料/スリッページ見積り（cost_buffer）を考慮した安全な調整アルゴリズムを実装。
    - 負の価格や欠損価格のケースはスキップし、ログでデバッグ情報を出力。

- Research / データ処理（src/kabusys/research/*）
  - factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いた SQL 実行）。
    - 計算窓・欠損データへの取り扱い（ウィンドウ不足時に None を返す等）を明示。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、引数検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマン相関の実装、最低有効レコード数チェックあり）。
    - 基本統計量を返す factor_summary とランク変換 rank を実装（同順位は平均ランク）。
  - research.__init__ で主要 API をエクスポート（zscore_normalize を kabusys.data.stats から再エクスポート）。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini を想定）でスコアリングして ai_scores テーブルへ書き込む方針を実装。
  - バッチ処理（最大 BATCH_SIZE=20）、記事トリム（最大記事数/文字数）、429/5xx/タイムアウトに対する指数バックオフでのリトライ処理、レスポンスバリデーション、スコアの ±1.0 クリップなど堅牢な設計方針を追加。
  - OPENAI_API_KEY の必須化（引数または環境変数で解決）。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用の検証レポート生成ツールを追加。
  - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出。
  - デフォルトしきい値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を定義し、PASS/FAIL 判定を行う。
  - 日付フィルタオプション（--from/--to）と DB パスオプション（--db）をサポート。

### Changed
- なし（初回リリースのため変更履歴はなし）。

### Fixed
- なし（初回リリース）。

### Security
- OpenAI API キーは明示的に要求し、未設定時は例外を投げるため不正な動作を抑制。

### Notes / Known issues / TODO
- news_nlp: 大量のテキスト処理や OpenAI API 呼び出しに伴うコストとレート制限を考慮する必要があります。実運用では API キーの管理やリトライポリシーの追加チューニングが必要です。
- position_sizing.apply の price 欠損時のフォールバック（コメントに TODO）: 現状 price が 0.0 の場合はエクスポージャーが過小評価され、除外判定が誤る可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討。
- run_monitoring はドキュメントにある通り、常に本番 sqlite_path を使う設計。テスト時に監視を分離したい場合は環境変数やコードの調整が必要。
- .env パーサは多くのケースに対応しているが、非常に複雑なクォート内改行や非標準フォーマットには対応していない可能性があります。

---

(注) 実際のリリース管理では、このCHANGELOGを commit / tag と紐づけて運用してください。各項目はソースコードのコメント・実装から推測しています。必要に応じて日時・詳細・影響範囲を補完してください。