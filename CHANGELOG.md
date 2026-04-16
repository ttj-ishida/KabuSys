# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づいています。

全般:
- 日付はリリース日（リポジトリ中のバージョン定義に準拠）を記載しています。
- 環境変数やデフォルトパスなどはコード中のコメント・実装から推測して記載しています。

## [Unreleased]

（現在の差分はありません。次回リリースでここに移動します。）

---

## [0.1.0] - 2026-04-16

### Added
- 基本アプリケーション構成
  - パッケージ初期化とバージョン定義（kabusys.__init__.__version__ = 0.1.0）。
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - 厳格な環境変数取得ヘルパ（_require）と Settings クラスを提供。
  - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）。
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証。
  - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）。
- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動フローを実装：プロセス優先度設定、DB 接続、BrokerClient 作成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、エンジンスレッド起動、停止フラグ監視。
  - Paper Trading（KABUSYS_ENV=paper_trading）時は paper_trading 専用 SQLite DB を使用して本番 DB と完全分離する設計。
  - デフォルトで data/execution.pid を PID 管理に使用し、data/stop_requested.flag による外部停止制御をサポート。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window, max_drawdown 等）を明示。
- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor を使ったポーリングループ実装。
  - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
  - 監視は環境に依らず本番 sqlite_path を使用する実装（意図的な設計）。
  - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt での終了処理あり。
- プロセス優先度と CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX 差を吸収してプロセス優先度（high/normal/low）設定を提供。
  - CPU コア数固定（set_cpu_affinity）機能を提供。
  - 権限不足や未サポート環境でのフォールバックと警告処理。
- Portfolio コンポーネント（src/kabusys/portfolio/*）
  - 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）。
  - リスク調整（apply_sector_cap, calc_regime_multiplier）:
    - セクター上限（max_sector_pct）に基づく候補除外ロジック。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - ポジションサイズ算出（calc_position_sizes）:
    - risk_based / equal / score ベースの株数計算。
    - lot_size（単元）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的推定、余剰キャッシュ配分アルゴリズム。
- リサーチ機能（src/kabusys/research/*）
  - ファクター計算（factor_research）:
    - Momentum（1M/3M/6M リターン、MA200 乖離）
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）
    - Value（PER, ROE） — DuckDB 上の prices_daily / raw_financials テーブル参照
  - フィーチャー探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（calc_ic、Spearman ランク相関）
    - ファクター統計サマリー（factor_summary）、ランク関数（rank）
  - DuckDB を用いた SQL + Python ハイブリッド実装でデータ取得と計算を行う設計。
- Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から指標を集計。
  - 出力項目: 稼働率（uptime）、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（avg/max/P95）など。
  - CLI オプション: --from / --to / --db。閾値（稼働率 99%、Fill 90% 等）を用いた PASS/FAIL 判定。
- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出。
  - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
  - 出力のバリデーション、スコアを ±1.0 にクリップ、ai_scores テーブルへ安全に差分更新する方針を実装。
  - API キーは引数または環境変数 OPENAI_API_KEY で指定（未設定時は ValueError）。
  - ニュース収集ウィンドウ計算関数（calc_news_window）を提供（JST→UTC のウィンドウ変換）。
  - （注）ファイル末尾が一部切れているため、完全な DB 書き込みロジックや一部実装は推測に基づく。
- パッケージエクスポート整理（src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/tools/__init__.py）
  - 主要関数のトップレベル公開を用意。

### Changed
- 初期リリースのため過去バージョンからの変更履歴はなし（初期導入）。

### Fixed
- 初期リリースのため過去バージョンからの修正履歴はなし。

### Security
- OpenAI API キーや各種機密値は環境変数経由で管理する設計。.env 自動ロード時も OS 環境変数を保護する仕組み（protected set）が実装済み。

### 注意点 / 既知の制約・ TODO（コード内コメントに基づく）
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用」する実装のため、意図的に本番 DB に書き込む設計になっている点に注意してください（paper_trading 環境でも本番監視 DB を参照する）。
- position_sizing.calc_position_sizes:
  - price_map / open_prices における価格欠損（0.0）がある場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックが必要（TODO コメントあり）。
- apply_sector_cap:
  - sector_map に存在しないコードは "unknown" 扱いとしてセクター上限の適用対象外になる仕様（意図的だが運用上の注意点）。
- process_priority:
  - 未サポート OS では優先度設定をスキップして警告を出す。権限不足で設定に失敗するケースはログ警告にとどめてフォールバックする。
- ai/news_nlp.py:
  - 実装は堅牢な設計（バッチ、リトライ、レスポンス検証）を目指しているが、ファイル末尾が途切れているため一部処理（記事取得関数の終端処理や DB 挿入の詳細など）は不完全。実運用前に該当箇所の完成と検証が必要。
- 環境変数の自動ロード:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（例: 配布パッケージ等）。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を活用可能。
- CLI/デフォルトパス:
  - 多くのデフォルトが data/ 以下に集中（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb 等）。運用時は明示的に環境変数で上書きすることを推奨。

### Migration / 設定メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings._require により未設定で ValueError を送出するため、本番実行環境でのセットが必須。
- Paper Trading を使う場合:
  - KABUSYS_ENV=paper_trading に設定すると run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用する点に留意。
- ログレベルや各しきい値は Settings 経由で環境変数から制御可能（LOG_LEVEL, CPU_THRESHOLD_PCT 等）。

---

参考: 上記はコードベース内のドキュメント文字列・コメント・実装から推測してまとめた CHANGELOG です。実際のリリースノートとして公開する場合は運用での決定事項（デフォルトパスの変更、重大な既知バグ、API キー取り扱い方針など）を追記してください。