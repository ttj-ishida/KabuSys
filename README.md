KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買に必要なコンポーネント群（エンジン、モニタリング、ポートフォリオ構築、リサーチ、AI ベースのニュース解析など）を含む小規模なフレームワークです。  
主要な設計方針は安全性（ペーパートレードと本番の分離、Kill Switch）、再現性（時刻参照の制御）、およびテストしやすさ（副作用を抑えた関数設計）です。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory による実ブローカー / モックの切替
  - リスク管理（RiskManager）・注文管理（OrderManager）・照合（Reconciler）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存確認
  - TradeMonitor / RiskMonitor: 注文滞留・成立異常・ドローダウン・ポジション上限監視
  - KillSwitch: 指定条件で ExecutionEngine を停止するフラグファイル生成
  - MonitoringDB: SQLite に監視ログ / トレードログ / リスクログ / ダッシュボードを永続化
- Portfolio construction
  - 候補選定、等分配・スコア重み配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイジング（単元丸め、aggregate cap）
- Research（DuckDB を用いた分析）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（情報係数）計算、統計サマリー
- AI モジュール（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores に保存
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントの複合で市場レジーム判定
- ツール
  - config_setup: .env 対話式ウィザード（.env の初期作成 / 更新）
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB から運用検証レポート生成
- ユーティリティ
  - 統一ログ設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度 / CPU affinity 設定
  - .env 自動読み込み（プロジェクトルート検出）

セットアップ手順
---------------
1. Python の用意
   - Python 3.9+ を推奨（typing とモジュール互換性を確認してください）。

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - オプション: PyYAML（config/*.yaml の内容検証を行う場合）
     - pip install PyYAML

   （プロジェクトには requirements.txt が無い場合があるため、上のパッケージをインストールしてください。）

3. プロジェクトルートに移動
   - 本リポジトリをクローンし、src 配下が PYTHONPATH に含まれるようにセットするか、仮想環境内でパッケージをインストールしてください。

4. 環境変数 (.env) の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/よく使う環境変数（デフォルトがあるものを含む）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI を使う機能で必須
     - PAPER_FILL_MODE — instant | partial | never | reject (paper_trading 用)
     - KILL_FLAG_CLEAR_ON_START — 0/1（本番では 0 推奨）
   - .env の自動読み込み:
     - プロジェクトルートに .env / .env.local があれば kabusys.config が自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. データディレクトリ
   - デフォルトで data/ 以下に各 DB フォルダやフラグファイルが作られます。実行ユーザーに作成権限があることを確認してください。

使い方（主要スクリプト）
------------------------

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - data/execution.pid に PID を書きます（Engine の pid_file パスは Settings で設定）。

- 監視ループ起動（SystemMonitor の簡易ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用してログを残します。
  - data/stop_requested.flag を検出すると終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール呼び出し（プログラム内部 API）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と target_date を受け取り、DB に書き込みます。api_key を渡すか OPENAI_API_KEY を環境変数で設定してください。

- Kill Switch 操作
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine 停止をトリガーします。
  - 実行時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされる場合があるため、本番では 0 推奨。
  - clear() を呼ぶと kill.flag を削除できます（例: 実行前の手動クリア）。

開発 / デバッグのヒント
--------------------
- ログ: デフォルトは logs/<app_name>.log（TimedRotatingFileHandler：日次ローテーション、30日保持）と標準出力の両方に出力されます。LOG_DIR で変更可。
- SQLite / DuckDB のパスは Settings で制御できます（環境変数で上書き可）。
- validate_config は .env および config/*.yaml の基本的チェックを行います（PyYAML があれば YAML の簡易パースも行う）。
- テスト目的で自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはリトライとフェイルセーフロジックを持ち、API 失敗時は安全側の値（例: macro_sentiment=0.0）で継続します。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理、.env 自動読み込み
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py             — ニュースの LLM ベースセンチメント評価
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化レイヤ
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py (実装ファイルあり)
  - monitoring_engine.py   — 複数モニタを束ねるエンジン
  - kill_switch.py
  - alert_manager.py (実装ファイルあり)
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

data/ と logs/ ディレクトリ（実行時に生成）
- data/monitoring.db (default: SQLITE_PATH)
- data/paper_trading.db (paper_trading 用)
- data/kabusys.duckdb (default: DUCKDB_PATH)
- data/kill.flag, data/stop_requested.flag, data/execution.pid
- logs/<app_name>.log

よくある質問 / 注意点
--------------------
- ペーパートレードと本番の DB は明確に分離されます（paper_trading モード）。
- OpenAI を使用する機能は API キーが必須です。キーがない場合は呼び出し側で例外になります（またはモジュールにより安全側の挙動にフォールバックする場合もあります）。
- run_monitoring は本番の sqlite_path を常に使います（KABUSYS_ENV に依存しない）。
- MONITOR_POLL_INTERVAL に 0 以下を指定すると無効値としてデフォルト（60 秒）にフォールバックします。

貢献 / 拡張案
--------------
- BrokerClient の具体実装（kabuステーションクライアント）を追加して実売買を行う。
- 単体テスト / CI を整備（ユニットテスト、モックによる API 呼び出し検証）。
- stocks マスタに銘柄別 lot_size を持たせ、position_sizing の単元処理を銘柄別に対応。
- モニタリングのアラート出力先（LINE / Slack 等）のプラグイン化。

ライセンス
---------
プロジェクト内に LICENSE ファイルがある場合はそちらを参照してください（本README には明記されていません）。

---

この README はコードベースの主要機能と運用方法を簡潔にまとめたものです。細かい実装や追加オプションは各モジュール（例: kabusys.config, kabusys.ai.*, kabusys.monitoring.*）のドキュメント／docstring を参照してください。