CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。
新しいバージョンはセマンティックバージョニングに基づきます。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-17
-----------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 環境設定／読み込み
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env / .env.local の読み込み順序と上書き（protected）ルールを実装。
  - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
  - Settings クラスを提供し、環境変数（J-Quants / kabuAPI、DB パス、Paper Trading 設定、監視閾値 等）をプロパティ経由で取得可能に。
  - 設定ウィザード CLI（kabusys.config_setup）を追加し、対話式で .env を生成／更新可能に。シークレットは表示をマスクして保存。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パス親ディレクトリ、config/*.yaml の存在・パース（PyYAML がある場合）などをチェック。--strict モードをサポート（警告を FAIL 扱い）。
- 実行系 / エンジン
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離して動作。
    - BrokerClientFactory を経由してブローカークライアントを作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、EngineConfig によりセッション実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた制御をサポート。
    - RiskManager に初期化時のパラメータ（max_position_pct、max_utilization、rate_limit_per_sec 等）を設定。
- 監視系
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず production 用 sqlite_path を使用する設計（監視 DB は常に同じ場所で記録）。
    - 起動時にプロセス優先度を "high" に設定。
    - stop_requested.flag による外部停止検知と例外処理時のログ出力。
- データベース / 分析
  - DuckDB 接続を前提とした分析処理を導入（Settings.duckdb_path）。
  - 監視テーブル初期化関数 init_monitoring_db を呼び出して整合性を確保。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告後 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数計算。単元株（lot_size）で丸め、per-position 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer（手数料/スリッページ想定） を考慮した安全な割付処理を実装。価格欠損時のスキップや残差に基づく追加配分ロジックあり。
- 研究・ファクター計算
  - research.factor_research を追加。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB の prices_daily を用いて計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算（true range の NULL 伝播を考慮）。
    - DuckDB を SQL＋ウィンドウ関数で計算する設計。
- ユーティリティ
  - utils.process_priority: Windows/Linux(Mac含む) の差を吸収するプロセス優先度設定ユーティリティを追加。psutil に対する安全なフォールバックと例外ハンドリングを実装。
    - set_process_priority(level: "high"|"normal"|"low")
    - set_cpu_affinity(cpu_count: int | None)
- ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを計算して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）。
    - --from / --to / --db オプションをサポート。
- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0" を設定。
  - パッケージ __all__ に主要サブパッケージをエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- （特記事項なし）

Migration notes / 注意事項
- .env は絶対に Git にコミットしないでください（config_setup が生成する .env にも注意喚起コメントを含めています）。
- 本番運用（KABUSYS_ENV=live）の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は本番向けの追加警告を出します。
- Paper Trading を行う場合、KABUSYS_ENV=paper_trading を使用すると paper 用 SQLite に記録され、本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH により変更可）。
- MONITOR_POLL_INTERVAL に 1 未満の値や非整数を与えると警告してデフォルト（60 秒）にフォールバックします。
- process_priority / cpu_affinity は権限やプラットフォームに依存するため、設定に失敗すると警告を出して処理を継続します。

（以上）