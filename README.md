README
======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
バックエンドは主にローカルファイルベースのデータストア（SQLite / DuckDB）を使用し、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リスク制御、研究用ファクター計算、及びニュースを用いた AI スコアリング等の機能を備えています。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（Mock 実装でペーパートレードを完全分離）
  - リスクマネジメント（ポジション上限・ドローダウン等）
- Monitoring（監視）
  - システム状態（CPU／メモリ／ディスク、プロセス生存）
  - 注文滞留・約定異常の検出
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）
  - 永続化：SQLite（monitoring.db）
- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定、等金額／スコア加重、リスクベース配分
  - セクター制約・レジーム乗数の適用
- Research（DuckDB を使ったファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value 等のファクター
  - 将来リターン、IC、統計サマリー
- AI（OpenAI 経由のニュース NLP）
  - ニュース記事をバッチで LLM に送信し銘柄別センチメントを ai_scores に保存
  - 市場レジーム判定（MA200 とマクロニュースの LLM 評価の合成）
- 各種ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

事前準備（セットアップ）
-----------------------
※ 以下は一般的な手順です。プロジェクト配布状況や依存ファイルによって調整してください。

1. Python
   - 推奨: Python 3.10+（ソースは型注釈で最新構文を利用しています）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config ファイル検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ SQLite は標準ライブラリ sqlite3 を使用します。

4. .env の初期作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を配置する（.env.example を参照して作成してください）。
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH （ペーパートレード DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE （instant / partial / never / reject、デフォルト: instant）
     - OPENAI_API_KEY （AI 機能を利用する場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知、任意）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか：0/1、デフォルト: 0）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

よく使う実行コマンド（使い方）
----------------------------

- ExecutionEngine を起動（本番／ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込むため本番 DB と完全分離されます。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルが送られます。
    - 実行時に pid ファイル（デフォルト: data/execution.pid）が作られ、Monitoring がプロセス生存を検知します。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を監視用 DB として使用します（監視ログは単一 monitoring.db に集約）。
    - 停止制御: プロジェクトルート/data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能（デフォルト: data/paper_trading.db）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

停止・Kill Switch
----------------
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine を停止させます（Execution 側は定期的に kill.flag を確認する実装を期待しています）。
  - KillSwitch.clear() で削除可能。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

- stop_requested.flag
  - run_monitoring / run_execution の起動ループは data/stop_requested.flag の存在を監視し、存在するとループを安全に終了します（外部からの即時停止用）。

設定（主なデフォルト値）
---------------------
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 60（秒、環境変数で変更可）
- PAPER_FILL_MODE: instant（"instant"|"partial"|"never"|"reject"）

依存関係
--------
- duckdb
- psutil
- openai（AI 機能）
- pyyaml（config ファイルチェック時に任意）
- Python 標準ライブラリ: sqlite3, logging, threading, datetime, os, etc.

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / .env 読み込み、Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（メインエントリ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/MEM/DISK・データ鮮度・プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch の実装（flag ファイル書き込み）
    - monitoring_engine.py — 各 Monitor を束ねてポーリング
    - alert_manager.py — （アラート送信管理。未掲示の詳細実装）
  - execution/  (発注関連の実装; OrderRepository/OrderManager/Engine など)
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算 / 投下資金スケールダウン
    - risk_adjustment.py — セクター上限 / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - ai/
    - news_nlp.py — ニュース記事 NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

設計上の注意点 / 運用メモ
-----------------------
- Monitoring は KABUSYS_ENV に関係なく「本番」用の monitoring DB（SQLITE_PATH）を参照します。監視ログを分離したい場合は別途設定を変更してください。
- Execution は KABUSYS_ENV=paper_trading のとき専用の paper_sqlite_path に書き込むため、本番 DB と分離されます。
- AI 機能を利用する際は OPENAI_API_KEY を必ず設定してください。API エラーは再試行・フェイルセーフが組み込まれていますが、料金とレート制限に注意してください。
- .env ファイルは絶対にバージョン管理にコミットしないでください（config_setup でも注意書きあり）。
- プロセス優先度の設定や CPU affinity はプラットフォーム差（Windows/Linux/Mac）を吸収する実装ですが、権限や OS の制約で設定できない場合があります（警告ログのみ）。

貢献・拡張ポイント（参考）
--------------------------
- AlertManager の送信先（LINE など）拡張／実装
- Broker クライアントの具体的な実装（kabuステーション API ラッパー）
- 単元株数を銘柄ごとに扱う拡張（position_sizing）
- テストカバレッジの強化（特に AI 呼び出しのモック）
- 監視アラート閾値の動的設定（config yaml からの読み込み）

ライセンス
----------
プロジェクトに付与されているライセンスファイルに従ってください（ここには含めていません）。

補足
----
- ここに記載したコマンドはパッケージがインストール済み、または ソースルート で pythonpath が通っていることを前提としています。パッケージ化されていない場合は python -m を使うか、PYTHONPATH を調整して実行してください。
- 実行前に必ず python -m kabusys.validate_config で設定の健全性を確認してください。

以上。必要であれば README にサンプル .env テンプレートや運用フロー（起動順序、監視→発注の相互作用）を追記します。どの情報を詳しく載せたいか教えてください。