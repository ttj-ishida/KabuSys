CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

フォーマットの解説: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-12
-------------------

Added
- パッケージ初回公開相当の機能群を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視では環境にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine の起動エントリポイントを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し paper_trading 用 SQLite（data/paper_trading.db をデフォルト）に分離して記録する。
- 設定管理
  - kabusys.config: .env / .env.local の自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。OS 環境変数を保護する override ロジック、export KEY=val 形式やクォート・エスケープ、インラインコメントの扱い等、堅牢なパーサを実装。
  - Settings クラスを用意し、各種設定値（DB パス、PID/kill フラグ、閾値、環境種別判定など）をプロパティで取得・バリデーションする機能を提供。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のチェックを実装。
- 監視周り
  - init_monitoring_db を利用して監視テーブルの存在を保証する仕組みを用意。
  - run_monitoring/run_execution の起動時にプロセス優先度を "high" に設定する呼び出しを組み込み（kabusys.utils.process_priority）。
- 実行系（Execution）
  - BrokerClientFactory によるブローカークライアント生成を導入（実運用／モックの切り替えを簡単に）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み合わせてセッション実行を行う流れを確立。RiskManager の初期設定例（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み、実行開始時にブローカー残高を初期ポートフォリオ値に利用。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio: 銘柄選定・重み計算・ポジションサイズ算出・リスク調整を純粋関数として実装。
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコア0.0時のフォールバック動作を含む）。
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算、単元株丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りを実装。
    - apply_sector_cap: 既存保有を考慮したセクター集中の上限チェック（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバックで 1.0。
- リサーチ / ファクター計算
  - kabusys.research.factor_research: DuckDB を利用したファクター計算を提供（momentum, volatility, value）。prices_daily / raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）、ATR、平均売買代金、PER/ROE 等を計算。
  - kabusys.research.feature_exploration: 将来リターン計算（複数ホライズン）、Spearman ランク相関による IC 計算、ファクターサマリー統計（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - zscore_normalize をエクスポートしてファクター正規化に対応（kabusys.data.stats から取り込み）。
- AI ニューススコアリング
  - kabusys.ai.news_nlp: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとにセンチメントスコアを算出・ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数、JSON Mode + 厳密なレスポンス検証、スコアクリップ（±1.0）、エクスポネンシャルバックオフを備えた堅牢な API 呼び出し設計。
    - ニュース対象時間ウィンドウを JST ベースで計算するユーティリティ（calc_news_window）を提供。API キー未設定時はエラーを投げる明示的な扱い。
- ツール
  - kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95レイテンシ等の指標を算出し PASS/FAIL 判定を出力。期間指定 (--from / --to)、DB パス指定 (--db) に対応。
- ユーティリティ
  - kabusys.utils.process_priority: クロスプラットフォームでプロセス優先度（Windows 高優先度 / POSIX nice 値）と CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS 時は警告してスキップする安全設計。

Changed
- （初回リリースのため該当なし：今後のリリースで差分を記載）

Fixed
- 環境変数読み込み・パースの堅牢化（不正な行やクォート・エスケープ、コメント処理などを改善）。
- MONITOR_POLL_INTERVAL の読み取りで 0 以下や非整数の値を検出した場合にデフォルトへフォールバックして time.sleep の ValueError を回避。
- Paper Trading 実行時にも監視テーブルの存在を保証するため init_monitoring_db を呼び出すようにした（冪等）。

Security
- news_nlp の OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY を設定する必要あり。未設定時は ValueError を送出して処理を中断する仕様により誤ったキー漏洩リスクを低減。

Notes / Migration
- 初回リリース: Settings のプロパティや環境変数名（例: SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, KABUSYS_ENV, PAPER_FILL_MODE, OPENAI_API_KEY 等）に依存するため、運用環境では .env/.env.local の整備と必要なキーの設定を行ってください。
- run_execution を paper_trading モードで実行する場合、本番 DB と混同しないよう PAPER_TRADING_SQLITE_PATH の確認を推奨します。
- news_nlp は OpenAI の API 呼び出しを行うため、実行時のコストやレート制限に注意してください（内部でリトライ・バッチ処理を実装していますが、運用上の監視を推奨します）。

パッケージ情報
- バージョン: 0.1.0 (src/kabusys/__init__.py にて定義)

今後の予定
- broker/mocking の詳細な実装ドキュメント化
- stocks マスタによる銘柄別 lot_size 対応（position_sizing の拡張）
- ニューススコアリングのローカルテスト用フェイルセーフ（API 呼び出しのモック化支援）
- DuckDB クエリ最適化、並列実行やキャッシュ対応

ご要望・バグ報告・改善提案は issue を作成してください。