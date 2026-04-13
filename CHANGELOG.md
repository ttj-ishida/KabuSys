CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）のガイドラインに準拠して記載しています。

Unreleased
----------

（現時点では未リリースのワークインプログレスはありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 全体
  - パッケージ初期リリース。パッケージバージョンは kabusys.__version__ = "0.1.0"。
  - DuckDB/SQLite を組み合わせた分析・監視・実行基盤を提供。

- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - 監視用 SQLite（settings.sqlite_path）および DuckDB を接続し、監視 DB 初期化関数 init_monitoring_db を呼び出して監視テーブルの存在を保証。
    - KABUSYS_ENV に関わらず監視は本番 sqlite_path を使用する旨を明記。

  - run_execution.py を追加。
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading 環境（KABUSYS_ENV=paper_trading）の場合は paper_sqlite_path を用いて本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の実行を行う。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）を組み込み。initial_portfolio_value は broker.get_available_cash() から取得。

- 設定 / 環境読み込み
  - config.py を追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装し、.env 自動ロードをサポート（.env → .env.local の順、OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - .env パーサーを実装（export KEY=val 形式、クォート文字列のバックスラッシュエスケープ、インラインコメント処理などに対応）。
    - Settings クラスを提供し、各種設定（J-Quants / kabuAPI / LINE / データベースパス / 監視設定 / システム設定）をプロパティ経由で安全に取得。
    - PATH デフォルト: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db、PAPER_TRADING_SQLITE_PATH=data/paper_trading.db など。
    - paper_fill_mode の有効値チェック（instant, partial, never, reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - 監視用の閾値（CPU/MEMORY/DISK）や pid / kill flag 関連の設定を追加。

- 監視・ツール
  - kabusys.tools.paper_verification_report を追加。
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から集計レポートを生成する CLI スクリプト。
    - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）をサポートし、DB が存在しない場合のエラーメッセージを出力。
    - P95 計算、NULL/データ欠損への耐性（テーブルが存在しない場合のフォールバック）を実装。

- ポートフォリオ構築
  - kabusys.portfolio パッケージを追加（portfolio_builder, risk_adjustment, position_sizing）。
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N 件を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分。全銘柄スコアが 0 の場合は等配分にフォールバック（警告ログ）。
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限を超える場合は新規候補を除外。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull:1.0, neutral:0.7, bear:0.3、未知レジームは警告して 1.0 にフォールバック）。
    - calc_position_sizes: risk_based / equal / score の配分方式に対応し、lot_size（例:100）で丸め、per-stock 上限・aggregate 上限（available_cash）・cost_buffer を考慮したスケーリング・端数配分ロジックを実装。

- ユーティリティ
  - utils.process_priority を追加。
    - set_process_priority(level) により Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収してプロセス優先度を設定。未対応 OS は警告。
    - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアに固定するユーティリティを実装。権限不足や未対応環境では警告でスキップ。

- リサーチ / ファクター計算
  - kabusys.research パッケージを追加（factor_research, feature_exploration）。
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials テーブルを用いてモメンタム・ATR・流動性・PER/ROE 等を計算。
    - calc_forward_returns: 将来リターン（複数ホライズン）を LEAD を使って一括取得。horizons の検証あり。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を提供。
    - 設計上、DuckDB を使い SQL 中心で高速に計算するように実装。

- AI / ニューススコアリング
  - kabusys.ai.news_nlp を追加（OpenAI を利用したニュースのセンチメントスコアリング）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を実装（calc_news_window）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、最大記事数・最大文字数でトリム（1銘柄あたり最大 10 件、3000 文字）。
    - 最大 20 銘柄単位でバッチ送信し、OpenAI（gpt-4o-mini）の JSON Mode を利用。レスポンスをバリデーションしてスコア（-1.0〜1.0）をクリップ。
    - 429/ネットワークエラー/タイムアウト/5xx に対して指数バックオフでリトライ（上限 3 回）。
    - スコアを書き込む際は、対象コード群を限定して DELETE→INSERT の置換を行い、部分失敗時に既存スコアを保護する実装を明記。
    - API キー未指定時には ValueError を送出（api_key または環境変数 OPENAI_API_KEY のいずれか必須）。

Changed
- 監視関連の堅牢化
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉してログ出力後に次のポーリングへ継続するように改善（耐障害性向上）。
  - SQLite/DuckDB の接続は finally ブロックで確実にクローズするように実装。

- .env 読み込みと環境変数保護
  - .env/.env.local のロード順および OS 環境変数を保護する仕組みを導入し、環境依存の上書きを予防。

Fixed
- 入力値バリデーション強化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対するフォールバックと警告表示を追加。
  - Settings.paper_fill_mode / KABUSYS_ENV / LOG_LEVEL の不正値チェックを実装し、誤設定時に早期に例外を出すようにした。
  - calc_forward_returns の horizons 引数検証を実装（正の整数かつ 252 以下に制限）。

- ロバストネス向上
  - DuckDB/SQLite からのクエリ時にテーブルが存在しない場合のフォールバックを paper_verification_report 側で実装（OperationalError を捕捉してデフォルト値を使用）。
  - process_priority と CPU affinity 設定で権限不足や未対応 API に対してキャッチして警告にとどめるように変更（起動失敗を防止）。

Notes / その他
- ドキュメント参照
  - ソース内に PortfolioConstruction.md, StrategyModel.md 等を参照する記述があり、アルゴリズムはそれらの設計文書に準拠していることが示唆されている（実ファイルはリポジトリ外の想定）。
- 将来の拡張ポイント（コード内 TODO）
  - position_sizing: 銘柄別 lot_size のサポートや price フォールバック（前日終値／取得原価）の導入が想定されている。
  - news_nlp: 実行中断や部分失敗時のより細かいトランザクション処理強化が可能。

参考: 主な追加ファイル
- src/kabusys/__init__.py (バージョン)
- src/kabusys/config.py (.env ローダー, Settings)
- src/kabusys/run_monitoring.py, src/kabusys/run_execution.py (起動スクリプト)
- src/kabusys/tools/paper_verification_report.py (レポート CLI)
- src/kabusys/portfolio/*.py (ポートフォリオ構築ロジック)
- src/kabusys/utils/process_priority.py (プロセス優先度 / CPU affinity)
- src/kabusys/research/*.py (ファクター / リサーチ)
- src/kabusys/ai/news_nlp.py (ニュース NLP スコアリング)

今後のリリースでは、テストケースの追加、エンドツーエンドのデプロイ手順、運用ドキュメント（監視・再起動ポリシー）や、銘柄毎の lot_size マスタ導入等を検討してください。