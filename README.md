KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークの一部実装です。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine（発注エンジン）と Monitoring（監視）を起動するランチャースクリプト
- 環境変数のウィザード / 検証ツール (.env の生成・検証)
- ペーパートレーディング用の分離ストレージと検証レポートツール
- ポートフォリオ構築・サイズ計算・リスク調整の純粋関数群
- 研究用モジュール（ファクター計算、特徴量解析）
- ニュースの NLP（OpenAI を用いたセンチメント）やレジーム判定
- 監視・アラート・Kill Switch ロジック、および永続化（SQLite）層
- ロギング / プロセス優先度 / ユーティリティ群

特徴一覧
--------
- 実行環境分離: KABUSYS_ENV によって development / paper_trading / live を切替。paper_trading は本番 DB と分離した専用 SQLite を利用。
- フェイルセーフ: API 呼び出しや DB 書込での失敗は基本的に局所的にハンドリング（部分失敗回避）
- モジュール化: ポートフォリオ構築・ポジションサイジング・リスク調整は純粋関数でテスト容易
- ニュース NLP / レジーム判定: OpenAI を用いたセンチメント評価（バッチ・リトライ・バリデーション付き）
- 監視: system / trade / risk の監視ロジック、Kill Switch による停止シグナル発出
- ロギング: stdout と日次ローテートファイル（logs/*.log）を統一的に設定

前提・依存
-----------
- Python 3.10 以上（型アノテーションに | を使用）
- 推奨パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリで利用）
- インターネット接続（OpenAI API を使う場合）

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai
     - （config 検証で YAML を使うなら pip install pyyaml）

   ※requirements.txt がある場合は pip install -r requirements.txt を使用。

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します。必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV の候補: development / paper_trading / live

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたければ --strict を付ける

6. ディレクトリ（data, logs）は自動作成されますが、権限やパスが問題であれば手動で作成してください：
   - data/ (デフォルト DB・フラグファイル保存)
   - logs/ (ログ出力)

主要環境変数（主なもの）
-----------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

使い方（ランスクリプト / CLI）
-------------------------------

- 環境ウィザード（.env生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が利用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - プロセスは data/execution.pid に PID を書き込みます。
  - 停止方法:
    - 監視プロセスや手動から data/stop_requested.flag を作成すると安全停止シーケンスが始まります。
    - KillSwitch が発動すると data/kill.flag が書き込まれます（Execution は起動時に KILL_FLAG_CLEAR_ON_START の設定次第でクリアする可能性があります）。

- 監視ループ起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング周期を変更可（秒、デフォルト 60）
  - 監視は常に本番 sqlite_path を参照して監視ログを記録します（環境にかかわらず）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db
  - 指標: 稼働率・注文成功率・送信率・P95 レイテンシなど。閾値を下回ると FAIL。

- AI / 研究系（ライブラリ関数利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究モジュール: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic など
  - DuckDB 接続を渡して使用します（duckdb.connect(path)）

ログ
----
- ログは stdout に出力されるほか、logs/<app_name>.log に日次ローテートで保存されます（30 日分保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一的に行っています。

停止・フラグファイル
-------------------
- stop_requested.flag: run_execution / run_monitoring の外部停止トリガ（data/stop_requested.flag）
- kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止指示を与える目的）
- PID ファイル: data/execution.pid（ExecutionEngine が起動時に書き込む）

データベース（既定）
-------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db

注意事項 / 運用メモ
------------------
- KABUSYS_ENV=live を使う場合は .env の設定、特に API キー類や通知設定（LINE）を慎重に確認してください。validate_config は live 時に追加チェックを行います。
- OpenAI を利用する機能は API キーの管理と利用料に注意してください。API エラー時はフェイルセーフ（多くの箇所で 0.0 やスキップ）にフォールバックします。
- ローカルでテストする際は KABUSYS_ENV=paper_trading を使うと本番 DB と分離されます。
- Windows と POSIX (Linux/macOS) のプロセス優先度設定をラップしているため、権限により優先度変更が失敗することがあります（警告ログが出ます）。

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 生成ウィザード
- validate_config.py       — 起動前チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- execution/                — （発注関連コンポーネント: broker_factory, execution_engine, order_manager, ...）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
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

（補足）主なファイルの説明
- config.py: 自動で .env を読み込むロジック、Settings クラス（env 判定・各種パス・閾値設定）
- run_execution.py: Broker の生成、OrderRepository / RiskManager / ExecutionEngine の組み立てと起動ループ
- run_monitoring.py: SystemMonitor を中心に SQLite/duckdb 接続を用いてポーリング監視を実施
- monitoring_db.py: system_status / trade_logs / positions / risk_logs / dashboard テーブルを作成・操作する永続化層
- news_nlp.py / regime_detector.py: OpenAI を使用したニュースセンチメント・レジーム判定

付録: よく使うコマンド例
-----------------------
- .env を作る:
  - python -m kabusys.config_setup

- 設定を検証する:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- エンジンを起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレードレポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はリポジトリ内のモジュール実装（docstring とコード）を基に作成しています。機能詳細や運用手順は開発方針や運用ポリシーに合わせて適宜更新してください。質問や補足の要望があればお知らせください。