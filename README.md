KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリと起動スクリプト群を含みます。  
ここではプロジェクト概要、主な機能、セットアップ方法、使い方、ディレクトリ構成などを日本語で説明します。

プロジェクト概要
---------------
KabuSys は次のような機能を持つモジュール群からなる自動売買基盤です：

- データパイプライン（DuckDB を用いた時系列データ参照）
- ファクター計算・研究用モジュール（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング・セクター制約）
- 実行エンジン（ExecutionEngine）/ 注文管理 / ブローカー抽象化（paper_trading モード対応）
- 監視（System / Trade / Risk の監視と Kill Switch）
- AI モジュール（OpenAI を使ったニュースセンチメント評価 / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザードなど）
- 各種 CLI ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）

主な特徴
--------
- 環境変数/.env による柔軟な構成（config.Settings）
- Paper Trading と Live を分離（paper_trading は専用 SQLite DB を使用）
- 監視ループはプロセス優先度を上げて定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可）
- Kill Switch（監視により危険検知時にファイルで実行を停止）
- OpenAI を使ったニュース NLP（スコアリング）と市場レジーム判定（フェイルセーフ実装、リトライ）
- DuckDB を使った分析/ファクター計算（研究用途向け）

必要な依存パッケージ（主なもの）
--------------------------------
最低限（pip 等でインストールしてください）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で YAML を検証する場合に必要）
- sqlite3（標準ライブラリ）

環境によって他のパッケージが必要になる場合があります（例: 開発用ツール等）。

セットアップ手順
----------------

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があればそちらを使用）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）

   主要な環境変数（デフォルト／説明）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (紙トレード用 DB、デフォルト: data/paper_trading.db)
   - KABUSYS_ENV (development|paper_trading|live、デフォルト: development)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
   - KILL_FLAG_CLEAR_ON_START (0/1、デフォルト: 0。本番で自動クリアは危険)

   補足:
   - 自動 .env ロードはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DB 初期化
   - 実行スクリプトを起動すると必要なテーブルは init_monitoring_db により作成されます（冪等）。

使い方
------

起動スクリプト（主なもの）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db など）へ記録。実稼働 DB と分離。
    - 起動時に data/stop_requested.flag があれば起動せず終了。
    - プロセス優先度を "high" に設定。
    - 実行中に data/stop_requested.flag が作成されるとエンジンに対して停止指示が送られる。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを記録（環境に依存せず本番 sqlite_path を使用します）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - data/stop_requested.flag を検出すると監視ループを終了。

停止・Kill Switch
- ExecutionEngine を安全に停止したい場合、監視ロジックか管理者操作で data/kill.flag を書き込む（KillSwitch がこれを作成）。
- run_execution/run_monitoring を即時停止したい場合、data/stop_requested.flag を作成すればスクリプトが検出して終了します。

設定検証・ウィザード
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（.env と config/*.yaml の簡易チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code=1）

ツール
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先して使用）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ指標、PASS/FAIL 判定

AI 関連（OpenAI）
- ニュース NLP スコアリング:
  - プログラム経由で kabusys.ai.score_news(conn, target_date, api_key=None) を呼ぶ
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - 失敗時はフェイルセーフ（部分失敗は無視等）として設計されています
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトログディレクトリ: logs/
- ログファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテート、30日保持）
- 環境変数: LOG_DIR, LOG_LEVEL を使用して調整可能

重要ファイル・フラグ
- data/stop_requested.flag — run_* スクリプトが監視している停止フラグ（存在すれば監視ループ・エンジンを止める）
- data/kill.flag — Kill Switch が書き込むファイル。ExecutionEngine 停止を意図するクリティカルなフラグ
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution が使用）
- DuckDB / SQLite ファイル（デフォルト）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db（paper_trading 用）

開発・運用上の注意
-----------------
- 本番環境（KABUSYS_ENV=live）の場合は .env の設定を慎重に行ってください。validate_config は live 向けのガードを行います。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するとベアな Kill Switch が自動クリアされるため危険です（デフォルト 0 を推奨）。
- Monitoring は環境に関わらず本番 sqlite_path を使用するため、別 PATH を使いたい場合は SQLITE_PATH を変更してください。
- Paper Trading は production DB と完全分離されるように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しにはレート制限・ネットワーク障害を考慮したリトライ実装がありますが、API キーと課金・利用制限に注意してください。
- DuckDB 用の SQL はシステムのデータ量によっては時間がかかるため、分析時は適切なリソースを用意してください。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要なモジュール構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings 定義
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（ma200 + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度検知
    - trade_monitor.py       — （取引監視ロジック）※本 README のコード抜粋では省略
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み/管理
    - alert_manager.py       — アラート送信用ラッパ（LINE 等）※省略
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン

  - execution/
    - execution_engine.py    — ExecutionEngine（注文実行セッション管理）※省略
    - broker_factory.py      — BrokerClient の生成（Mock 対応）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - research/
    - factor_research.py     — momentum / value / volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
    - その他ユーティリティ群

補足: テスト・拡張
-----------------
- モジュールはユニットテストしやすい純粋関数（research / portfolio 等）と、DB・IO 周りを伴う部分に分かれています。OpenAI 呼び出しは _call_openai_api を patch してテスト可能です。
- DuckDB 接続を外部から渡すデザインのため、テスト時にメモリ DB/テスト用ファイルを用意して検証できます。
- 監視・実行の停止はフラグファイル（data/stop_requested.flag, data/kill.flag）で制御されるため、運用上は管理者に対する手動オペレーションや外部監視システムと連携可能です。

最後に
------
この README はコードベースから抽出した主要機能と運用上の注意点をまとめたものです。個別モジュール（ExecutionEngine、OrderManager、TradeMonitor、AlertManager など）の詳細な設計・使い方はそれぞれのソースファイル内コメント（docstring）を参照してください。必要があれば、各モジュールの詳細なドキュメントを追加で作成します。