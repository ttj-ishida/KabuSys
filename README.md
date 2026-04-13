# KabuSys

日本株自動売買システムの一部を構成するライブラリ／ツール群です。  
このリポジトリには取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのモジュールが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。  
主要機能（実行エンジン、監視、ポートフォリオ構成、ファクター計算、ニュース NLP 等）を切り分けたモジュール設計になっており、DB（SQLite / DuckDB）を用いた永続化、LINE によるアラート、OpenAI を利用した NLP 評価などを提供します。

設計方針の主なポイント:
- モジュールは可能な限り純粋関数／副作用を限定して実装
- Paper Trading 環境は本番 DB と分離（data/paper_trading.db 等）
- ルックアヘッドバイアスを防ぐため、日付参照に注意した実装
- 外部 API（OpenAI, broker 等）は抽象化／フェイルセーフを採用

---

## 機能一覧

主要機能の要約:

- Execution（発注・実行）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化（本番／Mock）
  - OrderManager、OrderRepository、Reconciler（起動時の自動リコンシリエーション）
  - RiskManager（注文前検査、レートリミット等）

- Monitoring（監視）
  - SystemMonitor：CPU/MEM/DISK、PID ファイル、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件により data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringEngine：各 Monitor を束ねてポーリング
  - streamlit ダッシュボード（監視用 UI）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等ウェイト／スコア重み、セクター制限、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケーリング等）

- Research（リサーチ）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（ニュース NLP / レジーム判定）
  - raw_news を OpenAI でスコアリングして ai_scores に保存（news_nlp）
  - ETF + マクロニュースを合成して market_regime を判定（regime_detector）
  - エクスポネンシャルバックオフやレスポンス検証を実装

- ユーティリティ
  - 設定読み込み（.env / 環境変数）と Settings クラス
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 用検証レポート生成ツール

---

## セットアップ手順

前提
- Python 3.9 以上（typing の Union 表記などを想定）
- SQLite は標準で利用可能
- DuckDB、psutil、requests、openai、streamlit などを利用

推奨的なインストール例（仮想環境を使用）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt が無い場合は上記パッケージを個別に入れてください。  
   必要に応じて他の依存（例えばテスト用パッケージ等）も追加してください。

3. 環境変数 / .env の準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数例（.env に記載する項目）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...         # AI 機能利用時に必須
   - KABUSYS_ENV=development|paper_trading|live
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO

   注意:
   - Settings クラス内の _require() を参照する環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと ValueError になります。
   - .env の解析はシェルスタイル（export 付きやクォートを含む行等）に対応しています。

---

## 使い方

主要な起動方法とツールの使い方を示します。

1) 監視ループの起動（Monitoring）
- デフォルトのポーリング間隔は 60 秒です。環境変数 MONITOR_POLL_INTERVAL で上書き可（整数秒）。不正値や 0 以下は無視されデフォルトにフォールバックします。
- 実行:
  - python -m kabusys.run_monitoring
- 挙動:
  - プロセス優先度を high に設定（set_process_priority）
  - Settings を読み、SQLite（monitoring DB）と DuckDB に接続
  - SystemMonitor の check_once を定期実行しログ・アラートを書き込み

2) 実行エンジンの起動（Execution）
- KABUSYS_ENV により動作モードが変わります:
  - paper_trading: MockBrokerClient を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録。本番 DB と分離。
  - development / live: 本番設定に従ってブローカーへ接続
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - プロセス優先度を high に設定
  - BrokerClientFactory でブローカークライアントを生成
  - OrderRepository / OrderManager / RiskManager / Reconciler 等を初期化し ExecutionEngine を起動
  - 起動時にリコンシリエーション（Reconciler）を行う

3) Paper Trading 検証レポート
- ツール:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH があれば優先）
- 出力内容: 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）など。閾値に基づく PASS/FAIL 判定を表示。

4) Streamlit ダッシュボード（監視）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能: Overview / Positions / Orders / System タブで監視データを確認できます（読み取り専用 URI 経由で SQLite を開く）。

5) AI 関連（OpenAI）
- ニューススコアリング:
  - Python から関数を呼ぶ: kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
    - 書き込み先: ai_scores テーブル（DuckDB）
    - バッチサイズ、リトライ、クリップなどを実装済み
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF (1321) の MA200 とマクロニュースを合成して market_regime テーブルに書き込み
- 注意:
  - OpenAI 呼び出しはネットワークエラーや 5xx 等に対して指数バックオフでリトライしますが、API キー未設定時は ValueError が発生します。
  - レスポンスは厳格に JSON モードを想定して検証・クリーニングしています。

6) 設定読み込みの挙動
- 起動時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば `.env` と `.env.local` を自動読み込みします。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します。

---

## ディレクトリ構成

以下は主要なファイル／モジュールの構成（src/kabusys 以下）。

- src/kabusys/
  - __init__.py                     — パッケージ定義、バージョン
  - config.py                        — Settings（環境変数読み込み、.env パーサ）
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（ETF + マクロニュース）

  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 監視 DB 初期化 + MonitoringDB クラス
    - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度/PID チェック
    - trade_monitor.py               — 注文滞留・約定異常監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — data/kill.flag の生成・管理
    - alert_manager.py               — LINE Push 通知
    - monitoring_engine.py           — 各 Monitor を束ねる
    - streamlit_dashboard.py         — streamlit ダッシュボード

  - execution/
    - order_manager.py               — OrderState マシン外向け API
    - order_repository.py            — DB 操作（orders）  ※（ファイル全体は提示されていませんが存在前提）
    - reconciler.py                  — 起動時リコンシリエーション
    - broker_factory.py              — Broker クライアント生成（Mock / 実装）
    - ...                            — 他の実装ファイル（order_record など）

  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py             — セクターキャップ・レジーム乗数

  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value ファクター
    - feature_exploration.py         — IC, 将来リターン, 統計サマリ

  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト

  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

- data/
  - (データベース等の配置想定パス。デフォルト: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag)

---

## 重要な環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の MockBroker の fill モード（instant|partial|never|reject）
- PID_FILE_PATH — ExecutionEngine の PID 保存先（デフォルト data/execution.pid）
- KILL_FLAG_PATH — KillSwitch による停止フラグ（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

---

## 運用上の注意

- Paper Trading は本番 DB と完全に分離するよう設計されています。KABUSYS_ENV=paper_trading を利用してください。
- OpenAI API 利用時は API キーの管理と課金に注意してください。大量リクエストはレート制限とコストに影響します。
- Monitoring は kill.flag による停止信号を扱います。kill.flag の存在を確認してから ExecutionEngine を再起動してください。
- SQLite / DuckDB のファイルパスは Settings で上書きできます。運用時はバックアップ・ファイルアクセス権を管理してください。
- set_process_priority / set_cpu_affinity は権限により失敗することがあります（警告が出ますが動作継続します）。

---

README は以上です。必要であれば次のような追加を作成できます:
- requirements.txt の生成
- example .env ファイルテンプレート
- 実行例のデモスクリプト / systemd ユニットファイル例
どれを追加するか教えてください。