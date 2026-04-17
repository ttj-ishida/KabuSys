CHANGELOG
=========

すべての変更は Keep a Changelog の形式に沿って記載しています。  
このファイルは日本語で要約しており、コードベースから推測できる機能追加・仕様・注意点をまとめています。

[Unreleased]
------------

- なし（現時点では未リリースの差分はありません）。
- 注意事項 / TODO:
  - ai/news_nlp モジュールは実装が途中で切れている箇所があり（ファイル末尾の切断）、完全動作は保証されません。OpenAI API 周りの処理フローや部分的な実装は存在しますが、エラー処理やバッチ書き込みの最終段が未完です。
  - position_sizing の将来的拡張（銘柄別 lot_size 対応、価格フォールバック）は TODO コメントとして残されています。

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ初版を追加（kabusys v0.1.0）。
- 実行および監視の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine をスレッドで起動・監視する起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db がデフォルト）を使用して本番 DB と分離。
    - 停止フラグ(data/stop_requested.flag)の検知でエンジンを安全に停止。
    - 実行用 PID ファイルを data/execution.pid に記録する仕組みを使用（設定で上書き可）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を採用。initial_portfolio_value を broker.get_available_cash() から初期化。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番の sqlite_path を使用する設計（監視データは本番 DB を想定）。
    - 停止フラグ検知でループを終了。
- 設定管理モジュール（config.py）
  - Settings クラスを導入し、環境変数／.env/.env.local の自動ロード機構を実装。
  - .env パーサは export プレフィックス、クォート、エスケープ、インラインコメントなどを考慮する堅牢な実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティを追加（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値, LOG_LEVEL, KABUSYS_ENV 等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ有効）。
  - KABUSYS_ENV の検証（development/paper_trading/live のみ有効）。
- データベース周り
  - sqlite3 と DuckDB の接続を利用する設計。監視テーブルを保証する init_monitoring_db 呼び出しを各起動スクリプトで実行（冪等）。
  - paper_trading 用に DB 分離（PAPER_TRADING_SQLITE_PATH）。
- ユーティリティ
  - process_priority.py を追加
    - set_process_priority(level)（high/normal/low）: Windows / POSIX (Linux, Darwin, FreeBSD) を吸収し psutil を使って優先度設定。権限不足等は警告してスキップ。
    - set_cpu_affinity(cpu_count) : 指定コア数への CPU affinity 固定を実装（利用可能コア数を超える場合は全コア使用）。
- Portfolio モジュール（ポートフォリオ構築）
  - portfolio_builder.py
    - select_candidates: buy シグナルをスコア降順で選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全 0 の場合は等金額にフォールバックし WARNING を出力）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中超過の候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 フォールバック。
  - position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数計算（risk_based / equal / score の割当方式をサポート）。
    - 単元株（lot_size）、コストバッファ(cost_buffer) を考慮した aggregate cap スケーリングアルゴリズムを実装。
    - 価格欠損時の挙動、スケールダウン時の端数処理（lot 単位での補填）を実装。
    - 将来的拡張箇所（銘柄別 lot_size、価格フォールバック）を TODO として明記。
- Research モジュール（定量分析）
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照するファクター計算（MA200、ATR20、各種モメンタム、PER/ROE 等）。
    - データ不足に対する None の扱いを明確化。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターンを計算（horizons 検証あり、SQL で一括取得）。
    - calc_ic: スピアマンランク相関（IC）を計算。十分なサンプル（>=3）でない場合は None を返す。
    - factor_summary / rank: 統計サマリーとランク付けユーティリティを実装（外部依存なし）。
  - research/__init__.py で主要 API を公開（zscore_normalize を含む）。
- Tools
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などの算出と基準値による PASS/FAIL 判定を実装。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションあり。
    - P95 計算、日付フィルタの組み立て、各種レポート出力フォーマットを実装。
- AI ニュース NLP（初期実装）
  - ai/news_nlp.py にニュースを OpenAI（gpt-4o-mini）でスコアリングするモジュールを追加。
  - バッチ処理、最大記事数・文字数制限、リトライ（指数バックオフ）方針、JSON Mode 出力検証、スコアクリップを実装する設計を含む。
  - OpenAI API キー解決ロジック（引数優先、環境変数 OPENAI_API_KEY）を実装。
  - 注: ファイル末尾が切れており、処理の一部が未完成（WIP）です。
- パッケージメタ
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため過去からの変更はなし）

Fixed
- .env パーサの堅牢化（引用符、エスケープ、export プレフィックス、インラインコメントの扱いなど）により、複雑な環境値の読み込み精度を向上。

Security
- なし（特記事項なし）

Removed / Deprecated
- なし

Notes / Known limitations
- ai/news_nlp.py はファイル末尾で処理が途切れており、現状での運用は推奨されません。OpenAI との連携部分は実装方針が記載されていますが、リトライや DB への安全な書き込みロジック等を含めて完成が必要です。
- position_sizing の価格欠損時の扱いは TODO コメントで将来的な改善（前日終値や取得原価のフォールバック）を示しています。実運用では価格データの完全性に注意してください。
- set_process_priority / set_cpu_affinity は権限不足や未サポート OS ではスキップされる実装です（警告ログを出力）。サーバー環境での権限設定に注意してください。
- run_monitoring は監視データを本番 sqlite_path に記録する設計のため、監視専用 DB を使いたい場合は設定の見直しが必要です。

References
- ソースコード内の docstring や TODO コメントに基づき記載しています。運用前に各モジュール（特に ai/news_nlp、position_sizing の拡張点）を確認してください。