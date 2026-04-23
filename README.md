# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム（KabuSys）の部分実装です。価格データ集計・ファクター計算・ポートフォリオ構築・ポジションサイジング・発注実行・監視・AI を用いたニュース解析などのコンポーネントを含みます。ここに含まれるスクリプトはローカル実行 / ペーパートレード / 本番運用のワークフローを想定しています。

主な設計方針
- モジュールはできるだけ純粋関数（副作用少）で設計：研究・計算部分は DB に依存せずメモリ計算可能にする箇所が多い
- 実行環境は環境変数（.env）で指定。config_setup.py による対話的生成と validate_config.py による起動前検証を用意
- Paper Trading は本番 DB と完全分離（専用 SQLite）になるよう配慮
- AI（OpenAI）を利用する機能は API キーが必要。失敗時はフェイルセーフで継続する設計

---

主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - 環境に応じて実ブローカー／モックブローカーを切り替え
  - ExecutionEngine を起動し発注・リスク管理・リコンシリエーションを実行
  - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）で制御
- 監視ポーリング（run_monitoring.py）
  - SystemMonitor を周期的に実行し system_status 等を monitoring DB に記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
  - Monitoring は環境に関わらず本番 sqlite_path を使用（監視は本番 DB を見張るため）
- 監視インフラ（monitoring/*）
  - MonitoringDB: SQLite に対する永続化ラッパー（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（アラート送信は別実装想定）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重・スコア重み付け、セクター上限適用、レジーム乗数、株数計算（lot 丸め・aggregate cap 対応）
- 研究 / ファクター計算（research/*）
  - モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上の prices_daily / raw_financials を用いて計算
  - 将来リターン・IC・統計サマリ等のユーティリティ
- AI モジュール（ai/*）
  - news_nlp: ニュース記事を集約して OpenAI（例: gpt-4o-mini）へ投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 判定を組合せて市場レジーム（bull/neutral/bear）を算出して DB に書き込む
  - OpenAI API 呼び出しはリトライやバリデーションを備え、失敗は安全にフォールバック
- ユーティリティ（utils/*）
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーティングファイル）
  - process_priority: クロスプラットフォームでプロセス優先度 / CPU affinity 設定
- 管理ツール
  - config_setup.py: .env ファイルを対話的に作成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の存在・基本整合性を検証する CLI
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成

---

セットアップ手順（ローカル開発向け、例）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 本リポジトリに明示的な requirements は含まれていないため、少なくとも以下が必要になる可能性があります:
     - duckdb, psutil, openai, pyyaml（config 検証用）など

4. .env の作成
   - 対話式: python -m kabusys.config_setup
     - J-Quants リフレッシュトークン、kabu API パスワード等を入力します
   - 手動作成: プロジェクトルートに .env を置く
     - 例（最低限）:
       JQUANTS_REFRESH_TOKEN=your_jquants_token
       KABU_API_PASSWORD=your_kabu_password
       KABUSYS_ENV=development
       LOG_LEVEL=INFO
     - 注意: .env は決して Git にコミットしないでください

5. 設定検証（起動前）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. DB / ディレクトリ準備
   - デフォルトでは data/ ディレクトリにファイルが作成されます（monitoring DB, paper_trading DB, logs/ 等）
   - logging_setup がログディレクトリ（デフォルト logs/）を自動作成します

---

使い方（主なコマンド例）
- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV を paper_trading にすると MockBrokerClient を使い、ペーパートレード DB（data/paper_trading.db）へ記録されます
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は data/execution.pid に PID が書かれます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path（デフォルト data/monitoring.db）を使用します
  - 停止: data/stop_requested.flag を作成すると両スクリプトが検知して停止します

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

- AI 機能（プログラム的呼び出し）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
  - live: 本番運用（十分注意して設定すること）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60 秒）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（"instant"|"partial"|"never"|"reject"）

---

停止・Kill Switch の動作
- KillSwitch はリスク監視（drawdown や保有数超過）などの条件で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- run_execution/run_monitoring は data/stop_requested.flag の存在を検知して安全にシャットダウンします
- Settings.kill_flag_clear_on_start が 1 の場合起動時に kill.flag を自動クリア（本番では 0 推奨）

---

ディレクトリ構成（src/kabusys の主要ファイル）
- __init__.py
- config.py: 環境変数読み込み・Settings クラス
- config_setup.py: .env 対話式ウィザード
- validate_config.py: 起動前設定検証 CLI
- run_execution.py: ExecutionEngine 起動スクリプト
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト

- ai/
  - news_nlp.py: ニュース NLP（OpenAI）による銘柄別センチメント生成
  - regime_detector.py: 市場レジーム判定（MA + LLM）

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 株数決定・資金配分・丸め
  - risk_adjustment.py: セクター制限・レジーム乗数

- research/
  - factor_research.py: モメンタム・ボラティリティ・バリュー計算（DuckDB）
  - feature_exploration.py: 将来リターン計算・IC・統計サマリ

- monitoring/
  - monitoring_db.py: SQLite テーブル作成 + MonitoringDB ラッパ
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: 発注ログ・滞留注文チェック（ファイル未掲示のため参照箇所あり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 各 Monitor を束ねる

- utils/
  - logging_setup.py: ログ初期化（stdout + 日次ローテート）
  - process_priority.py: プロセス優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

---

運用上の注意
- .env は必ずローカル管理し、リポジトリへコミットしないでください
- KABUSYS_ENV=live の場合はログ・アラート設定、kill flag の取り扱い等を十分に確認してください
- OpenAI 等外部 API 呼び出しを行う機能は API 利用料が発生します。API キーの保護・呼び出し回数に注意してください
- 本リポジトリは実運用向けの完全実装ではなく、調整・テスト・安全弁（レート制限、リトライ、デグレードパス）の確認が必要です

---

追加情報 / 次のステップ
- .env の初期化: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。サードパーティのロギング集約・監視ツールと連携する場合はここを拡張してください
- DuckDB / SQLite のスキーマは monitoring_db.init_monitoring_db 等で自動作成・マイグレーションされます

ご不明な点や README に加えてほしい具体項目（例: 実行例の詳細、環境変数の完全一覧、デバッグ方法など）があれば教えてください。必要に応じてさらに詳細な運用マニュアルを作成します。