# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
リリース日はソースコードの最終更新日を基準にしています。

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買 (KabuSys) の基本機能群を実装しました。

### 追加
- パッケージメタ情報
  - kabusys パッケージ version 0.1.0 を追加。

- 設定・環境管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得する機能を追加。
    - J-Quants / kabuステーション / LINE / DB パス /監視しきい値 等のプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実装（無効値は例外を送出）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH サポート。
  - .env 自動読み込み機構を実装（プロジェクトルート判定、.env/.env.local の読み込み、既存 OS 環境変数保護）。
  - .env の対話式ウィザード (config_setup.py) を追加。
    - 秘匿値マスク表示、選択肢・デフォルト提示、.env ファイル出力。
  - 設定検証 CLI (validate_config.py) を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース確認（PyYAML がある場合）。
    - 本番 (live) 向けの追加注意喚起（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行スクリプト
  - run_execution.py を追加（ExecutionEngine 起動ラッパ）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し MockBrokerClient を利用可能な設計で分離。
    - BrokerClientFactory 経由でブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動処理（PID ファイル・停止フラグ処理含む）。
    - RiskManager 用のデフォルト RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring.py を追加（SystemMonitor ポーリングループ起動スクリプト）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は常に本番 sqlite_path を使用する（環境に依らず監視 DB を共通で参照する設計）。
    - 停止フラグ (data/stop_requested.flag) の検知による安全停止を実装。

- モニタリング関連
  - init_monitoring_db 呼び出しによる監視テーブル初期化を実行スクリプトで実行（冪等）。
  - SystemMonitor（監視ロジック）は別モジュールとして分離して利用。

- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority を追加。
    - Windows / POSIX を吸収した set_process_priority(level) を実装（"high"|"normal"|"low"）。
    - set_cpu_affinity(cpu_count) の実装（指定コアにピンニング、失敗時は警告を出しスキップ）。
    - psutil の権限エラー等を安全ハンドリング。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値超過のセクターの新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に従った発注株数計算。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に対するスケーリング、cost_buffer による保守的見積り、残差に基づく lot 単位での追加配分アルゴリズムを実装。

- リサーチ / ファクター計算（部分実装）
  - research.factor_research の骨格と定数、calc_momentum の説明を追加（モメンタム・MA200乖離等の計算を目的とした設計）。（注: ファイルは途中まで実装）

- ペーパートレード検証ツール
  - tools.paper_verification_report を追加。
    - PAPER_TRADING_SQLITE_PATH を参照してレポート生成。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - 一連の閾値を用いた PASS/FAIL 判定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）。
    - P95 の計算、データ不足時の N/A ハンドリング、日付フィルタ（ISO8601 UTC 形式）対応。

- その他ユーティリティ
  - tools パッケージ初期化ファイルを追加。
  - utils パッケージ初期化ファイルを追加。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 注意事項 / 実装上の制約
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視 DB に常に sqlite_path（本番設定）を使用します。paper_trading 環境でも監視 DB は分離されません（設計上の意図による）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離します。
- process_priority / cpu_affinity はプラットフォームや権限に依存するため失敗時は警告を出してスキップする設計です。
- 一部モジュール（例: research.factor_research）の実装は未完の箇所があります。今後のリリースで拡張予定です。

---

今後の予定（例）
- research モジュールの完成（モメンタム・バリュー等の計算実装）。
- ExecutionEngine / Broker クライアントの詳細な実装とテストカバレッジ拡充。
- 監視・アラート連携（LINE 通知など）の強化とドキュメント整備。