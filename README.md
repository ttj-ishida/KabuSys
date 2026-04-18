KabuSys — 日本株自動売買システム
=================================

本ドキュメントはこのリポジトリ（src/kabusys 以下）の概要、機能、セットアップ手順、使い方、主要ディレクトリ構成を日本語でまとめた README です。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買／研究プラットフォームです。主な目的は以下：
- 戦略の研究（ファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（実口座／ペーパートレードの発注管理）
- 監視・リスク管理（稼働監視、ドローダウン監視、Kill Switch）
- ニュース NLP によるセンチメント評価・レジーム判定（OpenAI を利用）
- ペーパートレード検証レポート生成ツール

設計方針の抜粋：
- DB（DuckDB / SQLite）を用いた分析・ログ永続化
- 環境変数（.env）による設定管理、設定ウィザード／検証ツールを提供
- 本番（live）／ペーパートレード（paper_trading）環境の分離
- LLM 呼び出しはフェイルセーフ（リトライ・フォールバック）で実装

主な機能一覧
--------------
- 設定管理
  - .env 自動ロード（プロジェクトルートに .env / .env.local があれば読み込む）
  - interactive ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って data/paper_trading.db に記録（本番 DB と分離）
- 監視
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（アラート送信や Kill Switch 判定）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額・スコア重み、セクター制約、ポジションサイズ計算（単元株丸め含む）
- 研究用モジュール
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（OpenAI）
  - ニュースセンチメントのバッチ評価（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - LLM 呼び出しは gpt-4o-mini を想定、API エラーはリトライ・フォールバック
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定（psutil を利用）
- 永続化（監視用 SQLite）
  - monitoring_db.py に MonitoringDB クラス（system_status / trade_logs / positions / risk_logs / dashboard）

前提（推奨）
------------
- Python 3.10+
  - ソース内で | 型注釈等を使用しているため 3.10 以上を想定
- 必須パッケージ（一例）
  - duckdb
  - psutil
  - openai
- 任意（YAML 検証など）
  - PyYAML（validate_config で config/*.yaml の内容検証をする場合に必要）

セットアップ手順
----------------
1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

   （プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください）

3. .env を生成・編集
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - ウィザードは .env の初期作成・更新を支援します
   - あるいは環境変数を直接設定してください
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）

5. ディレクトリ作成（初回）
   - data/ および logs/ は自動作成されますが、必要に応じて事前に作成しておくと良いです。

使い方（起動例）
----------------
- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能
  - 監視プロセスは data/stop_requested.flag を検知すると終了します

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用の専用 SQLite に記録されます
  - 実行中に data/stop_requested.flag が作成されると安全に停止します
  - 実行は data/execution.pid（デフォルト）に PID を書きます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを上書き）

- AI 機能（プログラムから呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を使用
  - レジーム判定:
    - from kabusys.ai import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

停止／Kill Switch
-----------------
- 実行・監視ループはそれぞれプロセス内で stop フラグファイルを監視します:
  - data/stop_requested.flag — run_monitoring/run_execution が終了を検知するためのフラグ（手動で作成）
  - KillSwitch は条件（ドローダウン超過など）に該当した場合 data/kill.flag を書き込み、ExecutionEngine 側で停止を受け取れるようにする
- 実稼働時には KILL_FLAG_CLEAR_ON_START 環境変数に注意（本番では 0 推奨）

ログ
----
- ログは stdout（コンソール）と日次ローテートファイル（LOG_DIR/<app_name>.log）に出力されます
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL（デフォルト INFO）

主要なファイル・ディレクトリ構成
-------------------------------
（src/kabusys をルートとして抜粋）

- __init__.py
- config.py
  - Settings クラス（環境変数 / .env の解決）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - 実行エンジン起動スクリプト
- run_monitoring.py
  - 監視ループ起動スクリプト

- utils/
  - logging_setup.py — 統一ロギング設定
  - process_priority.py — 優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・MonitoringDB
  - system_monitor.py — システム稼働・データ鮮度チェック
  - risk_monitor.py — ドローダウン・ポジション数監視
  - trade_monitor.py — （発注ログ監視）※実装ファイルあり
  - kill_switch.py — kill.flag を書くロジック
  - monitoring_engine.py — 各モニタを束ねる

- execution/
  - execution_engine.py — 実行エンジン本体（EngineConfig など）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    （ブローカークライアント抽象化・受注管理・リスク制御等）

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・丸め・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — ファクター計算（momentum／value／volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py — ニュース NLU（OpenAI）で銘柄別スコアを取得して ai_scores に書き込む
  - regime_detector.py — マクロ+ETF MA200 を合成してレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート出力

運用に関する注意点
------------------
- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config は live 時に追加警告を出します。
- OpenAI API キーを扱う場合は .env を Git 管理下に置かないでください（config_setup でもその旨の警告があります）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- ローカルでは psutil による優先度設定が失敗する場合があります（権限不足等）。その場合は警告が出てスキップされます。

よくあるコマンドまとめ
---------------------
- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はリポジトリ内のコード（主要ファイル）を参照して作成しました。実際の運用や追加機能（ブローカープラグイン、データパイプライン、CI/CD、詳細な設定ファイルなど）はプロジェクトの拡張に応じてさらにドキュメント化してください。必要であれば各モジュールの API 使用例や設定例（.env.example）も作成できます。希望があれば追加で作成します。