Changelog
=========

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------


0.1.0 - 2026-04-13
------------------

Added
- 初期リリース。KabuSys のコア機能群を実装。
- 実行・監視系スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード内に定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバック。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定する（utils/process_priority を利用）。
- 設定・環境変数周り
  - config.Settings クラスを実装。環境変数／.env ファイルから各種設定を取得可能。
  - .env 自動ロード機能を実装:
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local を読み込む。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応。
    - .env パーサは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等に対応。
  - 各種設定プロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/Memory/Disk の閾値, PAPER_FILL_MODE の検証など）。
  - KABUSYS_ENV の有効値検証（development, paper_trading, live）と LOG_LEVEL の検証実装。
- データ処理・ポートフォリオ構築
  - portfolio モジュール:
    - portfolio_builder: 候補選定（score 降順、タイブレーク処理）、等金額・スコア加重配分（スコア全0 の際のフォールバック）を実装。
    - position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数計算を実装。単元（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン（端数の再配分ロジック含む）、コストバッファ対応などを実装。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- 研究（research）機能
  - research.factor_research: DuckDB を用いたファクター計算を実装（momentum / volatility / value）。prices_daily / raw_financials テーブル参照、ウィンドウ制御、欠損ハンドリング、P95 等の計算を含む。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ランク処理、ファクター統計要約（count/mean/std/min/max/median）を実装。外部依存を最小化（標準ライブラリのみ）。
  - research パッケージは z-score 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）をエクスポート。
- AI / ニューススコアリング
  - ai.news_nlp: raw_news から銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを ai_scores テーブルに書き込む処理を実装。
    - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を厳密に計算。
    - バッチサイズ、1銘柄あたりの最大記事数／文字数制限、スコア ±1.0 のクリップ、API リトライ（429/5xx/接続断/タイムアウトに対する指数バックオフ）等を実装。
    - API キー未設定時は明示的なエラーを返す（api_key 引数または環境変数 OPENAI_API_KEY）。
    - 結果の検証および部分書き換え（該当日の該当銘柄のみ DELETE→INSERT）によるフェイルセーフ設計。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX を吸収）と CPU affinity 設定を提供。権限不足や未サポート環境では警告を出してスキップする安全策を実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を実装。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等を集計し、PASS/FAIL 判定を出力。期間フィルタ（--from / --to / --db）対応。
- パッケージメタ
  - kabusys.__version__ = "0.1.0"

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーの取り扱いは明示的に要求（env または引数）。ネットワークエラー等でのリトライ制御を実装し、過剰な情報漏洩リスクを低減する設計を意識。

Notes / Migration / Usage
- デフォルトのデータパス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を秒単位で調整可能。1 未満や不正な値はデフォルト（60 秒）にフォールバック。
- PAPER_FILL_MODE の有効値: instant | partial | never | reject。無効な値を設定すると ValueError を送出する。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 監視ループ（run_monitoring）は監視用 DB に常に本番 sqlite_path を使用する点に注意（KABUSYS_ENV に依存しない）。
- Paper Trading を動かす場合は KABUSYS_ENV=paper_trading を設定することで run_execution が paper 用 DB を使用し、本番 DB から分離される。
- process_priority / set_cpu_affinity は実行権限や OS によっては設定できない（警告ログを出力してスキップ）。

今後の予定（例）
- モニタリング・監査テーブルのスキーマ追加・改善（監査イベント、詳細メトリクス保存など）。
- ExecutionEngine 周りのセッション管理、詳細ログ・トラブルシュート支援の強化。
- ai.news_nlp のレスポンス検証を拡張し、異常応答検出・自動リトライの強化。
- ファクター計算の追加（PBR、配当利回り等）と z-score 正規化フローの公開 API 整備。

もし特定の変更点をより詳細に反映したい場合（たとえばコミット単位や差分からのより正確な変更履歴化）、対象となるコミットログや差分を提供してください。