# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（現状スナップショット）から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: リリース日と主な追加・変更点

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-20

初回公開リリース。自動売買システム「KabuSys」の基本機能群を実装しています。以下はコードベースから抽出した主な追加点、設計上の挙動、および既知の制限です。

### 追加 (Added)
- 基本パッケージ定義
  - パッケージバージョン: `__version__ = "0.1.0"`

- 環境設定・管理
  - Settings クラスにより環境変数をプロパティとして参照可能（J-Quants / kabu API / DB / ログ等）。
  - .env の自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込む）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
  - .env のパースは export 文、シングル/ダブルクォート、エスケープ、インラインコメントを考慮して実装。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を生成・更新可能（`python -m kabusys.config_setup`）。
  - validate_config: .env と config/*.yaml の整合性検証 CLI（`--strict` オプションで警告を失敗扱いにできる）。

- 実行/監視用エントリポイント
  - run_execution: ExecutionEngine を起動するスクリプト。環境により Paper Trading 用の MockBroker を利用し、Paper 専用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - BrokerFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動を含む。
    - PID ファイル管理、data/stop_requested.flag による安全停止ハンドリングを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（意図的な隔離／運用方針）。

- データ分析基盤
  - DuckDB 接続を受ける設計（Settings.duckdb_path, 各エンジンで duckdb.connect を利用）。

- ポートフォリオ構築ライブラリ (純粋関数群)
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（全スコア 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づき新規候補を除外するロジック（"unknown" セクターは制限除外）。
    - calc_regime_multiplier: market レジーム (bull/neutral/bear) に応じた乗数（未知レジーム時は 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各割当方式に対応。損切り・リスク・単元株（lot_size）丸め、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料/スリッページ保守）を実装。
    - 単元・スケールダウンの端数処理や再配分ロジックを備える。

- ツール
  - tools.paper_verification_report: Paper Trading DB を読み取り、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（P95 等）などの検証レポートを標準出力に生成する CLI を提供。
    - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - 合格基準となる閾値（稼働率 99% 等）を定義し PASS/FAIL 判定を出力。

- ユーティリティ
  - utils.logging_setup: ルートロガーを初期化する共通関数。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）を設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: Windows / POSIX を吸収してプロセス優先度設定（high/normal/low）と CPU affinity 固定をサポート。権限不足等の失敗は警告ログでスキップ。

### 変更 (Changed)
- 設定読み込みと優先順位:
  - OS 環境変数 > .env.local > .env の優先度で読み込み。既存 OS 環境変数を保護する実装あり（protected set）。
- ログ設定:
  - stdout を利用する設計（cron/tascheduler でのリダイレクトを想定）。

### 修正 (Fixed)
- 不正な環境変数値のフォールバックを個別にハンドリング（例: MONITOR_POLL_INTERVAL、PAPER_FILL_MODE の検証）。
- DB テーブルが存在しない場合でも init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等に初期化）。

### 既知の制限 / 注意点 (Known issues / Notes)
- factor_research モジュールはファイル末尾で未完（途中で切れている／実装継続が必要な箇所あり）。研究用途のファクター計算ロジックは現在作業中。
- apply_sector_cap の価格欠損時の挙動について注釈あり（price が 0.0 の場合、エクスポージャーが過小見積りされるリスク）。将来的にフォールバック価格の導入が想定されている。
- process_priority / set_cpu_affinity は OS 権限に依存し、権限不足や未対応 OS では設定がスキップされる（警告ログ）。
- run_monitoring は監視に常に本番 sqlite_path を使用するため、ローカル開発と監視 DB を明確に分離したい場合は運用上の注意が必要。
- logging_setup: ログディレクトリの作成失敗時はファイル出力を無効化する仕様。ログ出力先の権限設定には注意。

### 実行コマンド例
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する: --db /path/to/paper_trading.db

---

今後の改善候補（リリースノートに反映予定）
- factor_research の完実装（価格・FIN データ参照の安定化、DuckDB クエリ最適化）
- price 欠損時のフォールバックロジック（前日終値等）
- ログの構造化（JSON 出力）やメトリクス統合（Prometheus 等）
- 単体テスト・統合テストの追加と自動化（CI）
- 実運用向けの監視・アラート強化（LINE 通知の堅牢化、アラートチャンネルの拡張）

---

（注）この CHANGELOG は提供されたコードスナップショットから推測して作成しています。実際のコミット履歴や PR の粒度とは差異がある可能性があります。必要であれば、より詳細な差分情報（Git のコミットログ等）を提供してください。