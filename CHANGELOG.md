CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-16
-------------------

Added
- 基本リリース: KabuSys の初期実装を追加。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 実行系
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 環境に応じて paper_trading 用 DB を分離（PAPER_TRADING 使用時は data/paper_trading.db を使用）。
    - BrokerClientFactory によりブローカークライアントを抽象化（paper/live 切替対応）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせてエンジンを起動。
    - エンジンはスレッドでデーモン実行。停止フラグ検知で安全に停止する仕組みを実装。
    - pid ファイル管理用パスを使用。
- 監視系
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブル初期化を保証。
    - 停止フラグファイル検知・例外時ログと次ポーリング継続など堅牢化。
- 設定・環境読み込み
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git / pyproject.toml 基準）。
    - 読み込みは OS 環境変数を保護し、上書き制御可能。
    - 多数の設定プロパティを提供（DB パス、PID/kill flag、閾値、環境種別、paper_trading 切替等）。
    - 入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの値検査）。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates：スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights：等額・スコア加重を提供。スコア全0時は等分にフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクターエクスポージャーを計算し上限を超えるセクターの新規候補を除外。
      - "unknown" セクターは上限適用外。
      - TODO: 価格欠損時のフォールバック改善の注記あり。
    - calc_regime_multiplier：regime (bull/neutral/bear) に応じた投下資金乗数を返す。未知レジームはフォールバック 1.0。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）でのスケールダウン、余剰配分ロジックを実装。
    - cost_buffer による手数料/スリッページ保守見積りを考慮。
- 研究・ファクター計算（DuckDB 前提）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を用いた複数ファクターを実装。
    - 各関数はデータ不足を考慮して None を返す仕様。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns：任意ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic：Spearman ランク相関（IC）実装。有効レコード不足時は None。
    - factor_summary / rank：統計サマリとランク関数（同順位は平均ランク）。
  - research パッケージに zscore_normalize をエクスポートするための __init__ を提供。
- AI ニュース NLP（草案実装）
  - src/kabusys/ai/news_nlp.py にて OpenAI API（gpt-4o-mini）を使ったニュースセンチメントスコアリング実装。
    - タイムウィンドウ計算（JST→UTC 変換）、記事集約、銘柄ごと文字数/記事数トリム、バッチ送信（最大 20 銘柄）、JSON 出力バリデーション、スコアの ±1.0 クリップ、書き込みの原子性（対象コードのみ差し替え）などの設計を記述。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ方針、API キー未設定時に ValueError を送出する仕様。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出。
    - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能。
    - 基準値（稼働率 99% など）を定義し PASS/FAIL 判定を出力。
- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS 等の差分を吸収して優先度設定を行う set_process_priority。
    - set_cpu_affinity で最初の N コアにプロセスをピンニング（権限不足等はログでスキップ）。
    - 例外に対して安全にフォールバックして警告ログを出す実装。

Changed
- 初期リリースのため該当なし。

Fixed
- 環境変数/設定の堅牢化
  - .env パーサーで export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）に対するフォールバック処理を run_monitoring に実装。ログ警告を出す。
- 監視・実行スクリプトでのリソースクリーンアップ
  - DB 接続（sqlite, duckdb）を finally で確実にクローズするように実装。
- レート制限・API 障害対策の設計（AI モジュール）
  - リトライ回数・バックオフ定義、部分失敗時の既存データ保護方針を明示。

Known Issues / Notes
- news_nlp モジュールは設計が詳細に記述されているが、ソースの最後が切れている（fetch_articles 関数以降の処理がスニペットで途切れています）。実運用には以下の点を確認・実装する必要があります:
  - _fetch_articles の実装、API 呼び出しの実コード、DuckDB への書き込みロジックの完成。
- apply_sector_cap 内で price が欠損（0.0）の場合のエクスポージャー過少見積りに関する TODO が残っています。前日終値等のフォールバックを検討する必要あり。
- position_sizing の将来拡張: 銘柄別 lot_size を持たせる設計（現状は全銘柄共通の単元扱い）。
- DuckDB/SQLite のテーブルスキーマや monitoring/system_monitor、execution の内部実装（Engine 本体・Broker 実装等）はこのスナップショットに含まれていません。実運用前に各コンポーネントの統合テストが必要です。
- 権限が必要な操作（プロセス優先度設定、CPU affinity）は環境により失敗する可能性があります。これらはログ警告でスキップされる設計です。

Security
- OpenAI API キー等の機密値は環境変数経由で取得する設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- .env 自動ロードの際、OS 環境変数は protected として上書きを防ぐ仕様。

付記
- ドキュメントの多くは PortfolioConstruction.md、StrategyModel.md 等の外部ドキュメントに依拠する旨の注記があります。戦略仕様／データスキーマを参照して運用してください。