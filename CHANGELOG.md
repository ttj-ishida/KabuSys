CHANGELOG
=========

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

フォーマット:
- バージョン見出しは "バージョン - リリース日"（YYYY-MM-DD）
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

0.1.0 - 2026-04-17
------------------

Added
- 初回公開: kabusys パッケージ v0.1.0 を導入。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行関連スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - プロセス優先度を "high" に設定する処理を先頭で実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient の利用を想定）。
    - BrokerClientFactory によるブローカー生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動（バックグラウンドスレッド）を実装。
    - data/execution.pid と停止フラグ（data/stop_requested.flag）による起動／停止制御を実装。
    - 監視テーブル（init_monitoring_db）の冪等初期化を行う。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（監視 DB を本番と共通化）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。例外・KeyboardInterrupt を安全にハンドリングして接続をクローズ。

- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数経由で各種設定値（API トークン、DB パス、監視閾値、PID/フラグパス等）を取得する実装を追加。
    - .env / .env.local の自動読み込み機能を実装（OS 環境変数の保護を考慮）。
    - .env パーサーはコメント行・export 形式・クォート文字列・エスケープに対応。
    - 値検証を実装（例: KABUSYS_ENV の有効値チェック、LOG_LEVEL、PAPER_FILL_MODE の許容値チェック）。
    - デフォルト値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止機能を追加。

- モニタリング DB 初期化ユーティリティ参照
  - 各起動スクリプトで monitoring_db.init_monitoring_db を呼び、監視テーブルが存在することを保証（冪等）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。
    - コマンドライン引数: --from, --to, --db（PAPER_TRADING_SQLITE_PATH と併用可能）。
    - システム安定性（稼働率）、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）を SQLite のテーブルから集計してレポート出力。
    - 判定基準（PASS/FAIL）を定義（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 latency <= 200 ms）。
    - データ欠損・テーブル未存在時に N/A を返す安全な実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと候補抽出（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮したセクター集中上限チェック（max_sector_pct）。売却予定銘柄はエクスポージャー計算から除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームは警告を出して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく注文株数計算を実装。
    - 単元 lot_size（デフォルト 100）で丸め、1 銘柄上限・aggregate cap（available_cash）を考慮。
    - cost_buffer により保守的に手数料・スリッページを見積もり、投資合計が available_cash を超える場合はスケールダウンして残余キャッシュで端数（lot 単位）を順次割当てるロジックを実装。
    - 価格欠損時のスキップ、max_per_stock の考慮、将来的な銘柄別 lot_size 拡張に関する TODO を記載。

- 研究（Research）モジュール
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily/raw_financials を参照してファクターを計算。
    - 各種窓・バッファ設定を定義（例: MA200, ATR20 等）。
  - research/feature_exploration.py
    - calc_forward_returns, calc_ic, rank, factor_summary を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで統計量やスピアマン（ランク）相関等を計算。

- AI / ニュース NLP（プロトタイプ）
  - ai/news_nlp.py （初期実装）
    - ニュースの収集ウィンドウ算出（calc_news_window）。
    - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリングの処理方針・定数（バッチサイズ、最大記事数/文字数、リトライポリシー、出力 JSON 仕様など）を実装。
    - score_news の雛形を実装し、API キーの解決と基本的なエラーチェックを行う（API キー未設定時に ValueError を送出）。
    - 注意: 本ファイルは大きな処理フローを設計・部分実装しているが、ファイル末尾が途中で切れているため（部分実装／プロトタイプ）である。実運用での完全な検証／安全対策は要追加。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。権限不足等で失敗した場合は WARNING を出力してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する処理を追加（引数 None で無効化）。入力バリデーションを実装。

- パッケージエクスポート
  - research/__init__.py, portfolio/__init__.py による主要 API のエクスポートを整備。

Changed
- N/A（初回リリースのため過去バージョンからの差分なし）

Fixed
- N/A（初回リリース）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / Known limitations
- .env 自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local をロードする。テスト等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
  - .env.local は .env の上書き用。OS に存在する環境変数は保護（上書きされない）。

- PAPER_TRADING（分離）
  - paper_trading 環境は明示的に実運用 DB と分離する設計。Execution は paper_sqlite_path を使用し、発注シミュレーション（MockBroker）を想定している。

- モニタリング
  - run_monitoring は本番 sqlite_path を使用するため、監視は本番データストアと同じ DB を参照する。監視専用 DB を望む場合は設定値を変更する必要がある。

- process_priority / CPU affinity
  - 権限不足やプラットフォーム非対応で処理が失敗する可能性があるが、その場合は警告を出して処理を継続する（fail-safe）。

- position_sizing の制約
  - 現状は単元（lot_size）が全銘柄共通である点、価格欠損時に単純スキップしてしまう点など、将来的な拡張を想定した TODO が残る。

- ai/news_nlp.py
  - 主要な定数・方針は実装済だが、ファイル中に処理が途中で途切れている箇所がある（未完）。本モジュールを本番で用いる前に完了実装および十分な検証が必要。

- paper_verification_report
  - DuckDB を使用せず SQLite に直接クエリを投げるため、スキーマ差異やテーブル未存在時に配慮したフェイルセーフ処理を行っている。DB スキーマが整っていることを前提に利用すること。

今後の予定（予定事項・TODO）
- ai/news_nlp の完全実装（API の呼び出し・レスポンス検証・DB 書き込みの完全化、部分失敗時のロールフォワード戦略の実装）
- position_sizing: 銘柄別 lot_size の導入、価格フォールバック（前日終値等）の追加
- テストカバレッジの追加（特に金融ロジック・スケーリングロジック・DB マイグレーション）
- ドキュメント整備（PortfolioConstruction.md, StrategyModel.md の参照実装との対応付け）

以上。