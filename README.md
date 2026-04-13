KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システム「KabuSys」の一部実装です。
監視・実行・ポートフォリオ構築・リサーチ・AI を組み合わせたモジュール群を含みます。
以下はコードベース（src/kabusys 以下）を対象とした README です。

要約 / プロジェクト概要
------------------
KabuSys は以下の責務を持つモジュール群から構成されます。

- Execution: ブローカーとのやり取り、注文ライフサイクル管理、リコンシリエーション
- Monitoring: システム安定性・注文滞留・リスク（ドローダウン等）の監視、アラート送信（LINE）
- Portfolio: 候補選定・配分・ポジションサイズ計算、セクター制限・レジーム調整
- Research: DuckDB上の価格／財務データから各種ファクター・将来リターン・IC等を算出
- AI: ニュースセンチメントによる銘柄スコアリング、マクロニュースとETF MA を組み合わせたレジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit 監視ダッシュボード等
- Utils: プロセス優先度・CPU affinity 設定等のユーティリティ

主な特徴（機能一覧）
------------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading 切替（KABUSYS_ENV）
  - BrokerClientFactory を通じて実ブローカー or MockBroker を利用
  - リスク管理（RiskManager）、注文管理（OrderManager）、リコン（Reconciler）を統合

- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度を監視
  - TradeMonitor: 注文滞留（stale orders）・約定異常価格を検出
  - RiskMonitor: ドローダウンやポジション上限の監視とリスクログ記録
  - KillSwitch: 条件成立時に flag ファイルを書き、Execution 停止シグナルを送る
  - AlertManager: LINE Push API を用いた一方向通知（クールダウン管理）

- Portfolio（選定・重み付け・サイズ決定）
  - 候補選定（score / rank ベース）、等金額・スコア加重配分、リスクベースの株数計算
  - セクターキャップ、レジーム乗数による資金調整

- Research
  - momentum/volatility/value 等のファクター算出（DuckDB 接続で SQL 実行）
  - 将来リターンや IC（スピアマンランク相関）計算、統計サマリー

- AI
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を用いてニュース記事を銘柄別にセンチメント採点、ai_scores テーブルへ永続化
  - regime_detector.score_regime: ETF（1321）のMA乖離とマクロニュースセンチメントを統合して日次レジーム判定を実行

- ツール
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定を出力
  - Streamlit ダッシュボード: 監視 DB（monitoring.db）を読み取るフロントエンド

前提・依存
----------
- Python 3.10+
- 必要な主要パッケージ（例）:
  - duckdb, psutil, openai, requests, streamlit
- DuckDB / SQLite を用いたローカル DB（data/*.db）
- OpenAI を利用する機能は OPENAI_API_KEY が必要

セットアップ手順
-------------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（requirements.txt がある場合）
   - pip install -r requirements.txt
   - ない場合の例:
     - pip install duckdb psutil openai requests streamlit

3. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動ロードされます（OS 環境変数が優先）。
   - 必須（使用する機能に応じて）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（research 等で使用）
     - KABU_API_PASSWORD — kabuステーション API 用認証
     - OPENAI_API_KEY — AI（news/regime）を使う場合
   - 参考: Settings クラスにデフォルトや期待値の説明あり（src/kabusys/config.py）
   - 自動ロードを無効化する:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じてパスは環境変数で上書きできます（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）

使い方（実行例）
--------------
- 監視ループを起動（Monitoring）
  - デフォルトで 60 秒ポーリング。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（1 以上）
  - python -m kabusys.run_monitoring
  - または: python src/kabusys/run_monitoring.py
  - KABUSYS_ENV に依らず監視用 DB は本番 sqlite_path（SQLITE_PATH）を使用します。
  - 起動時にプロセス優先度を "high" に設定します。

- 実行エンジンを起動（Execution）
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を利用し data/paper_trading.db に分離して記録されます。
    - python -m kabusys.run_execution
  - 本番モード:
    - KABUSYS_ENV=live（または development 等）を設定して実行
  - 実行時もプロセス優先度を "high" にします。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは指定 DB を read-only URI で開きます。MonitoringEngine が先に DB を作成している必要があります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db オプションで DB パスを指定可能（デフォルト: data/paper_trading.db）

- AI 機能（ニューススコア／レジーム判定）
  - OPENAI_API_KEY が必要です。呼び出しはモジュール関数を直接利用できます（テスト時は _call_openai_api をモック可能）。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

主要な環境変数（抜粋）
-------------------
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意事項 / 実装上のポイント
-----------------------
- Settings モジュールは .env/.env.local をプロジェクトルートから自動ロードします（CWD ではなく __file__ を基点にルートを探索）。自動ロードを無効化できます。
- Monitoring は環境にかかわらず監視用の本番 sqlite_path を使う設計です（Paper Trading でも監視は本番 DB に記録することに注意）。
- Execution の Paper Trading は data/paper_trading.db を使って本番 DB と完全分離されます（KABUSYS_ENV=paper_trading）。
- OpenAI API 呼び出しは堅牢化されており、429/タイムアウト/5xx に対して指数バックオフでリトライします。失敗時はフェイルセーフ（スコア=0 など）で続行する設計です。
- monitoring_db.init_monitoring_db は冪等で、マイグレーション的にカラム追加も行います（例: peak_value, latency_ms）。
- process_priority ユーティリティは Windows / POSIX を吸収しますが、権限不足等では警告が出てスキップします。

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 以下の主なファイル・モジュールと簡単な説明です（この README に含まれるコード群に基づく）:

- src/kabusys/
  - __init__.py             — パッケージ定義（__version__ 等）
  - config.py               — 環境変数 / 設定管理（Settings）
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py           — ニュースセンチメントの LLM スコアリング
    - regime_detector.py    — マクロ + ETF MA による市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py     — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py      — 注文滞留・約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 管理
    - alert_manager.py      — LINE への通知
    - monitoring_engine.py  — 各 Monitor を束ねるループ
    - streamlit_dashboard.py— Streamlit での監視ダッシュボード

  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・資金配分（lot, cost buffer, aggregate cap）
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py    — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
    - __init__.py

  - execution/
    - reconciler.py         — 起動時の注文/ポジション突合せ
    - order_manager.py      — 注文状態遷移の外向き API
    - （その他: broker_factory, order_repository, order_record, execution_engine 等が存在）

  - tools/
    - paper_verification_report.py — Paper Trading 集計レポート生成
    - __init__.py

  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

補足 / 開発時メモ
----------------
- DB スキーマは monitoring_db.init_monitoring_db で管理されます。開発中にカラムを追加する場合はここにマイグレーションロジックを入れてください。
- OpenAI を使う箇所は外部呼び出し部分をラップ／分離してあり、テスト時には _call_openai_api 等をモックしてテスト可能です。
- Streamlit は監視用 DB を read-only URI で開くため、MonitoringEngine が走っているホストの監視 DB を参照することができます。

ライセンス / 貢献
----------------
（ここではライセンス情報は省略しています。実プロジェクトでは LICENSE を追加してください。）

以上がこのコードベースの概要・セットアップ・使い方です。具体的な拡張や運用ルール（ブローカー接続情報、資金管理ポリシー、テスト方針など）は別途ドキュメント化してください。必要であれば README に含める起動例や環境変数の .env.example を作成する手伝いもできます。