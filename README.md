# KabuSys — 日本株自動売買システム（README）

この README は、リポジトリ内のコードベースに基づく簡易ドキュメントです。起動スクリプト、設定管理、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

重要: 実行前に .env を作成し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。詳細は「セットアップ手順」を参照してください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主な設定）
- ファイル・ディレクトリ構成
- 運用上の注意点 / トラブルシューティング

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたシステム群の骨格です。
- 発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュースセンチメント / レジーム判定などをモジュール化して提供します。
- 設定は .env（および .env.local）で管理し、SQLite / DuckDB をローカルに用いてデータ永続化・分析を行います。
- paper_trading モード（KABUSYS_ENV=paper_trading）を使えば、本番 DB と分離したペーパートレードが可能です。

---

機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or ペーパー）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 設定・検証
  - config_setup.py: .env を対話式に作成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック（--strict オプションあり）
- 監視
  - monitoring_engine: SystemMonitor / TradeMonitor / RiskMonitor を束ねるポーリング実行
  - monitoring_db: SQLite ベースの監視テーブル（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch（kill.flag）により ExecutionEngine を安全に停止可能
- 注文 / 発注
  - ExecutionEngine（起動スクリプト経由）
  - ブローカークライアントのファクトリ（本番 API / MockBrokerClient を切り替え）
  - リスク管理（RiskManager）・注文管理（OrderManager）
- ポートフォリオ構築
  - 銘柄選定・重み付け（等分配 / スコア加重）
  - セクター制限、レジーム乗数
  - 株数算出（ロット丸め、資金制限、aggregate cap）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）など解析ユーティリティ
- AI
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントスコアの生成
  - regime_detector.score_regime: MA 分析 + マクロニュース（LLM）を組合せた市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパー取引 DB から検証レポートを生成

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 主要な依存例: duckdb, psutil, openai, PyYAML（オプション）, 等
   - （注）requirements.txt がない場合は上記パッケージを手動でインストールしてください。

4. .env を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリの作成
   - デフォルトでは data/ および logs/ を使用します。setup_logging は自動で作成を試みますが、権限の問題がある場合は事前作成してください。

---

使い方（主要コマンド例）
- ExecutionEngine を起動（デフォルト: PID ファイル生成、停止フラグ確認）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは data/paper_trading.db（デフォルト）へ記録されます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は settings.env にかかわらず production の sqlite_path を参照して初期化します（監視ログは本番 DB を使用）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。別パスを指定するには --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数を使用。

- AI 関連（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime は Python API として使用します。実行には OPENAI_API_KEY の設定が必要です（引数でのキー指定も可能）。

---

主要な環境変数（抜粋と説明）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading: MockBrokerClient を使い、発注はペーパー DB に保存
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- OPENAI_API_KEY（AI モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知に使用、任意）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））

運用で使うファイル（例）
- data/kill.flag — Kill Switch 用フラグファイル（作成されると ExecutionEngine 停止のトリガー）
- data/stop_requested.flag — run_monitoring / run_execution の停止フラグ検出に使用
- data/execution.pid — ExecutionEngine の PID ファイル（デフォルト場所は設定可能）
- logs/<app>.log — setup_logging により日次ローテートで出力されるログファイル

---

ディレクトリ構成（主なファイル / モジュール）
- src/kabusys/
  - __init__.py  (パッケージ定義)
  - config.py  (環境変数・Settings クラス・自動 .env ロード)
  - config_setup.py  (.env 対話式ウィザード)
  - validate_config.py  (設定検証 CLI)
  - run_execution.py  (ExecutionEngine 起動スクリプト)
  - run_monitoring.py  (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py  (ペーパートレード検証レポート)
  - utils/
    - logging_setup.py  (共通ログ設定)
    - process_priority.py  (プロセス優先度 / CPU affinity)
  - monitoring/
    - monitoring_db.py  (SQLite テーブル初期化・永続化 API)
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり・ファイルはリポジトリに含まれている可能性あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信ロジック、ファイル参照あり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (スキーマ / パイプライン関連モジュールが想定)
    - pipeline.py (get_last_price_date 等)
    - stats.py (zscore_normalize)
  - monitoring/、execution/、portfolio/、research/、ai/ はそれぞれ上記の責務を持つモジュール群

（※ 上記はリポジトリ内の主要ファイル一覧です。実際の細部実装や追加ファイルはリポジトリを参照してください。）

---

運用上の注意点 / トラブルシューティング
- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探して .env / .env.local を自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログディレクトリ作成失敗:
  - 権限やマウントの問題で logs/ の作成に失敗した場合、コンソール出力のみになります。setup_logging は失敗を警告します。
- psutil による優先度設定:
  - set_process_priority はプラットフォームや権限に依存します。AccessDenied 等が出る場合は警告を出してスキップします（挙動は安全側）。
- OpenAI API:
  - news_nlp / regime_detector は OPENAI_API_KEY が必要です。API 呼び出し時の 429・ネットワーク断・5xx はリトライロジックがありますが、キー未設定は例外になります。
- DuckDB / SQLite:
  - デフォルトの DB パス（data/*.db）を使用する場合、実行ユーザーに書き込み権限があることを確認してください。config の検証ツールは親ディレクトリの存在を警告します。
- Kill Switch:
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。kill.flag を誤ってクリアすると取り返しのつかない発注リスクがあります。
- ペーパートレード分離:
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 sqlite_path と分離されます。必ず env を確認してから起動してください。

---

追加情報 / 参考
- コード内ドキュメント（docstring）に各関数・クラスの挙動詳細が記載されています。挙動確認やテスト作成時は該当モジュールの docstring を参照してください。
- YAML 設定ファイル（config/*.yaml）や追加スクリプトが想定されています。validate_config.py は config/*.yaml の存在とパースをチェックします（PyYAML が必要）。

---

問題報告・貢献
- バグ報告や機能要望は issue を立ててください。プルリクエストは歓迎します。

以上。README の内容はコードの現状に基づいて作成しています。実運用前に必ず設定検証（python -m kabusys.validate_config）を行い、安全な環境での動作確認を実施してください。