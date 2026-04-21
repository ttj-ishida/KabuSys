KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視ツール群です。
主に以下の責務を持つコンポーネントを含みます。

- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理を行う
- 監視（Monitoring）：システム/注文/リスクの定期チェックと Kill Switch
- リサーチ（Research）：DuckDB を使ったファクター計算・特徴量解析
- ポートフォリオ構築（Portfolio）：候補選定・配分・株数決定ロジック（純粋関数）
- AI モジュール（AI）：ニュースの NLP スコアリングや市場レジーム判定（OpenAI）
- ユーティリティ：設定管理 (.env)、ログ設定、プロセス優先度設定 等

以下にプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を示します。

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコアライブラリ群および起動スクリプト群です。
設計上のポイント：

- 環境変数/.env による設定管理（config_setup によるウィザード）。
- ExecutionEngine は実際のブローカー（kabuステーション）またはペーパートレード用の Mock を切替可能。
- Monitoring はシステム健全性・注文状況・リスク（ドローダウン／ポジション数）を定期的に記録・評価し、必要時に Kill Switch（data/kill.flag）を書き込む。
- DuckDB を分析用に使用、SQLite を監視／注文ログ用に使用。
- OpenAI を利用したニュース NLP / レジーム判定機能を備える（APIキー必須）。

主な機能一覧
---------------
- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を利用し paper_trading.db を使用。
- 監視起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）。
  - Monitoring は環境に関わらず production 用 sqlite_path を使用する点に注意。
- 設定関連
  - config_setup.py: .env を対話的に生成/更新するウィザード。
  - validate_config.py: .env と config/*.yaml の内容を起動前に検証。
- ツール
  - tools.paper_verification_report: ペーパートレード実行ログから合否判定用のレポートを生成。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、重み算出、セクター上限適用、ポジションサイズ計算など（テスト容易）。
- AI
  - news_nlp.score_news: OpenAI を使ってニュース記事を銘柄ごとにセンチメントスコア化し ai_scores に保存。
  - regime_detector.score_regime: ETF の MA 等とマクロニュースから市場レジームを判定し DB に保存。
- ロギング & プロセス制御
  - utils.logging_setup.setup_logging: stdout + 日次ローテートファイルログを統一設定。
  - utils.process_priority.set_process_priority: OS に依存せずプロセス優先度を設定（psutil 必須）。
- 監視 DB 操作
  - monitoring.monitoring_db.MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard の永続化 API。

セットアップ手順
-----------------
1. Python 環境（推奨: 3.10+）を用意する
   - 仮想環境を作る例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールする
   - コードベースに基づく主な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML (validate_config の YAML 検証を行いたい場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   注意: 実行環境によっては psutil の権限（優先度変更や cpu_affinity）で権限不足の警告が出ることがあります。

3. .env を作成する
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成する。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な任意／重要な変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視DB, 例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START 等

   自動ロード: プロジェクトルートに .env/.env.local があれば起動時に自動読み込みされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. DB ディレクトリ/ファイルを作成する
   - デフォルトでは data/ 配下を使います。スクリプト実行時に自動で作られる場合がありますが、権限等で失敗する場合は手動作成してください。

使い方（基本コマンド）
---------------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密チェック（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading を指定すると MockBroker と data/paper_trading.db を使用して本番 DB と分離します。
    - 起動時に data/stop_requested.flag があると起動せず終了します。
    - 起動中に停止するには data/stop_requested.flag を作成するか、ExecutionEngine の Kill Switch を使って data/kill.flag を書きます。

- 監視（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存せず）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH  または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラム的に呼ぶ）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...) を呼んで ai_scores に書き込みます（OpenAI API キーが必要）。

- ログ
  - デフォルトは logs/ に日次ローテーションで出力（setup_logging により設定）。
  - LOG_DIR 環境変数や setup_logging の引数で変更可。

運用上の注意
-------------
- Monitoring は常に Settings.sqlite_path（本番向けパス）を使用するので、ペーパートレード時でも監視 DB を分けたい場合は設定を見直してください。
- run_execution は KABUSYS_ENV=paper_trading で paper_trading 用 DB を使用して本番 DB と分離します。
- Kill Switch（data/kill.flag）に関する設定:
  - KillSwitch は RiskMonitor 等の結果に基づいて data/kill.flag を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動でクリアされますが、本番では 0 を推奨します。
- OpenAI 呼び出しは API クォータ・エラー（429 等）を取り扱う実装になっていますが、API キーやコストには注意してください。
- psutil を用いたプロセス優先度変更や CPU affinity 設定は OS の権限に依存します。適切な権限で実行してください。

主要ファイル / ディレクトリ構成
-----------------------------
（ソースは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - config.py                      — 環境変数 / 設定読み込みロジック（自動ロード）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成ツール
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）による ai_scores 作成
    - regime_detector.py           — マクロ + ETF MA による市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - risk_adjustment.py           — セクター上限・レジーム乗数
    - position_sizing.py           — 株数決定・スケーリング・単元丸め
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py       — 将来リターン計算・IC・統計サマリ等
  - monitoring/
    - monitoring_db.py             — SQLite テーブル作成 & MonitoringDB クラス
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — （注文）トレード監視（滞留・異常等）
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - monitoring_engine.py         — 各 Monitor を束ねる
    - kill_switch.py               — data/kill.flag の書き込み管理
    - alert_manager.py             — (実装済みの場合) 通知管理（LINE等）
  - execution/
    - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py
      — 実行エンジン構成要素（発注管理、リスク管理、ブローカ抽象化等）
  - data/ (runtime)
    - stop_requested.flag          — 手動停止要求（起動スクリプトが参照）
    - kill.flag                    — Kill Switch（監視が書き込む）
    - execution.pid                — 実行プロセス PID（ExecutionEngine が書込む）
    - monitoring.db / paper_trading.db / kabusys.duckdb など（DB ファイル）
  - utils/
    - logging_setup.py             — ログ初期化ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ

（注）上記はコードベース内の主要モジュールを抜粋した説明です。実際のファイル数や細分化はリポジトリの内容に準じます。

よくある操作例
----------------
- 監視を 30 秒間隔にしたい:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード実行（環境変数で切替）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- OpenAI を用いてニューススコアを当日のデータで計算（プログラム的に）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")

その他
-----
- validate_config は config/*.yaml の存在・基本的なパースチェックも行います（PyYAML が必要）。
- DuckDB は分析用に最適化されています。research モジュールは prices_daily / raw_financials 等のテーブルを参照します。
- 本 README はコードのドキュメントを要約したものです。詳細な内部仕様や論理は該当モジュールの docstring を参照してください。

問題・拡張案・運用相談があればどの点を補足したいか教えてください。README をプロジェクトの実情（依存ファイル名・実際の起動コマンド）に合わせてさらに整形できます。