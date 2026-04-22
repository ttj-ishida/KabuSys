KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買 / 研究 / 監視ツール群をまとめた Python パッケージです。
主要な機能は戦略のファクター計算・ポートフォリオ構築、ExecutionEngine（発注実行）、
Monitoring（監視・Kill Switch）、AI を使ったニュース評価などです。

プロジェクト概要
----------------
- 名前: KabuSys
- 目的: 日本株自動売買に必要な執行ロジック、監視、分析、AI スコアリングを提供する。
- 設計方針:
  - 実行コードと研究用コードを同一パッケージ内で分離。
  - 設定は .env / 環境変数で管理。config_setup による対話型ウィザードを提供。
  - Execution と Monitoring はプロセス優先度や PID / フラグファイルによる停止制御を備える。
  - DuckDB と SQLite をデータ保存に使用。Paper Trading は本番 DB と完全に分離可能。

主な機能一覧
-------------
- Execution（実行）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注・リスク管理）
  - paper_trading モードで MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
- Monitoring（監視）
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス死活）
  - TradeMonitor（注文滞留／約定異常などの検出）
  - RiskMonitor（ドローダウン／ポジション上限の監視）
  - KillSwitch（条件を満たすと data/kill.flag を書き込み停止をトリガー）
  - MonitoringEngine によるポーリング実行
- 研究・データ処理
  - research モジュール（ファクター計算、IC 計算、特徴量探索）
  - portfolio モジュール（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- AI（OpenAI を用いたニュース NLP）
  - news_nlp.score_news: raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定
- ツール
  - config_setup: .env を対話的に生成/更新するウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: ペーパートレード検証レポート生成

前提（必須 / 推奨）
------------------
- Python 3.10+（typing の `X | Y` を使用しているため）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の詳細検証用。なくても動作するが警告が出る）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI API を使う場合）

セットアップ手順
----------------

1. リポジトリを取得
   - git clone … で取得して作業ディレクトリに移動。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt を用意している場合:
     - pip install -r requirements.txt
   - 代表的なパッケージを個別にインストールするには:
     - pip install duckdb psutil openai PyYAML

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークンや KabuStation パスワード、DB パス等を設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告も fail 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトの DB 等は data/ 以下を想定しています（例: data/kabusys.duckdb, data/monitoring.db）。
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を指定してください。

重要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要（任意 / デフォルトあり）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（デフォルト）
  - OPENAI_API_KEY: OpenAI を使う場合必須
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになる

- ExecutionEngine（実行プロセス）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）に分離して記録
    - PID ファイル: data/execution.pid（デフォルト）
    - 停止は data/stop_requested.flag を作成（monitoring や外部スクリプトが書き込む想定）

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - デフォルトは 60 秒間隔でポーリング（環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB は常に同じ場所で運用する想定）
    - 停止は top-level の data/stop_requested.flag によりループ終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db。--db で別指定可。

- AI スコアリング（プログラムから利用）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB の接続オブジェクトと target_date を受け取ります。
  - 例（スクリプト内で）:
    - import duckdb
    - from datetime import date
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026,4,1), api_key="sk-...")  # または環境変数 OPENAI_API_KEY を使用

停止・Kill Switch
-----------------
- 手動停止フラグ:
  - data/stop_requested.flag : run_execution / run_monitoring がこのファイルを検出するとプロセスを終了します（run_execution はスレッドの停止トリガ、run_monitoring はループ終了）。
- Kill Switch:
  - KillSwitch はリスク条件（ドローダウンやポジション上限）に応じて data/kill.flag を書き、ExecutionEngine に停止を促します。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動で kill.flag をクリアします（本番環境では 0 を推奨）。

ログ
---
- 共通ロギング設定: kabusys.utils.logging_setup.setup_logging を使用
  - 標準出力（stdout）と日次ローテートファイル出力（logs/<app_name>.log）
  - デフォルトログディレクトリ: logs/
  - LOG_LEVEL 環境変数で出力レベルを調整

ディレクトリ構成（抜粋）
-----------------------
（src/kabusys 以下の主要モジュールを中心に記載）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - research/
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite のテーブル初期化と永続化 API
    - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
    - trade_monitor.py       — （注文関連の監視）※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み管理
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
  - execution/               — Execution 周りの実装（OrderManager 等）
  - data/                    — データ関連（pipeline、stats 等）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

補足と運用上の注意
------------------
- 本番（KABUSYS_ENV=live）では .env の内容、LINE 通知設定、Kill Switch の設定等を慎重に確認してください。validate_config にて live 固有の警告を出します。
- Paper Trading モードは本番 DB と分離するため、テストや検証を安全に行えます（PAPER_TRADING_SQLITE_PATH をご確認ください）。
- OpenAI を用いる機能は API 呼び出しの失敗時にフォールバックする設計ですが、API キーやコストは適切に管理してください。
- ログや DB ファイルの保存先（デフォルト data/, logs/）は運用環境に合わせて .env で上書き可能です。

貢献・拡張
----------
- 新しい指標・戦略を research/*.py に追加し、portfolio モジュールと連携してください。
- 外部ブローカーの統合は execution/broker_factory.py を拡張してください。
- テストはユニットテストでローカル DB を用いた検証を推奨します。AI 呼び出し部分はモック化してテスト可能です（既に _call_openai_api の差し替えがしやすい設計になっています）。

ライセンスやその他メタ情報はリポジトリのトップレベルファイル（LICENSE 等）を参照してください。

以上。セットアップや実行で不明点があれば実行環境（OS、Python バージョン、インストール手順、出たエラーメッセージ）を教えてください。