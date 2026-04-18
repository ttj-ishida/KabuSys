# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルではリポジトリから推測される主要な追加・変更点を日本語でまとめています。

フォーマット: [バージョン] - YYYY-MM-DD

---

[0.1.0] - 2026-04-18
Added
- 初期リリースとして以下の主要コンポーネントを追加。
  - 環境/設定管理
    - 自動 .env ロード機能（.git または pyproject.toml をプロジェクトルートとして探索）。
    - 高機能な .env パーサ（export 形式、クォート/エスケープ、インラインコメント処理対応）。
    - Settings クラスによる環境変数ラッパー（J-Quants / kabu API / DB パス / 監視閾値 / 環境判定などのプロパティを提供）。
    - settings インスタンスをモジュールレベルで提供。
  - 設定関連 CLI
    - config_setup: 対話式ウィザードで .env を作成・更新する CLI（シークレット入力、選択肢、デフォルト提示、保存確認など）。
    - validate_config: .env と config/*.yaml の事前検証ツール。必須環境変数チェック、パス存在チェック、YAML パース検証（PyYAML 利用）、本番用ガード（LINE 設定や Kill Switch の警告）、`--strict` オプションで警告も失敗扱いに可能。
  - 実行系起動スクリプト
    - run_execution: ExecutionEngine の起動スクリプト。
      - 起動時にプロセス優先度を高に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動と停止フラグ監視（data/stop_requested.flag）。
      - デフォルトの RiskManager 設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 設定, max_drawdown 等）をコード上に定義。
      - 起動時に監視テーブルの存在を保証する init_monitoring_db 呼び出し。
  - 監視系起動スクリプト
    - run_monitoring: SystemMonitor ポーリングループの起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、不正値は警告の上デフォルトにフォールバック。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視用 DB を共通で参照）。
      - stop フラグ（data/stop_requested.flag）検知で安全にループ終了。
      - check_once() 実行時の例外はログに出力して次ポーリングに継続。
  - ログ・プロセスユーティリティ
    - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority: Windows/Linux/macOS 間の差分を吸収するプロセス優先度設定ユーティリティ（psutil ベース）。CPU affinity 設定関数も提供。権限不足や未サポート環境では警告ログを出力してスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank）。
      - calc_equal_weights / calc_score_weights: 等金額およびスコア比例配分（スコア合計が 0 の場合は等金額にフォールバック）。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限の適用（既存保有の時価を元に新規候補を除外、"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング。未知レジームは 1.0 にフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定。単元株（lot_size）丸め、1銘柄上限や aggregate cap（available_cash）を考慮したスケーリング、cost_buffer（手数料・スリッページ見積り）対応。多数の安全弁（価格未取得時のスキップ、端数配分の安定化ロジック）を実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。
      - system_status / trade_logs / risk_logs 等から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出。
      - デフォルト閾値（稼働率 >= 99%、成功率 >= 90% 等）による PASS/FAIL 判定を出力。
      - --from / --to / --db オプションに対応。DB 存在チェックと例外ハンドリングを実装。
  - リサーチ（ファクター計算）
    - research.factor_research: Momentum/Value/Volatility/Liquidity 等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。momentum 計算関数（calc_momentum）の実装を開始（コードベース内に基準日や窓幅などの定数を定義）。
  - パッケージメタ
    - __version__ = "0.1.0" を設定。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated / Removed / Security
- 該当なし。

注意事項 / 既知の設計上のポイント
- apply_sector_cap 内に価格欠損時の挙動に関する TODO コメントあり（price が 0.0 の場合に過小見積りとなる可能性）。将来的に前日終値等のフォールバックを導入する予定。
- run_monitoring は監視 DB として常に settings.sqlite_path を使用する（環境に依存しない運用を想定）。paper_trading 実行と監視 DB の分離は run_execution 側で制御。
- process_priority / set_cpu_affinity は権限不足や未サポート OS の場合に操作をスキップし、警告ログを出力する実装。
- research.factor_research の calc_momentum 等、一部関数はまだ実装継続中（コード末尾が途中の状態）。本リリースでは骨組みと定数を提供しているが、完全実装は次期リリースを予定。

---

今後の予定（推測）
- research.* の各ファクター完全実装とユニットテスト追加
- strategy / execution の統合テスト、MockBroker の拡充
- config/monitoring に関するドキュメントおよび運用手順の整備
- ログ回転・アーカイブや監視アラート（LINE 等）の追加強化

---