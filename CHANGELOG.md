# CHANGELOG

すべての著名な変更点を Keep a Changelog 形式で記録します。  
日付は本コードスナップショット作成日 (2026-04-23) を使用しています。

フォーマット:
- Unreleased: 今後の変更（このスナップショット時点の未リリース事項）
- 各バージョン: そのリリースで追加／変更／修正された主要事項

## [Unreleased]

- ドキュメントやテストの追加予定、内部 API の微調整などが想定されます。

---

## [0.1.0] - 2026-04-23
初回リリース。KabuSys の基盤となる設定管理、起動スクリプト、実行／監視ロジック、ポートフォリオ構築ユーティリティ、各種ユーティリティ、およびツール群を実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"`。
  - Python モジュール群（config, execution, monitoring, portfolio, utils, research, tools）を実装。

- 設定関連
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env ファイルパーサを実装。`export KEY=val`、引用符付き値（エスケープ処理）、インラインコメントの扱いなどに対応。
  - Settings クラスを追加し、環境変数アクセスを型安全に提供。J-Quants / kabu API / DB パス / paper trading など主要設定プロパティを提供。
  - PAPER_FILL_MODE の検証（有効値: "instant","partial","never","reject"）を実装。
  - 環境判定プロパティ（is_live, is_paper, is_dev）を提供。

- 設定ツール
  - config_setup: 対話式 .env ウィザードを実装。既存 .env 読み込み、入力プロンプト、ファイル書き込みをサポート。
  - validate_config: 起動前チェック CLI を実装。必須環境変数の確認、KABUSYS_ENV の妥当性、DB パスの存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）を実施。`--strict` モードで警告を FAIL 扱いに可能。

- 起動スクリプト / 実行系
  - run_execution: ExecutionEngine 起動スクリプトを実装。
    - プロセス優先度を起動直後に High に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock/実ブローカ切替対応想定）。
    - OrderRepository, OrderManager, RiskManager（既定値セット済み）、Reconciler を組み合わせて ExecutionEngine を組み立て、別スレッドでエンジンを実行。停止フラグ (data/stop_requested.flag) の監視と安全停止処理を実装。
    - 実行 PID を data/execution.pid に出力（設定参照）。
  - run_monitoring: SystemMonitor（監視）起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は常に本番用 sqlite_path を使用する設計（環境に依存せず監視データを統一して記録）。
    - 停止フラグ検知でループを終了、例外時はログ出力して次サイクルへフォールバック。
    - sqlite3 と DuckDB の接続確立／終了を適切に管理。

- 監視 / DB 初期化
  - monitoring_db 初期化呼び出しをエントリポイントで実行し、監視テーブルの存在を保証（冪等）。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: 統一的なロギングセットアップ関数を実装。
    - コンソール出力は stdout、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加。ログディレクトリを自動作成（失敗時は警告表示してコンソールのみで継続）。
    - ログローテーション 30 日分保持。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（Windows の priority class / POSIX の nice）を設定するユーティリティを実装。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未サポート OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア順ソート（タイブレークに signal_rank を使用）と上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別エクスポージャ計算に基づく候補の除外ロジック。売却予定銘柄の除外や "unknown" セクターの扱い。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0/neutral:0.7/bear:0.3）。未知レジームは警告のうえ 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method (`risk_based`, `equal`, `score`) に応じた発注株数決定。
    - 単元株 (lot_size) に丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積り、残余の分配ロジックなどを実装。

- ツール
  - tools.paper_verification_report: Paper Trading データベースから検証レポートを生成する CLI を実装。
    - 指標: 稼働率 (uptime), 注文成功率（Filled / Created）, 送信率（Sent / Created）, リスク却下数, レイテンシ（avg/max/P95）を集計。
    - P95 計算関数を実装。閾値を定義し PASS/FAIL 判定を出力。
    - コマンドライン引数で期間 (--from/--to) と DB パス (--db) を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH もサポート。

- リサーチ / ファクター計算（スキャフォールド）
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールの骨組みを追加（モジュール設計、定数、calc_momentum のインターフェースなど）。（ファイル末尾はスナップショット上で途中まで実装）

### 変更 (Changed)
- ロギングのデフォルト挙動:
  - StreamHandler は stderr ではなく stdout を使用（cron 等で stdout/stderr を一本化して扱いやすくするため）。
- .env 読み込み優先度:
  - OS 環境変数 > .env.local > .env の順で読み込む実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。

### 修正 (Fixed)
- 環境変数パースの改善:
  - 引用符付き値のエスケープ処理やコメント解釈の改善により、より安全に .env を読み込めるようにした。
- run_monitoring のポーリング間隔:
  - 環境変数 MONITOR_POLL_INTERVAL が不正な値（0 以下や非整数）の場合、デフォルト 60 秒にフォールバックして ValueError を回避。

### 注意事項 / 破壊的変更 (BREAKING CHANGES)
- 監視（run_monitoring）は「環境にかかわらず」本番の sqlite_path を使用する設計になっています（運用上、監視データを一箇所に集約する意図）。Paper トレード用に監視 DB を分けたい場合は運用ルールの変更が必要です。
- KILL_FLAG_CLEAR_ON_START の既定値は "0"（自動クリアしない）です。本番環境ではデフォルトのまま運用することを推奨します。

### セキュリティ (Security)
- 機密情報（API パスワードやトークン）は .env に保存される前提ですが、config_setup ではこれらをシークレット扱いにしてマスク表示するなど運用上の注意点を提供しています。`.env` は絶対にリポジトリにコミットしないでください。

---

参考: 今後の改善候補（未実装/検討中）
- factor_research の完全実装（モメンタム、バリュー、ボラティリティ等の完全化）。
- 銘柄ごとの lot_size をマスターから取得する設計への拡張。
- monitor / execution のユニットテストとエンドツーエンドテストの整備。
- ロガーの構成をさらに柔軟化（JSON 出力、外部集約対応など）。

--- 

（以上）