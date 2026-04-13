KEEP A CHANGELOG
=================

すべての注目すべき変更を履歴として記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース (バージョン 0.1.0) を追加。
- パッケージのメタ情報:
  - パッケージ名: kabusys
  - バージョン: __version__ = "0.1.0"
- 設定・環境変数管理 (kabusys.config):
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env のパースにおける細かい挙動を実装（export 形式、クォート、インラインコメント処理など）。
  - Settings クラスを導入し、アプリケーション全体で使用する設定プロパティを提供:
    - J-Quants / kabu API / LINE 用トークン/ID
    - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH) のデフォルトを設定
    - PAPER_FILL_MODE の検証 ("instant"|"partial"|"never"|"reject")
    - PID/KILL フラグや監視しきい値 (CPU/MEM/DISK)
    - KABUSYS_ENV の検証 (development / paper_trading / live) とヘルパープロパティ (is_live/is_paper/is_dev)
    - LOG_LEVEL の検証
- 実行エントリスクリプト:
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskConfig の初期値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。initial_portfolio_value は broker.get_available_cash() から取得。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化ユーティリティ:
  - init_monitoring_db を実行して監視用テーブル存在を担保（冪等）。
- プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority):
  - set_process_priority(level) を実装（Windows と POSIX を吸収）。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアにピン留め）。
  - 権限不足や未対応 OS の場合は警告を出力して安全にスキップ。
- ポートフォリオ構築モジュール (kabusys.portfolio):
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコアが 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が max_sector_pct を超える場合、新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に応じた投下資金乗数（既知値以外は 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた株数計算、lot_size（単元）丸め、1銘柄上限・aggregate cap のスケーリング（端数配分アルゴリズム含む）、cost_buffer（手数料・スリッページ見積り）の考慮。
- リサーチ / ファクター計算 (kabusys.research):
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を追加（DuckDB 接続を受け取り prices_daily, raw_financials テーブルから計算）。
    - 定数（窓幅、ATR/MA/ボラティリティ等）を定義。
    - 不足データ時の扱い（NULL / None）に注意。
  - feature_exploration:
    - calc_forward_returns: 将来リターンを計算（多ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損や有効レコード数の検査）。
    - rank, factor_summary: ランク付け(同順位は平均ランク) と基本統計量出力を実装。外部依存なし（pandas 等を使わない）。
  - research パッケージは zscore_normalize を外部モジュールから再エクスポート。
- ニュース NLP スコアリング (kabusys.ai.news_nlp):
  - raw_news + news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
  - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、タイムウィンドウ（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を定義。
  - API 呼び出しに対する再試行（429/ネットワーク/5xx の指数バックオフ）、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分失敗時の DB 保護戦略（対象コードのみ DELETE→INSERT）。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。不在時は ValueError。
- ツール:
  - paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - CLI で期間指定 (--from/--to) や DB パス指定 (--db) が可能。
    - 指標: 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ (avg/max/P95)。
    - P95 計算、日付フィルタ、SQL クエリでの堅牢なエラーハンドリング（テーブル未存在時は N/A や 0 を返す）。
    - 判定基準（しきい値）を定義: 稼働率 99%、注文成功率 90% など。
- DB / クエリ関係:
  - DuckDB を分析用途に採用（prices_daily, raw_financials, raw_news, ai_scores 等を想定）。
  - SQLite はモニタリング・paper_trading 用データ保持に利用。
- ログ / エラーハンドリング:
  - 各所で logging を使用し、予期しないエラー時に exception ログを出力して処理継続するよう設計。
  - 権限不足や未対応環境では動作をスキップし警告を出すことで堅牢性を確保。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Removed
- （初回リリースのため削除履歴はありません）

Notes / Breaking changes
- 本リリースは初回公開のため互換性の過去版は存在しませんが、以下点に注意してください:
  - run_monitoring は監視 DB に常に settings.sqlite_path を使用する（環境に依存しない挙動）。
  - run_execution は paper_trading 環境時に paper 用 SQLite を使用し、本番 DB と分離する設計。
  - .env の自動読み込みはデフォルトで有効。テスト環境等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OpenAI API を利用する機能は API キーの正しい設定を必須とします。

Acknowledgments / References
- ドキュメント内にコメントとして設計方針（PortfolioConstruction.md, StrategyModel.md 等）への言及があり、実装はそれらの仕様に基づいています（実ファイルはリポジトリ外に存在する想定）。

お問い合わせ
- バグ報告や機能要望はリポジトリの issue にて受付してください。