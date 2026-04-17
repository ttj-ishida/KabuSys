CHANGELOG
=========

すべての重要な変更はここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています（日本語訳）。

Unreleased
----------

Added
- news_nlp モジュール（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を追加。
  - バッチサイズ、最大記事数・文字数の制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ等の耐障害設計を導入。
  - ニュース収集ウィンドウ（JST基準の前日15:00〜当日08:30）をUTCで計算するユーティリティを追加。
  - 注意: ファイル末尾で記事集約フェーズ以降の処理が途中（実装の続きが必要）となっているため実行環境での動作検証が必要。

Changed
- なし（未リリース分）

Fixed
- なし（未リリース分）

v0.1.0 - 2026-04-17
-------------------

Added
- パッケージ基盤
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - モジュールのエクスポート整理（portfolio / research / tools 等の __all__ 整備）。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ検知で Engine.stop() を呼び出して安全停止。実行用 PID ファイル保存（data/execution.pid）。

- 設定管理
  - config.py
    - .env / .env.local の自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - 複雑な .env 行のパースを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュ、インラインコメント処理など）。
    - Settings クラスを実装し、アプリケーション設定（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / env 判定 等）をプロパティとして提供。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL 等のバリデーション実装。
    - paper_sqlite_path, duckdb_path, sqlite_path, pid_file_path, kill_flag_path 等のデフォルト値と上書きルールを用意。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX の差分を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - psutil を用いた実装で権限不足時は warning を出してスキップするフェイルセーフ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート／上位 N 抽出（score 降順、同点は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限のチェックおよび候補除外ロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（フォールバック動作含む）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り。
    - risk_based の場合は risk_pct・stop_loss_pct を用いた株数算出。
    - 価格欠損時のスキップ、ログ出力と安全弁の実装。

- リサーチ/バックテスト支援
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M、MA200乖離）、ATR、20日平均売買代金、volume_ratio、PER/ROE の算出ロジックを提供。
    - 処理は SQL（DuckDB）で行い、データ不足を考慮した None フォールバック。
  - research/feature_exploration.py
    - calc_forward_returns: target_date 基準の将来リターン（複数ホライズン）を一括取得する高速クエリ実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。
    - factor_summary: ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランク扱いのランク化ユーティリティ。
  - research/__init__.py で主要関数をエクスポート。

- データ / レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（コマンドラインから利用可能: python -m kabusys.tools.paper_verification_report）。
    - システム稼働率、注文成功率（Filled/Create）、送信率（Sent/Create）、リスク却下数、API レイテンシ（avg/max/P95）等の指標を集約してレポート出力。
    - 合格基準（稼働率/成功率/送信率/P95）を定義して PASS/FAIL 判定を行う。

- DB 周り / モニタリング初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - run_monitoring/run_execution で sqlite3 と DuckDB の接続を確立して使用。

- 実装方針・設計注記（ソース内ドキュメント）
  - 多数の関数に詳細な docstring を追加し、設計根拠（PortfolioConstruction.md / StrategyModel.md 等参照）を明記。
  - DuckDB を SQL と組み合わせてファクター計算を効率化する方針。
  - ルックアヘッドバイアス防止のため日付取得の扱いに注意した実装（news_nlp 等）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし

Notes / Breaking changes
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（0 以下や非整数）な場合にデフォルト 60 秒へフォールバックする動作を行います。
- config の自動 .env ロードはプロジェクトルートが検出できない場合はスキップされます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_nlp は堅牢性を考慮した設計ですが、ソースが一部未完の可能性があるため本番運用前に実装完了と実動作確認を行ってください。

Contributing
------------
変更はこの CHANGELOG を更新してください。リリース前に Unreleased セクションの内容を該当バージョンに移動してください。