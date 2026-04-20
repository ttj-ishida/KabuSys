KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買およびそれに付随する監視・研究・AIユーティリティ群を集めた Python パッケージです。  
本 README はコードベース（src/kabusys 以下）に基づいた概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

重要な前提
----------
- Python 3.10 以上を想定（型ヒントの | 演算子等を使用）。
- プロジェクトルート直下に data/ および logs/ を作成して利用します（スクリプトは自動作成することもありますが、権限に注意してください）。
- .env（環境変数）に機密情報を含むため、絶対に Git にコミットしないでください。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine（発注エンジン）: ブローカークライアントを介して発注を実行します。KABUSYS_ENV に応じて本番/ペーパー分離が行われます。
- Monitoring（監視）: システム稼働状況、発注ログ、リスク（ドローダウン・ポジション数）を定期ポーリングしてログ化・アラート発行・Kill Switch 制御を行います。
- Portfolio（ポートフォリオ構築）: 候補選定・重み付け・ポジションサイズ計算・セクターキャップ適用などの純粋関数群。
- Research（研究）: DuckDB を用いたファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）。
- AI モジュール: ニュースのセンチメント評価や市場レジーム判定（OpenAI API を利用）を行うモジュール。
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- Utilities: ロギング設定、プロセス優先度設定、設定読み込みなどの共通ユーティリティ。

主な機能一覧
-------------
- 環境設定ウィザード（.env 生成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env、config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
- Monitoring のポーリングループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- Kill Switch（data/kill.flag）で ExecutionEngine を停止できる仕組み
- Paper Trading 検証レポート生成スクリプト: python -m kabusys.tools.paper_verification_report
- DuckDB を使ったファクター計算（research モジュール）
- OpenAI を用いたニュース NLP（ai.news_nlp.score_news）および市場レジーム判定（ai.regime_detector.score_regime）

セットアップ手順
----------------

1. リポジトリをクローン、プロジェクトルートへ移動
   - git clone ...
   - cd <project-root>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 推奨パッケージ（例）
     - duckdb
     - psutil
     - openai
     - pyyaml (config の詳細検証に任意)
   - 例:
     - pip install duckdb psutil openai PyYAML

   （注）requirements.txt はこのリポジトリに含まれていない場合があります。実行する機能に応じて上記パッケージを追加してください。

4. 初期設定（.env）作成
   - ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）:
     - .env には API キーやパスワード等を設定。絶対にコミットしないこと。

5. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

6. データベースファイル（必要に応じて）
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH で変更可能

使い方（主要コマンド例）
-----------------------

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（バックグラウンド管理は別途）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - development: 発注なし（テスト用）
    - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録
    - live: 実際のブローカーに接続（注意!!）

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL に秒数を指定してポーリング間隔を変更可能（デフォルト 60）

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH がない場合）

- AI モジュールの利用（プログラムから呼び出し）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数に api_key 引数を渡す
  - 例（Python REPL 等）:
    - from openai import OpenAI
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

主要環境変数一覧（抜粋）
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（一般的）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB の SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで利用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）
- MONITOR_POLL_INTERVAL — run_monitoring で使用するポーリング間隔（秒）
- LOG_DIR — ログ出力先（デフォルト logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag ファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値（%）

（詳細は kabusys.config.Settings のプロパティを参照してください。）

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）へ出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging にて統一制御されます。

監視 / Kill Switch の仕組み
--------------------------
- Monitoring は system_status / trade_logs / risk_logs / positions / dashboard 等を SQLite に永続化します（監視用 DB）。
- RiskMonitor によってドローダウンやポジション上限が検出されると risk_logs に記録し、KillSwitch が条件に合致すれば data/kill.flag を書き込んで ExecutionEngine に停止要求を出します。
- ExecutionEngine 側は起動時および実行ループ中に stop フラグ（data/stop_requested.flag）や kill.flag を監視して安全に停止します。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 下の主要なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注関連（broker, engine, order_manager 等）
    - (各モジュール: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 発注ログ監視（滞留/約定異常等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 複数 monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信の抽象）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 数量計算・集約キャップ
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py     — レジーム判定（ma200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

備考 / 運用上の注意
-------------------
- 本番環境（KABUSYS_ENV=live）で実行する際は設定（API キー、LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を慎重に確認してください。validate_config は live 用の追加警告も行います。
- .env に誤ったプレースホルダ（your_value など）を残すと validate_config が警告を出します。
- OpenAI を使うモジュールは API コール（料金）・応答失敗の扱い（リトライ・フォールバック）に注意していますが、運用時はレート制限等を考慮してください。
- DB のマイグレーションは monitoring_db.init_monitoring_db にて簡易的な列追加を行っています。手動での移行が必要なケースもあります。

開発者向けメモ
---------------
- 各モジュールはできるだけ副作用を避ける設計（DuckDB/SQLite 接続を呼び出し元で渡す等）になっています。
- テストや CI で .env の自動ロードを禁止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（kabusys.config が .env を自動ロードする機能を搭載しています）。
- ログは stdout に出力するため、cron / systemd / コンテナのログ収集と親和性が高いです。

ライセンス / 貢献
-----------------
- 本 README はコードから自動生成した説明です。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください（該当ファイルがない場合はリポジトリ所有者に問い合わせてください）。

以上。必要であれば README を README.md 形式のファイルに整形してコミットする内容を作成します（英語版やさらに詳細な運用手順も作成可能）。