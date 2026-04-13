CHANGELOG
=========

全ての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- 特になし。

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開: KabuSys コードベースを追加。
  - パッケージエントリポイントとバージョン:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 設定管理:
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export 形式、クォート付き値（エスケープ対応）、インラインコメントの扱いをサポート。
    - Settings クラスで各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境検証 等）。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の値検証を実装（不正値は ValueError）。
- 実行用スクリプト:
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はログ警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する仕様。
    - プロセス優先度を起動時に "high" に設定（set_process_priority 呼び出し）。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（Settings.paper_sqlite_path）を使用して本番 DB と分離。MockBrokerClient を使う想定。
    - Execution 起動時にプロセス優先度を "high" に設定。
    - Execution 系の依存組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を行う。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値に broker.get_available_cash() を使用。
- 監視 DB 初期化:
  - kabusys.monitoring.monitoring_db.init_monitoring_db を run_monitoring/run_execution 起動時に呼び出して監視テーブルの存在を保証（冪等）。
- ユーティリティ:
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX の差分吸収、失敗時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) を実装（N コアへの固定、失敗時は警告でスキップ）。
- ポートフォリオ構築:
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates、等金額/スコア加重 calc_equal_weights/calc_score_weights を実装。スコア全0 のときは等金額へフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有時価を基に新規候補を除外）。"unknown" セクターは上限外扱い。
    - calc_regime_multiplier: 市場レジームに応じた投下乗数（bull/neutral/bear）を提供。未知レジームは 1.0 でフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash） によるスケールダウン、cost_buffer を用いた保守的見積り、残差処理による追加配分ロジックを実装。
- リサーチ / ファクター:
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクターを計算。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns, calc_ic（スピアマン IC）, factor_summary, rank を実装。DuckDB 接続を受け取って標準ライブラリのみで分析可能。
  - src/kabusys/research/__init__.py で公開 API を整備。
- AI / ニュース NLP:
  - src/kabusys/ai/news_nlp.py
    - raw_news テーブルを元に OpenAI API (gpt-4o-mini) を用いた銘柄別センチメントスコアリング機能を実装。
    - バッチサイズ、最大記事数/文字数制限、タイムウィンドウ計算（JST基準→UTC変換）を導入。
    - API エラー（429/ネットワーク/5xx 等）に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップを実装。
    - OpenAI API キー未設定時は ValueError を送出。
    - 成功時に ai_scores テーブルへ部分的に安全（対象コードのみ）に置換する方針。
- ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。CLI オプション --from / --to / --db をサポート。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標算出ロジックを実装。閾値はファイル先頭の定数で定義（UPTIME 99%、FILL_RATE 90% 等）。
    - DB が存在しない場合やテーブル欠落時は適切に "N/A" を表示して継続。
- パッケージ公開インターフェース:
  - src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/tools/__init__.py, src/kabusys/utils/__init__.py を整備し主要関数をエクスポート。

Changed
- 起動処理の挙動:
  - run_monitoring と run_execution の main() で起動時にプロセス優先度を "high" に設定するようにした（呼び出しは最初に行われる）。
- DB 周り:
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離する挙動を明確化。
  - run_monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（本番想定）をモニタ用に使用する仕様を明確化。

Fixed
- 設定読み込みの堅牢性:
  - .env パーサでクォート内のバックスラッシュエスケープ、export キーワード、インラインコメントの扱いを正しく処理するように修正（空白/タブ前の '#' をコメントとみなす等）。
- 実行時の堅牢性:
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもログを残して次ループへ継続するように例外ハンドリングを追加。
  - 各所で DB 接続を finally ブロックで確実にクローズするようにした。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で提供する必要があり、未設定時は明示的にエラーを出す（誤設定で silently fail しない方針）。

Notes / Breaking changes
- 重要: run_monitoring は環境（KABUSYS_ENV）に関係なく Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。テストや paper_trading 環境でモニタ用 DB を分離したい場合は環境変数を適宜設定してください。
- Settings のプロパティは不正値で ValueError を投げます（例: KABUSYS_ENV に許可されない値、PAPER_FILL_MODE の不正文字列など）。デプロイ前に .env を確認してください。
- AI スコアリング機能は外部 API（OpenAI）に依存します。API の利用上限や費用に注意してください。

参考: 主な実行例
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔調整（秒）。
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading DB と Mock ブローカを利用（data/paper_trading.db）。
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを明示指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

今後の予定（TODO）
- position_sizing の価格フォールバック（前日終値等）導入。
- stocks マスタを使った銘柄ごとの lot_size サポート。
- news_nlp の部分失敗時の永続化ロールバック/トランザクション最適化。
- DuckDB 側の executemany 空パラメータ問題に対する追加ガード（注: 実装内に留意コメントあり）。