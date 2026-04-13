# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行／監視ツール群）。

本リポジトリはトレード実行エンジン、監視（Monitoring）機能、ポートフォリオ構築、リサーチ／ファクター計算、AI を用いたニュース NLP / レジーム判定など、実運用を想定した機能群を含みます。

---

## プロジェクト概要

- 目的: 日本株の自動売買を行うためのエンジンと、それを安全に運用するための監視・検証ツールを提供する。
- 設計方針:
  - 実行ロジックと DB（SQLite / DuckDB）・ブローカーを分離。
  - Paper Trading（疑似環境）を本番 DB から分離して検証可能。
  - 外部モデル（OpenAI 等）利用時はフェイルセーフ処理（リトライ／フォールバック）を実装。
  - 主要コンポーネントは純粋関数化または小さな責務に分割。

---

## 主な機能一覧

- Execution（発注）
  - OrderManager / ExecutionEngine による注文生成・送信・同期
  - Reconciler による起動時の自動復旧（ブローカーとの照合）
  - RiskManager による注文前チェック（設定に基づく制約）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留、約定価格の異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視と alert / kill flag 書き込み
  - MonitoringEngine: 上記モニタをまとめてポーリングしアラート送出
  - Streamlit ダッシュボード（リアルタイム監視 UI）
- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア順、上位 N）
  - 重み計算（等比重、スコア加重）
  - ポジションサイズ計算（リスクベース・割当方式・単元丸め）
  - セクター集中制限、レジーム乗数
- Research（リサーチ）
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリ
- AI（OpenAI を利用）
  - news_nlp: ニュース記事の銘柄ごとセンチメントスコア化（ai_scores へ書込）
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - 環境設定読み込み（.env 自動ロード、Settings）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 向けレポート生成スクリプト（paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+ を推奨（コードが type hint 等を利用）
- 基本的に UNIX 系 / Windows のどちらでも動作するが、一部 OS 固有差分あり（プロセス優先度等）

1. リポジトリをクローン、ルートで仮想環境を作成／有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - pip でインストール（requirements.txt がある場合はそれを使う）
     - 例:
       - pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD に依存せず、ファイルの場所はパッケージ実ファイルの位置から探索されます）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading のマッチングモード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 専用 sqlite パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス（デフォルト: data/execution.pid, data/kill.flag）
     - LOG_LEVEL — ログレベル（DEBUG|INFO|...）
   - .env の書式は shell 風（export KEY=VAL や、クォート、コメントをサポート）。

4. データディレクトリ
   - デフォルトでは data/ に DB 等を作成します。必要に応じてディレクトリを作成してください。
     - mkdir -p data

5. （任意）パッケージを編集インストール
   - pip install -e . などで開発インストール可能（setup がある場合）

---

## 使い方（実行例）

- ExecutionEngine を起動（実際に注文を送る側）
  - Paper Trading（疑似ブローカー）で動かす場合:
    - KABUSYS_ENV=paper_trading を設定することで、MockBrokerClient を利用し、data/paper_trading.db に記録します
  - コマンド:
    - python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定します。起動中は pid ファイルが作られます（Settings.pid_file_path）。

- Monitoring（ポーリング監視）を起動
  - ポーリング間隔は環境変数で上書きできます:
    - MONITOR_POLL_INTERVAL=30  （秒）
  - コマンド:
    - python -m kabusys.run_monitoring
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず）。

- Streamlit ダッシュボード
  - 監視 DB を read-only で参照してダッシュボードを起動します:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB が未生成の場合は MonitoringEngine を先に起動してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 機能
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI の API キーは API 呼び出し時に引数で渡すか環境変数 OPENAI_API_KEY を利用します。

- その他
  - process priority / CPU affinity:
    - kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
    - set_cpu_affinity(N) で最初の N コアへ固定（管理者権限が必要になる場合があります）

---

## 主要ファイルとディレクトリ構成

（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込みと Settings
  - run_execution.py          — ExecutionEngine 起動用スクリプト
  - run_monitoring.py         — SystemMonitor 単体起動用スクリプト（ループ）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
    - position_sizing.py       — 発注株数決定・スケール調整
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し・ai_scores 書込）
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ初期化 + DB 操作ラッパー
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag の生成 / 判定
    - alert_manager.py        — LINE Push（通知送信）
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py  — Streamlit ベースの監視 UI
  - execution/
    - order_manager.py        — 注文の生成 / broker 呼び出しの順序管理
    - reconciler.py           — 起動時の注文/ポジション突合
    - ...（BrokerFactory, OrderRepository 等が存在）
  - utils/
    - __init__.py
    - process_priority.py     — 優先度 / CPU affinity ユーティリティ
  - data/（DuckDB/SQLite を期待する data ディレクトリ）
    - 既定: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db

---

## 運用上の注意 / 補足

- Paper Trading と Live は DB を明確に分離する設計です。KABUSYS_ENV=paper_trading を設定すると paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用するため、監視 DB と発注 DB を分けたい場合は設定调整が必要です。
- OpenAI を使う機能は APIキー必須。API 呼び出しはリトライやパース失敗時のフォールバックを行いますが、API 利用料やレート制限に注意してください。
- kill.flag（Settings.kill_flag_path）による停止は冪等に実装されています。Execution 起動時に必要なら clear を行ってください（Settings.kill_flag_clear_on_start により自動クリア可能）。
- ログレベルは LOG_LEVEL 環境変数で制御できます。

---

## 例: よく使うコマンドまとめ

- 仮想環境作成・有効化（UNIX）
  - python -m venv .venv && source .venv/bin/activate
- 依存インストール
  - pip install duckdb psutil requests openai streamlit
- ExecutionEngine（本番／paper）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution
- Monitoring（ポーリング）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載のない内部 API を利用する場合は、ソース（各モジュールの docstring）を参照してください。設計上の意図や制約（ルックアヘッドバイアス回避、冪等操作、フォールバック挙動等）はモジュール内コメントに詳細があります。

必要であれば導入用の Dockerfile / systemd ユニットやサンプル .env.example のテンプレートも作成できます。要望があれば教えてください。