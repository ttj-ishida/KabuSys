# CHANGELOG

すべての非互換性のある変更はメジャー番号を増やした新リリースで示します。
このファイルは「Keep a Changelog」形式に準拠しています。

## [Unreleased]

## [0.1.0] - 初回リリース
初回公開。以下の主要機能・ユーティリティ・CLI を追加。

### 追加 (Added)
- アプリケーション初期バージョンを追加（__version__ = 0.1.0）。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag による安全停止対応。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視データは本番 DB）。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）・OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグによる安全停止、実行中 PID ファイル管理（data/execution.pid）。
- 設定関連
  - config.Settings: 環境変数/`.env` ベースの設定クラスを追加。
    - 自動 .env 読み込み機構（プロジェクトルートの検出: .git または pyproject.toml）を搭載。
    - .env/.env.local の読み込み優先度、OS 環境変数保護（protected）対応。
    - 各種設定のプロパティ化（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）とバリデーションを実装。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE の検証。
  - config_setup CLI: 対話式ウィザードで .env を生成/更新するツールを追加。
    - 秘密値はマスク表示、既存値の再利用、確認プロンプト、保存機能を備える。
  - validate_config CLI: 起動前設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検査（PyYAML があれば）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_DIR 指定やディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
    - 既存ハンドラのクリアで二重登録を防止。
  - utils.process_priority:
    - psutil を利用して Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築（純関数群、DB非依存）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供（スコア全て0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 同一セクター集中超過時に新規候補を除外するロジックを実装（unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した発注株数計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差処理による優先配分を実装。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH）からシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出してレポート出力。
    - デフォルトの合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義。
    - 日付レンジ指定（--from/--to）と DB パス上書き（--db）をサポート。

### 変更 (Changed)
- 起動スクリプトの初期処理としてプロセス優先度を "high" に設定（set_process_priority の呼び出しを追加）。
- run_monitoring が MONITOR_POLL_INTERVAL の不正値を検出した場合に警告を出しデフォルトにフォールバックするよう改善。
- ロギングは stdout を標準出力先に使用（cron/スケジューラでの取り扱いを考慮）。
- .env 読み込みロジックは OS 環境変数を保護しつつ .env.local で上書き可能（ローカル優先）。

### 修正 (Fixed)
- SQLite / DuckDB 接続の明示的な初期化とクローズ処理を追加（起動失敗時や終了時のリソースリークを低減）。
- ExecutionEngine 起動前に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等に対応）。
- run_execution が停止フラグを検知した場合にエンジン起動を抑止するように安全化。

### ドキュメント/ヘルプ (Added / Improved)
- 各モジュールに詳細な docstring を追加（設計意図、使い方、引数、制約、注意点など）。
- config_setup と validate_config に CLI ヘルプを実装。
- portfolio モジュールでは PortfolioConstruction.md / StrategyModel.md との関連を明記（実装の参照元をコメントで記載）。
- tools.paper_verification_report に使用方法と環境変数説明を追記。

### 既知の制約と注意事項 (Unresolved / Notes)
- price が欠損（0.0）の場合、apply_sector_cap や calc_position_sizes のエクスポージャー/株数計算が過少見積もりになる可能性がある旨をコメントで明記。今後の改善候補として前日終値等のフォールバックを検討。
- 一部機能は psutil や PyYAML 等の外部依存に依存。これらがない場合は該当機能をスキップまたは警告で代替する実装になっている。
- PAPER_FILL_MODE の不正値は Settings で ValueError を送出するため起動前に .env を検証することを推奨。

### セキュリティ (Security)
- .env は絶対にリポジトリへコミットしない旨を config_setup の生成ヘッダで明記。
- 秘密情報（API トークン等）は .env に格納する設計のため、運用上の取り扱いに注意（アクセス権限・ログ出力等）。

---

今後の予定（例）
- portfolio/研究系モジュールのテスト拡充（ユニットテスト・境界値テスト）。
- price 欠損時のフォールバック価格の導入（前日終値や取得原価）。
- ExecutionEngine / BrokerClient 周りのモックテスト・統合テスト強化。
- 運用向け監視・アラートの強化（LINE 通知のテンプレート化等）。

(注) 上記 CHANGELOG は提供されたコードから推測して作成しています。実際の変更履歴やリリース日付はプロジェクトの管理履歴に従って修正してください。