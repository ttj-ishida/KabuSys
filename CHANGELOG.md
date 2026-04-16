# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の書式に準拠し、セマンティックバージョニングを用います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-16

初回リリース。自動売買システム KabuSys のコア機能群（実行エンジン、監視、ポートフォリオ構築、ファクター計算、ユーティリティ、ツール等）を実装しました。主な追加内容は以下のとおりです。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止はプロジェクト配下 data/stop_requested.flag ファイルを検知して行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - 停止フラグ / PID ファイル管理およびエンジンスレッドのデーモン実行をサポート。

- 設定管理
  - config.py
    - 環境変数および .env/.env.local の自動読み込み実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
    - Settings クラスを実装し、各種設定値（DB パス、API トークン、監視閾値、環境名等）をプロパティで提供。未設定の必須値は ValueError を送出。
    - 環境（KABUSYS_ENV）や LOG_LEVEL、PAPER_FILL_MODE の検証ロジックを実装。

- 実行コンポーネント（Execution）
  - ExecutionEngine の起動に必要な骨格（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組立て）を run_execution で組み合わせる実装を追加（詳細な各クラスの実装は別モジュールとして参照）。
  - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を run_execution 側で注入。
  - Broker クライアントは環境に応じて生成（paper_trading 時は MockBroker を想定）。

- 監視関連
  - monitoring_db.init_monitoring_db を使って監視用テーブルの存在を保証（冪等）。
  - DuckDB を分析用に併用（duckdb_path の設定）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存保有からセクター別エクスポージャを算出し、上限超過セクターの新規候補を除外）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく注文株数計算を実装。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング処理、cost_buffer の反映、残差に基づく追加配分を実装。

- 研究・ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。必要な過去データが不足する場合は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御に注意。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。target_date 以前の最新財務データを銘柄ごとに取得。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得する SQL 実装（デフォルト [1,5,21]）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 なら None）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - research/__init__.py で主要 API をエクスポート（zscore_normalize を含む）。

- AI（ニュース NLP）
  - ai/news_nlp.py
    - raw_news を元に OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント ai_score を生成する設計を実装。
    - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を実装。
    - バッチ処理・トークン肥大対策（1 銘柄あたり記事数・文字数上限）、リトライ（429/ネットワーク/5xx）での指数バックオフ、レスポンス検証、スコアの ±1.0 クリッピング、部分更新（該当コードのみ置換）の方針を採用。
    - （注）ファイル末尾が切れているため、記事取得関数や DB への書き込みの一部はこの差分からは不明。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI オプション: --from / --to / --db（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - 標準的な合格基準（しきい値）を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 latency <= 200 ms）。
    - P95 の計算、NULL/テーブル未存在時のフォールバックを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX の差分を吸収してプロセス優先度を設定。権限不足や未サポート環境では警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定したコア数に CPU affinity を固定。引数検証および権限エラー時の警告を実装。

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details / 動作上の注意
- 設計方針として、Research / Portfolio / Position sizing 等の関数群は副作用を持たない純粋関数（DB 参照の最小化）として実装されており、テストや再利用性を重視しています。
- run_monitoring は KABUSYS_ENV に関係なく monitoring 用の sqlite_path（デフォルト data/monitoring.db）を使う点に注意してください。対して run_execution は paper_trading 環境時に専用 DB を使用して本番データと分離します。
- process priority / cpu affinity の設定はプラットフォーム依存・権限依存のため、失敗時はログ警告でフォールバックします（例: 非 root での nice 値設定など）。
- ai/news_nlp は OpenAI API キー（OPENAI_API_KEY）に依存し、未設定時は例外を投げます。ファイルは末尾が切れている箇所があり、完全実装・DB 書き込みの詳細は差分外です。
- .env 読み込みはデフォルトで有効（プロジェクトルート検出に失敗した場合は読み込みをスキップ）。OS 環境変数は .env によって上書きされないよう保護されています（.env.local の上書きは許可）。

---

参考: 主要なデフォルト値・環境変数
- MONITOR_POLL_INTERVAL (監視ポーリング間隔、デフォルト 60)
- KABUSYS_ENV (development | paper_trading | live、デフォルト development)
- SQLITE_PATH（監視 DB、data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper trading DB、data/paper_trading.db）
- DUCKDB_PATH（分析用 DuckDB、data/kabusys.duckdb）
- OPENAI_API_KEY（news_nlp 用）
- PAPER_FILL_MODE（paper_trading の約定動作: instant|partial|never|reject、デフォルト instant）

もし特定の変更点（例: news_nlp の未実装部分や ExecutionEngine 内部の具体的な API 呼び出し）についてさらに詳しい CHANGELOG エントリが必要であれば、該当ファイルの続きや関連モジュールの実装を提示してください。