README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの一部実装です。本リポジトリは以下を含みます。

- ExecutionEngine（発注エンジン）を起動するスクリプトと関連コンポーネント
- Monitoring（稼働監視 / Kill Switch / アラート）コンポーネント
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量解析
- ニュース NLP（OpenAI を使ったセンチメント評価）と市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証ツール）
- Paper Trading 検証レポート生成ツール

本コードはプロダクションを想定した設計（設定の冪等性、フェイルセーフ、DB マイグレーション処理、ログローテーション等）を一部備えています。

主な機能
--------
- ExecutionEngine の起動（src/kabusys/run_execution.py）
  - KABUSYS_ENV に応じて本番 / ペーパートレードを切り替え
  - paper_trading モードでは MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）へ記録
  - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した制御
- Monitoring（src/kabusys/run_monitoring.py, monitoring/*）
  - システムリソース監視（CPU/メモリ/ディスク）
  - Execution 停止検出、データ鮮度チェック、取引ログ監視、リスク監視（ドローダウン / ポジション上限）
  - Kill Switch による停止信号書き込み（data/kill.flag）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重／スコア依存の重み計算、セクター上限適用、レジーム乗数、株数決定（単元丸め、aggregate cap）
- 研究モジュール（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- ニュース NLP / レジーム判定（kabusys.ai）
  - raw_news テーブルを集約して OpenAI による銘柄別センチメント評価（ai_scores に保存）
  - マクロニュースと ETF（1321）の MA200 を組み合わせた日次レジーム判定（market_regime へ保存）
  - OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を備える
- ユーティリティ
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ログ設定ユーティリティ（統一的なコンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

依存関係（主要）
----------------
- Python 3.9+（アノテーション from __future__ を使用）
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

インストール例（推奨）
--------------------
1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

設定方法
--------
1. .env の作成（推奨: 対話ウィザードを使用）
   - python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development/paper_trading/live）等を設定します。
   - 自動読み込み:
     - Settings はプロジェクトルートの .env および .env.local を自動でロードします（OS 環境変数が優先）。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

2. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗として扱う場合: python -m kabusys.validate_config --strict

主な環境変数（代表）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（ニュース / レジームスコアリング用）
- LOG_LEVEL（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、run_monitoring 用）
- PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）

使い方（起動例）
----------------
- ExecutionEngine を起動（デフォルト: env に従う）
  - python -m kabusys.run_execution
  - ペーパートレードで起動するには .env で KABUSYS_ENV=paper_trading に設定

- Monitoring を起動（ポーリングループ、停止は Ctrl+C または data/stop_requested.flag を作成）
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: --db /path/to/data/paper_trading.db

- .env の初期化 / 編集
  - python -m kabusys.config_setup

停止・キルスイッチ
------------------
- 実行中のエンジンを外部から停止するには data/kill.flag を書き込む（KillSwitch が検出して停止指示を出します）。
- run_execution/run_monitoring は data/stop_requested.flag により外部から監視ループ・エンジン起動を制御します。
- run_execution は起動時に data/execution.pid を利用してプロセス管理を行います。

ログ
----
- ログはデフォルトで logs/ に日次ローテーションで出力されます（各アプリケーション名に合わせたログファイル）。
- コンソール出力は stdout に出力されます（cron 等でのリダイレクト運用を想定）。

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトルート（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings クラス（.env 自動ロード）
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py       — SQLite 用永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （取引監視、コードベース参照）
      - risk_monitor.py        — ドローダウン・ポジション監視
      - kill_switch.py         — Kill Switch 実装（flag ファイル）
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - alert_manager.py       — （アラート送信管理、コード参照）
    - execution/                — 発注・リスク管理・リポジトリ等（Engine, OrderManager, BrokerFactory 等）
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 株数決定・スケーリング
      - risk_adjustment.py     — セクター制限・レジーム乗数
    - research/
      - factor_research.py     — Momentum/Value/Volatility 等の計算（DuckDB）
      - feature_exploration.py — 将来リターン / IC / 統計
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し）
      - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート生成
- config/
  - *.yaml                     — 設定テンプレート（system_config.yaml 等）
- data/
  - monitoring.db / paper_trading.db / kill.flag / stop_requested.flag / execution.pid など
- logs/
  - *.log                      — ログ出力先（デフォルト）

注意事項 / 運用のヒント
-----------------------
- .env は絶対に Git にコミットしないでください。
- 本番運用時（KABUSYS_ENV=live）は特に KILL_FLAG_CLEAR_ON_START を 0 にするなど設定を慎重に行ってください。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キーと料金発生を伴います。テスト時は環境変数 OPENAI_API_KEY を設定するか、該当機能を無効化してください。
- DuckDB/SQLite のパスは Settings で指定できます。paper_trading モードでは paper_sqlite_path が使用され、本番 DB と分離されます。
- Monitoring は本番 sqlite_path を使用して監視ログを記録します（run_monitoring の設定参照）。

貢献 / 拡張案
--------------
- stocks マスタの追加（銘柄別 lot_size 等）
- 戻り値を Pandas で扱うためのラッパー（研究モジュールの高速化）
- アラート送信先（LINE / Slack）プラグインの拡充
- unit テストと CI（特に AI モジュールは外部 API をモックするテスト整備）

お問い合わせ
------------
実装方針や各モジュールの詳細はコード内 docstring およびコメントに記載しています。特定の使い方や拡張方法についての質問があればお知らせください。