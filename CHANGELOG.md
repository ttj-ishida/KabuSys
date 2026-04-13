# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
リリースはコードベースから推測して記載しています（自動生成のため実際の履歴と差異がある場合があります）。

全般:
- 初期リリース相当の機能セットを収録（バージョンはパッケージ定義 (kabusys.__version__) に基づく 0.1.0）。
- 主にトレード実行、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、および開発/運用用ツールを含む。

Unreleased
- （なし）

[0.1.0] - 2026-04-13
========================================
Added
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py を追加。ExecutionEngine を起動するエントリポイント。
  - KABUSYS_ENV=paper_trading のときは paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と完全分離する設計。
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler を組み合わせて ExecutionEngine を構成。
  - プロセス優先度を起動時に High に設定。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py を追加。SystemMonitor を定期実行するポーリングループを提供。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - 起動時にプロセス優先度を High に設定。

- 設定/環境変数管理
  - src/kabusys/config.py を追加。
  - .env/.env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）を実装。OS 環境変数を保護するための上書き制御をサポート。
  - .env パーサーは export 構文、クォート値（バックスラッシュエスケープ含む）、インラインコメントの取り扱いを考慮した堅牢実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスで多数のプロパティを提供（J-Quants, kabu API, LINE, DB パス, paper trading 設定, 監視閾値, ログレベル, env 検証 など）。環境変数検証とデフォルト値を含む。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py を追加。paper_trading の SQLite を読み取り、稼働率・注文成功率・送信率・レイテンシ等の指標を算出して PASS/FAIL 判定する CLI ツール。
  - CLI 引数: --from / --to / --db。デフォルト DB パスは data/paper_trading.db。
  - P95 計算、SQL クエリを通じた各種集計、閾値による判定ロジックを備える。

- ポートフォリオ構築
  - src/kabusys/portfolio 以下を追加。
  - portfolio_builder: select_candidates（スコア降順で選出）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中制限。既存保有のセクター露出を計算し上限超過セクターの候補除外）、calc_regime_multiplier（market regime に基づく資金乗数）。
  - position_sizing: calc_position_sizes（allocation_method に応じて発注株数算出。risk_based/equal/score をサポート、lot_size 単位丸め、コストバッファ考慮、aggregate cap によるスケールダウンと端数配分ロジック）。
  - すべて純粋関数設計（DB 非依存、メモリ内計算）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py を追加。DuckDB を使ったファクター計算（momentum, volatility, value）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200 のデータ不足は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials と prices_daily を組み合わせた PER/ROE（最新財務データを target_date 以前から取得）。
  - src/kabusys/research/feature_exploration.py を追加。将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー、rank ユーティリティを提供。
  - research パッケージの __init__ で zscore_normalize（kabusys.data.stats）や主要関数を再エクスポート。

- ニュースNLP（AI スコアリング）
  - src/kabusys/ai/news_nlp.py を追加（OpenAI を利用したニュースセンチメント評価）。
  - 指定ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）で raw_news を集約し、最大 20 銘柄/チャンクで OpenAI API（gpt-4o-mini）へ送信するバッチ処理。
  - トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx のエクスポネンシャルバックオフによるリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の DB 書き込みの保護（対象コードを限定して DELETE→INSERT）等を実装。
  - API キーは引数または OPENAI_API_KEY 環境変数で指定。未指定時はエラー。

- ユーティリティ
  - src/kabusys/utils/process_priority.py を追加。クロスプラットフォームでプロセス優先度（Windows の優先度クラス / POSIX の nice 値）と CPU affinity を設定するユーティリティ。対応 OS での設定、権限エラー時の警告スキップ、入力検証を実装。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定、主要サブパッケージを __all__ に定義。

Changed
- （初回リリースのため、変更履歴はなし。設計上の注記を以下に列挙）
  - .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後も CWD に依存せず動作するように設計。
  - run_monitoring は監視用 DB に常に sqlite_path（本番設定）を使用するため、環境切替が監視データに影響しないように明示的に設計。

Fixed
- .env パーサーの堅牢化（export プレフィックス対応、クォート付き値のエスケープ処理、クォートなしでのインラインコメント判定）により、複雑な .env 記述での誤読を回避。

Security
- 環境変数の扱いに注意:
  - 必須の機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY など）は Settings 経由で取得し、未設定時は明示的にエラーを発生させることで運用時に見落としを防止。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。

Notes / Upgrade / 運用メモ
- 必要な環境変数（代表例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（ニュースNLP 使用時）
  - KABUSYS_ENV: development / paper_trading / live
  - PAPER_FILL_MODE: instant | partial | never | reject
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - SQLITE_PATH / DUCKDB_PATH（監視 DB / DuckDB path）
  - MONITOR_POLL_INTERVAL（run_monitoring の監視間隔、秒）
- Paper Trading と本番 DB は明確に分離。paper_trading 実行時は settings.is_paper に応じて paper_sqlite_path が使用される。
- process_priority.set_process_priority は権限不足や未対応 OS の場合は警告ログを出してスキップするため、必ずしも優先度変更が成功するとは限らない点に注意。
- news_nlp の OpenAI 呼び出しはバッチとリトライを行うが、API コストやレート制限に注意して運用すること。
- DuckDB を用いたファクター計算/リサーチ機能は prices_daily / raw_financials 等のテーブルに依存するため、事前に DuckDB に必要なデータをロードしておく必要があります。

================================================
参考: この CHANGELOG はコード内容からの推測に基づき自動生成されています。実際の変更履歴（コミット単位や過去リリース）が存在する場合は、該当履歴に合わせて適宜修正してください。