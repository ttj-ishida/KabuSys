README
=====

概要
----
KabuSys は日本株向けの自動売買／研究／監視を目的とした Python パッケージです。
このリポジトリは下記の主要機能を含み、ローカルの DuckDB / SQLite を用いたデータ処理と、
ブローカー接続・モニタリング・Paper Trading 検証・LLM を用いたニュース評価などを提供します。

主な特徴
-------
- Execution Engine 起動スクリプト（本番 / Paper Trading 切替対応）
- 監視（Monitoring）コンポーネント：システム状態、注文滞留、ドローダウン監視、Kill Switch
- 監視データの永続化（SQLite）と簡易ダッシュボード（Streamlit）
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・リスク適用・株数決定）
- リサーチ向けモジュール：ファクター（Momentum, Volatility, Value）計算、特徴量探索（IC など）
- AI モジュール：ニュースのセンチメント評価（OpenAI）と市場レジーム判定
- Paper Trading 向け検証レポート生成ツール

セットアップ
----------
1. Python 環境を作成します（例: venv）。
   - 推奨: Python 3.9+（プロジェクトの実行環境に合わせてください）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要なパッケージをインストールします（主要依存のみの例）。
   実際のプロジェクトでは requirements.txt を用意している想定です。最低限必要なもの:

   ```bash
   pip install duckdb psutil openai streamlit requests
   ```

3. 環境変数を設定します。
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（既存 OS 環境が優先）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定（主な環境変数）
------------------
以下は Settings クラスで参照される主要な環境変数の一覧（抜粋）です。

- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID を保存するファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

注意:
- Settings は .env / .env.local を自動読み込みします。既存 OS 環境は上書きされません（.env.local は override=True）。
- 環境変数が必須の場合（Settings._require による）は未設定時に例外が投げられます。

使い方
------

起動スクリプト（Execution）
- 実際に注文を行う ExecutionEngine を起動します。
- KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- 起動前に必要な環境変数を設定してください（API キー等）。

起動コマンド例:

```bash
# 環境変数を設定する例（bash）
export KABUSYS_ENV=paper_trading
export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
# 必要な API キー等も設定

python -m kabusys.run_execution
```

監視ポーリング（Monitoring）
- SystemMonitor をポーリングし、SQLite に監視ログを残します。
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
- Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（監視ログは本番 DB にまとめる設計）。

起動コマンド例:

```bash
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

Streamlit ダッシュボード
- 監視データを可視化する簡易ダッシュボードです（読み取り専用で SQLite を開きます）。

起動例:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

Paper Trading 検証レポート
- Paper Trading の SQLite（data/paper_trading.db）から検証レポートを生成します。

CLI 例:

```bash
# デフォルト DB を使う場合
python -m kabusys.tools.paper_verification_report

# 期間指定・DB指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

AI 関連
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に書き込みます。
  - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込みます。

運用上の注意
- run_execution / run_monitoring は起動時にプロセス優先度を high に設定しようとします（プラットフォーム依存・権限が必要）。
- ExecutionEngine 側の停止指示は kill.flag により行われます（KillSwitch が書き込む）。Execution 側は起動時に kill.flag をクリアする設定があります（Settings.kill_flag_clear_on_start）。
- Paper Trading と本番 DB は分離して管理してください（PAPER_TRADING_SQLITE_PATH を利用）。

ディレクトリ構成（抜粋）
---------------------
以下は主要ファイル／モジュールの構成（src/kabusys 以下）と簡単な説明です。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper/live 切替）
- config.py
  - 環境変数読み込みと Settings クラス
- __init__.py
  - パッケージメタ情報（バージョン等）

- ai/
  - news_nlp.py: ニュースの LLM スコアリング（OpenAI 連携）
  - regime_detector.py: 市場レジーム判定（MA200 + マクロセンチメント）

- monitoring/
  - monitoring_db.py: SQLite の監視用永続化層（テーブル初期化・CRUD）
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py: 注文滞留・約定異常の検出
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag の読み書き（Execution 停止トリガー）
  - alert_manager.py: LINE 通知（クールダウン管理付き）
  - monitoring_engine.py: 複数モニタの統合ループ
  - streamlit_dashboard.py: Streamlit ベースの簡易ダッシュボード

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（equal / score）
  - position_sizing.py: 株数計算（risk_based / equal / score）
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value のファクター算出（DuckDB 使用）
  - feature_exploration.py: 将来リターン・IC・統計サマリー

- execution/
  - order_manager.py: 注文フロー制御（OrderState 管理）
  - reconciler.py: 起動時の注文・ポジション同期処理
  - （その他 broker_factory, order_repository, execution_engine 等が存在する想定）

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成 CLI

- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

データ・DB の既定値
------------------
- DuckDB: data/kabusys.duckdb
- 監視用 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag

マイグレーション
- monitoring_db.init_monitoring_db は冪等（存在確認の上 CREATE）。既存スキーマへの列追加等も簡単なマイグレーションを含みます。

ログとデバッグ
- LOG_LEVEL 環境変数でログレベルを変更します（デフォルト INFO）。
- run_* スクリプトは logging.basicConfig(level=logging.INFO) を使用しています。

その他
-----
- 本リポジトリはローカル実行 / 研究・検証用のコードが多く含まれており、外部 API キーやブローカー設定が必要です。実運用に移す前に充分なテストとコード監査を行ってください。
- AI モジュールは外部 API（OpenAI）を使用します。料金やレート制限、プライバシーに注意してください。

ライセンス・貢献
----------------
- 本 README はコードベースの説明用です。ライセンスやコントリビュートガイドが別途ある場合はそちらに従ってください。

以上。README に記載した各スクリプト／関数の詳細は該当モジュールの docstring を参照してください。