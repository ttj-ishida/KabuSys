KEEP A CHANGELOG — KabuSys

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の形式に準拠して作成されています。
比較対象はリポジトリの現行スナップショット（バージョン 0.1.0 相当）です。

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加
- 基本アプリケーション情報
  - パッケージのバージョンとエクスポート一覧を追加（kabusys.__init__.__version__ = "0.1.0"）。

- 環境設定管理
  - .env の自動読み込み機能を実装（.env, .env.local をプロジェクトルートから読み込み）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサーを強化：
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの取り扱い（クォートあり/なしで挙動を分離）。
  - Settings クラスを提供し、環境変数から各種設定値を注入：
    - J-Quants / kabuステーション / LINE API / DB パス / 監視閾値 / 実行環境など。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - env/log_level のバリデーションと is_live / is_paper / is_dev ヘルパー。

- 環境設定ウィザード（CLI）
  - python -m kabusys.config_setup で対話的に .env を作成・更新するウィザードを追加。
  - シークレット入力のマスク表示、デフォルト/既存値の再利用、最終確認後の .env 保存をサポート。

- 設定検証ツール（CLI）
  - python -m kabusys.validate_config により起動前に設定不備を検出。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と YAML パースチェック（PyYAML 未インストール時は警告）を実施。
  - --strict フラグで警告を FAIL 扱いにできる。

- ログ設定ユーティリティ
  - kabusys.utils.logging_setup.setup_logging により一元的なログ設定を提供。
  - stdout 出力（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler、既定 logs/ ディレクトリ、30日保持）を設定。
  - LOG_DIR / LOG_LEVEL / 引数で挙動カスタマイズ可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

- プロセス制御ユーティリティ
  - kabusys.utils.process_priority.set_process_priority(level)：
    - Windows/Linux/macOS の差分を隠蔽してプロセス優先度を設定（high/normal/low）。
    - アクセス権限等で失敗した場合は警告を出してスキップ。
  - set_cpu_affinity(cpu_count) によりカレントプロセスを最初の N コアへピン留め可能（対応環境のみ）。

- 実行コンポーネント起動スクリプト
  - run_execution.py:
    - 実行エンジン（ExecutionEngine）起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知による安全停止、スレッドによるエンジン実行を実装。
    - リスク管理設定（RiskConfig）にデフォルト値を提供し、初期ポートフォリオ値は broker.get_available_cash() から設定。

- 監視コンポーネント起動スクリプト
  - run_monitoring.py:
    - SystemMonitor を定期ポーリングで実行するループを提供。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。無効な値はデフォルトへフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（監視 DB は本番 DB を参照する仕様）。
    - stop flag による停止、例外時のログ出力とポーリング継続を実装。

- モジュール: portfolio（銘柄選定・配分・調整）
  - portfolio_builder:
    - select_candidates: スコア降順＋signal_rank で上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分（スコア全て 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に同セクターの新規候補を除外（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知のレジームは 1.0 にフォールバックして警告。
    - コメントで将来の拡張（価格フォールバック等）を明記。
  - position_sizing:
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算ロジックを実装。
    - risk_based: 損切り幅・リスク許容率から目標株数を算出。
    - equal/score: ポートフォリオ比率と max_utilization を考慮した配分。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer（手数料・スリッページ想定）を加味した保守的見積り、端数反映アルゴリズムを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標を算出して標準出力にレポートを出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（平均/最大/P95）等。
    - デフォルト閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ (--from / --to)、--db オプションで DB パス指定可。

- 研究モジュール（着手）
  - research/factor_research.py にモメンタム等ファクター計算基盤を追加（DuckDB を用いた prices_daily/raw_financials 参照設計）。モジュールは設計方針と一定の定数定義、calc_momentum の冒頭実装を含む（後続実装または補完が必要）。

### 変更
- 監視用 DB 初期化の冪等化
  - init_monitoring_db(sqlite_conn) を run_execution/run_monitoring の起動時に呼び出して監視テーブルの存在を保証（存在する場合は無害）。

### 修正 / 安全対策
- 停止処理と安全性
  - run_execution/run_monitoring に stop flag（data/stop_requested.flag）を用いた外部停止機構を追加。実行中のスレッド/ループはフラグを検知して安全に停止。
  - run_execution は起動時に停止フラグが既に立っている場合は起動をスキップ。

- エラー耐性
  - run_monitoring の監視ループで monitor.check_once() が例外を投げてもループを継続し、ログに例外スタックトレースを出力して次回ポーリングまで待機する設計。

- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合はファイルハンドラを作成せず、コンソール出力のみ継続することで起動不能状態を回避。

### 既知の注意点 / TODO
- research/factor_research.calc_momentum がファイル末尾で途中（スニペットが途切れている可能性あり）。ファクター計算の完全実装は継続作業が必要。
- apply_sector_cap 内の注記: price_map に価格が欠損（0.0）する場合のエクスポージャー過少見積り問題が明記されており、将来的に前日終値や取得原価を用いるフォールバックが提案されている。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」仕様のため、ローカル開発環境での監視 DB を分離したい場合は運用上の取り決めが必要。
- process priority / cpu affinity の設定はプラットフォーム・権限に依存するため、設定失敗時はログ警告でスキップする仕様。

### 互換性 / マイグレーション
- 本リリースは初回としての追加が中心のため、既存ユーザー向けの破壊的変更は無し。
- .env 自動ロードや .env.local の優先度、Settings からの設定取得は自動で行われるため、環境変数の管理方針に注意してください（特に OS 環境変数の保護挙動）。

---

過去のバージョンとの差分や追加の運用ドキュメントが必要であれば、対象箇所（ex. 実行手順、.env 推奨設定例、監視の運用フロー等）を指定してください。