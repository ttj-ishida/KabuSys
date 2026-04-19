KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を目的とした軽量なフレームワークです。  
主な役割は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム状態・注文状況・リスク指標を定期監視し、Kill Switch（停止フラグ）を発動
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算などポートフォリオ構築ロジック
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：OpenAI を利用したニュースセンチメント評価・市場レジーム判定
- Tools：検証レポート生成や設定ウィザードなどのユーティリティ

主な機能
--------
- 実行環境（KABUSYS_ENV）に応じた動作（development / paper_trading / live）
  - paper_trading：MockBroker を用いてデータは data/paper_trading.db に分離
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス存続・データ鮮度の定期ロギング
  - RiskMonitor によるドローダウン・ポジション数監視
  - Kill Switch（data/kill.flag）を書き込むことで安全に ExecutionEngine を停止
- ポートフォリオ構築（選定・重み付け・リスク調整・株数算出）
- 研究モジュール（DuckDB を想定したファクター計算、Forward return、IC 等）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコアの取得）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 設定ウィザード（.env 生成補助）と設定検証 CLI
- Paper Trading 検証レポート出力（注文成功率、レイテンシ、稼働率など）

前提 / 必要環境
---------------
- Python 3.10+（ソース内の型注釈・構文により）
- 必要なパッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config 検証で YAML をパースする場合）
- SQLite（標準ライブラリに同梱）
- ネットワーク接続（OpenAI を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動します。
2. 仮想環境を作成・有効化し、依存をインストールします（requirements.txt がある場合はそれを使用）。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai
     - （必要に応じて）pip install pyyaml
3. データ・ログ用ディレクトリを作成します（通常はアプリケーションが作成しますが、手動でも可）:
   - mkdir -p data logs
4. .env を作成します（推奨: 対話式ウィザードを利用）:
   - python -m kabusys.config_setup
   - あるいは .env.example をコピーして手動編集
5. 設定を検証します:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

主要な環境変数（抜粋）
--------------------
設定は .env または環境変数で行います。主なキーとデフォルト：

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- 実行モード
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- データベース
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB。デフォルト: data/paper_trading.db
  - PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject
- ログ / 監視
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — デフォルト: logs/
  - PID_FILE_PATH — 実行エンジンの pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効）
- OpenAI
  - OPENAI_API_KEY — News NLP / Regime Detector で使用
- Monitoring 特有
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）。デフォルト 60

使い方（コマンド例）
-------------------

- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗にする）： python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - paper_trading の場合、MockBroker を使い data/paper_trading.db に記録されます（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします
    - 実行中に data/stop_requested.flag を作成すると正常停止をトリガーします

- Monitoring を起動（ポーリングで各種監視を実行）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 既定は 60 秒。監視は環境に関わらず本番 sqlite_path を使用して監視ログを記録します
  - 監視ループは data/stop_requested.flag の存在で停止します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止 / Kill Switch / フラグ
--------------------------
- stop_requested.flag（data/stop_requested.flag）
  - run_execution/run_monitoring のループを外部から停止させたい場合にこのフラグファイルを作成してください。
- kill.flag（Settings.kill_flag_path（デフォルト data/kill.flag））
  - Monitoring の KillSwitch が検出条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch.clear() を使ってプログラムからこのフラグを消去できます（起動時の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効化する設定が提供されています）。

ロギング
-------
- 共通のログ設定ユーティリティが用意されています（kabusys.utils.logging_setup.setup_logging）。
- デフォルトでコンソール（stdout）と日次ローテートするファイルハンドラ（logs/<app_name>.log）を設定します。
- ログレベルは LOG_LEVEL 環境変数で制御できます。

モジュール / API の概要
---------------------
（実行可能スクリプト以外の主なモジュール）
- kabusys.config — 環境変数読み込み・Settings クラス
- kabusys.portfolio — 銘柄選定・重み付・リスク調整・株数決定（純粋関数群）
- kabusys.research — ファクター計算・特徴量探索（DuckDB 接続で実行）
- kabusys.ai.news_nlp — ニュースセンチメントの取得（OpenAI）
- kabusys.ai.regime_detector — 市場レジーム判定（MA + マクロセンチメントの合成）
- kabusys.monitoring — 監視コンポーネント群（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine）
- kabusys.utils — ログ設定、プロセス優先度 / CPU affinity ユーティリティ など

ディレクトリ構成（主要ファイル）
------------------------------
下記はソース内の主要な構成です（src/kabusys 以下を想定）。

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/           # ExecutionEngine 周辺（OrderManager 等） — 実行ロジック
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                # 実行時に生成される想定のディレクトリ（DB, フラグ, pid など）
  - logs/                # ログ出力先（デフォルト）

開発・運用上の注意
-----------------
- 本番（KABUSYS_ENV=live）では設定（APIキーや kill フラグ動作）を慎重に確認してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup にもその旨の注意文があります）。
- Monitoring は監視 DB（SQLITE_PATH）に書き込みます。監視は環境に関係なく本番の sqlite_path を使用するため、開発時に監視 DB を分離したい場合は SQLITE_PATH を変更してください。
- paper_trading モードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

よくある操作例
--------------
- デーモンっぽくバックグラウンドで起動（簡易例）:
  - nohup env KABUSYS_ENV=live python -m kabusys.run_execution > logs/execution.stdout 2>&1 &
  - nohup python -m kabusys.run_monitoring > logs/monitoring.stdout 2>&1 &

ライセンス / 貢献
----------------
- 本 README にはライセンス情報を含めていません。実際のリポジトリでは LICENSE を追加してください。  
- コントリビュートは PR と Issue を通じて受け付けてください（実運用ルール・テスト・CI を整備することを推奨します）。

最後に
------
この README はソースコードからの主要な使い方や設計上のポイントをまとめたものです。  
実際の運用前に python -m kabusys.validate_config で設定を検証し、ログ・データの保存先や API キーの管理ポリシーを十分に確認してください。