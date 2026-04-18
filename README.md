KabuSys
======

日本株向け自動売買システムのコアライブラリ群（KabuSys）。  
このリポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

概要
----
KabuSys は以下を目的に設計されたモジュール群です。

- 戦略に基づく銘柄選定・配分（portfolio）
- 注文管理・リスク管理・発注エンジン（execution）
- システム/注文/リスクの常時監視（monitoring）
- DuckDB を用いたデータ解析・ファクター計算（research）
- OpenAI を用いたニュースセンチメント評価・レジーム判定（ai）
- 運用支援ツール（設定ウィザード / 設定検証 / 検証レポート など）

主な機能
--------
- ExecutionEngine：Broker クライアント経由の注文実行・注文管理・リスク制御
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading DB（data/paper_trading.db）へ完全分離して記録
- Monitoring：System / Trade / Risk を定期ポーリングしてログ・アラート・Kill Switch を管理
  - 監視ログは SQLite（data/monitoring.db）に永続化（monitoring は常に本番 sqlite_path を使用）
- Portfolio construction：候補選定、重み計算、ポジションサイズ算出、セクター上限・レジーム乗数
- Research：DuckDB 接続を受けてファクター計算（モメンタム／ボラティリティ／バリュー等）や特徴量解析
- AI：
  - news_nlp：ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存
  - regime_detector：ETF（1321）MA200 とマクロニュースセンチメントから市場レジーム判定
- ツール：
  - config_setup：.env 初期化ウィザード（対話式）
  - validate_config：.env / config/*.yaml の事前検証 CLI
  - paper_verification_report：Paper Trading の検証レポート生成

前提 / 依存
------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意（YAML 検証を行う場合）
  - PyYAML

（環境に合わせて requirements.txt を作成してください。リポジトリにない場合は pip install で個別に入れてください。）

セットアップ手順
--------------
1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて）pip install pyyaml
4. ディレクトリ作成（data, logs 等）
   - mkdir -p data logs
5. 環境変数の設定
   - 推奨：対話式ウィザードで .env を作成する（下記参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OPENAI_API_KEY は AI 機能を使う場合に必要
   - DB のデフォルト：
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db（paper_trading 実行時）
   - 実行環境:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

.env の作成（推奨）
-----------------
対話式で .env を生成するには：

- python -m kabusys.config_setup

ウィザードは既存 .env の読み込み・編集をサポートします。生成後、下記コマンドで設定を検証してください。

- python -m kabusys.validate_config
- 警告を厳密に扱いたい場合: python -m kabusys.validate_config --strict

使い方
------

一般的な実行コマンド（パッケージルートが PYTHONPATH にある前提）:

- ExecutionEngine 起動（実行エンジン）
  - python -m kabusys.run_execution
  - 動作:
    - 起動時にプロセス優先度を "high" に設定
    - KABUSYS_ENV=paper_trading の場合は paper_trading DB を使用し MockBroker を利用
    - data/stop_requested.flag が存在すると起動を中止／停止
    - PID ファイル: data/execution.pid（デフォルト）

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を "high" に設定
    - monitoring は環境にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
    - 監視ループ停止用フラグ: data/stop_requested.flag（存在するとループ終了）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

主要環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で取得可能（デフォルトは data 以下）

停止 / Kill Switch
------------------
- run_execution / run_monitoring は data/stop_requested.flag をチェックして安全に停止します（手動でフラグ作成すると停止処理を促せます）。
- KillSwitch（monitoring 側）は状況に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側で kill.flag のチェックを行い停止する挙動になっています）。
- 実運用では kill フラグの取り扱いは慎重に（KABUSYS_ENV=live では KILL_FLAG_CLEAR_ON_START=1 は危険、と validate で警告されます）。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- デフォルト出力:
  - コンソール（stdout）
  - ローテートファイル: logs/<app_name>.log（1日単位、バックアップ 30 日）
- LOG_LEVEL は .env の LOG_LEVEL または引数で決定

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下をルートとした構成）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - execution/                — 発注エンジン関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 注文/約定監視（滞留・異常価格検出等）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書込ユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるループ
    - alert_manager.py        — （アラート送信管理; LINE 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・資金配分・lot 切り上げ
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）で銘柄スコア化
    - regime_detector.py      — 市場レジーム判定（ETF MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - data/                     — 実行時 DB / フラグ / pid 等を配置（プロジェクトルートに作成）

実装上の注記 / 運用上の注意
--------------------------
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング（デフォルト 60 秒）。異常な小値は無効化されデフォルトにフォールバックします。
- monitoring は「監視用 DB（SQLite）」を初期化しますが、監視は常に sqlite_path（本番パス）を使用します。つまり paper_trading 環境でも監視 DB は本番設定の sqlite_path に保持されます（設計による挙動）。
- ExecutionEngine は paper_trading モードのとき paper_sqlite_path（data/paper_trading.db）を使用します。paper_trading のログは本番 DB と分離されます。
- AI（news_nlp / regime_detector）は OpenAI の API を呼び出します。OPENAI_API_KEY の管理、レートリミットやエラー時の処理（リトライ・フォールバック）が組み込まれていますが、API コストと呼び出し頻度に注意してください。
- .env を絶対に git にコミットしないでください（README にも記述されていますがウィザードも警告を出します）。
- DuckDB / SQLite に対するスキーマ変更やマイグレーションは各モジュール内に安全性を考慮した処理（ALTER TABLE の追加、冪等 init など）が含まれていますが、本番運用前にバックアップを推奨します。

よく使うコマンドまとめ
--------------------
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張
----------------
- DuckDB を使った分析クエリやファクター計算は research 以下で提供されています。研究用途やバックテストに活用してください。
- BrokerClient の実装を切り替えることで、実際の発注先（kabuステーション等）とモックを切り替えられます（BrokerClientFactory を参照）。
- logging_setup, process_priority などのユーティリティは他モジュールから再利用可能です。

ライセンス・バージョン
--------------------
- バージョン: __version__ = "0.1.0"（kabusys.__init__ より）
- ライセンス情報は本リポジトリのルートに置かれた LICENSE を参照してください（存在しない場合はプロジェクト所有者に問い合わせてください）。

補足
----
README に記載の挙動はソースコードを基にまとめています。実際の運用前に python -m kabusys.validate_config によるチェック、テスト環境での動作確認を必ず行ってください。必要があれば各モジュールの docstring を参照して詳細を確認してください。