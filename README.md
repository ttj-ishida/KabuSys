# KabuSys

日本株向け自動売買／リサーチ基盤の小規模モジュール群です。  
このリポジトリは、発注実行エンジン、監視（モニタリング）、ファクター計算、ニュースNLP を含む主要コンポーネントを持ち、DuckDB / SQLite をデータ層に使用します。

以下の README はコードベース（src/kabusys 以下）に基づく利用説明書です。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群です。

- シグナルに基づく発注の実行（ExecutionEngine）
- 発注状態の永続化と再同期（OrderRepository / Reconciler）
- リスク制御（RiskManager, RiskMonitor）
- システム・注文に関する監視（MonitoringEngine, SystemMonitor, TradeMonitor）
- ファクター計算・研究ユーティリティ（research パッケージ）
- ニュースを LLM（OpenAI）で解析して銘柄別スコア化（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 可視化用 Streamlit ダッシュボード

設計方針の要点：

- DuckDB を主な市場データの集計に使用（prices_daily, raw_financials 等）。
- 監視ログ等は軽量な SQLite（data/monitoring.db）に永続化。
- Paper trading（モックブローカー）モードを提供し、本番 DB と分離可能。
- LLM 呼び出しは失敗に寛容（フォールバック・リトライ実装あり）。

---

## 主な機能一覧

- ExecutionEngine
  - シグナル読み取り→Gate（リスク）チェック→発注（BrokerClient）→同期
  - 発注の二相永続化や Reconciler による起動時復旧
- OrderManager / OrderRepository
  - 注文ステートマシン、DB 永続化、同期ロジック
- RiskManager / RiskMonitor
  - レート制限、サーキットブレーカー、ドローダウン・ポジション上限監視
- MonitoringEngine
  - SystemMonitor / TradeMonitor / RiskMonitor の統合ポーリング
  - Kill switch（kill.flag）による実行停止シグナル
  - LINE への通知（AlertManager）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 前方リターン／IC 計算、統計サマリ
- ai
  - ニュースの LLM を用いた銘柄別センチメントスコア化（score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（score_regime）
- Streamlit ダッシュボード（監視情報の可視化）

---

## 要件（推奨）

- Python 3.10+
- 推奨ライブラリ（一例）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
- SQLite（標準ライブラリで利用可）

（実際の requirements.txt はプロジェクトに含めてください。上記は本リポジトリで使われている主要依存です。）

---

## セットアップ手順

1. リポジトリをクローン / 取得し、作業ディレクトリをプロジェクトルートにする（pyproject.toml / .git が存在する想定）。

2. 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（requirements.txt があれば）:
   - pip install -r requirements.txt
   - ない場合は主要パッケージを個別に:
     - pip install duckdb psutil requests

   - Streamlit ダッシュボードを使う場合:
     - pip install streamlit

   - OpenAI を利用する場合:
     - pip install openai

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を作成すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数の例（必須や推奨）:

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須 for live)
     - KABU_API_BASE_URL (省略可、デフォルト http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
     - KILL_FLAG_PATH: Kill flag（デフォルト data/kill.flag）
     - PAPER_FILL_MODE: paper_trading 時の fill 挙動（instant|partial|never|reject; デフォルト instant）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）
     - LOG_LEVEL: ログレベル（DEBUG|INFO|...）

   - .env の書式は shell の一般的な format に準拠（export 対応、コメント対応あり）。

5. データディレクトリを作成:
   - mkdir -p data

---

## 使い方

※ このリポジトリはソースルートが `src/` 配下になっているため、実行時に PYTHONPATH を通すか、パッケージインストールしてください。

- 簡易（ローカル）実行例:
  - PYTHONPATH=src python src/kabusys/run_monitoring.py
  - PYTHONPATH=src python src/kabusys/run_execution.py

- ExecutionEngine（発注エンジン）を起動
  - 環境を paper_trading にすると MockBrokerClient / 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されます。
    - export KABUSYS_ENV=paper_trading
    - PYTHONPATH=src python src/kabusys/run_execution.py
  - 本番想定:
    - export KABUSYS_ENV=live
    - 必要な本番用環境変数（KABU_API_PASSWORD 等）を設定してから実行。

- MonitoringEngine（監視ループ）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - export MONITOR_POLL_INTERVAL=30
    - PYTHONPATH=src python src/kabusys/run_monitoring.py
  - 監視は Settings に従い常に本番用 sqlite_path を使用します（paper_trading の影響を受けない）。

- Streamlit ダッシュボード（監視 UI）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - パスに指定した SQLite を読み取り専用で開きます（MonitoringEngine が書き込んでいる DB）。

- AI 機能
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（api_key 引数でも可）
    - raw_news / news_symbols / ai_scores テーブルを扱います
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースを合成して market_regime テーブルへ書き込み

- Kill Switch
  - KillSwitch は監視で評価されると `data/kill.flag` に理由テキストを書き込み、ExecutionEngine は起動時やループ中にこのファイルを検知して安全停止します。
  - 起動時にフラグをクリアしたい場合は、Settings.kill_flag_clear_on_start を 1 に設定するオプションが Settings にあります。

---

## 重要な実行上の注意点

- paper_trading モードではブローカー呼び出しはモックに差し替えられ、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）にのみ書き込みます。本番 DB（SQLITE_PATH）とは分離されます。
- run_monitoring.py はプロセス優先度を上げるユーティリティを呼びます。権限がない環境では警告が出ますが続行します。
- LLM/API 呼び出しはネットワークエラーや 429 を考慮したリトライ実装がありますが、失敗時はフェイルセーフで継続する設計です。
- DuckDB の一部操作では executemany に空リストを渡せない制約を考慮した実装になっています。DuckDB バージョンに注意してください。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL
- OPENAI_API_KEY
- SQLITE_PATH (デフォルト data/monitoring.db)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- MONITOR_POLL_INTERVAL (秒、run_monitoring.py で使用)
- LOG_LEVEL

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env ロードと Settings 抽象
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - execution/
    - execution_engine.py — ExecutionEngine 本体（シグナル処理・push ドレイン等）
    - order_manager.py — 発注 API 層（Order ステート遷移を扱う）
    - order_repository.py — SQLite ベースの注文永続化（not shown: 実装ファイル）
    - reconciler.py — 起動時の注文/ポジション照合
    - risk_manager.py — 実行時リスク管理（not shown: 実装ファイル）
    - broker_factory.py — BrokerClient の生成（実ブローカー/Mock の差し替え）
    - broker_api.py — ブローカー API 抽象プロトコル（型定義等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出 / スケーリング
    - risk_adjustment.py — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 + DB ラッパ（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み/検査
    - alert_manager.py — LINE Push 通知ラッパ
    - monitoring_engine.py — 複数 Monitor のポーリング統合
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB を利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM で評価して ai_scores に書き込む
    - regime_detector.py — マクロ + MA200 で市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

（上記に含まれないファイルも存在しますが、主要コンポーネントの一覧です。）

---

## 開発時のヒント

- ソースを直接実行する場合は PYTHONPATH=src を指定するか、パッケージとしてインストールしてください。
- DuckDB の SQL はコード中に含まれているため、prices_daily / raw_financials 等のテーブルを DuckDB に用意してから研究機能を実行してください。
- monitor 系は init_monitoring_db() を呼んで DB スキーマを作成するため、初回は data ディレクトリを作成しておくとスムーズです。
- AI 機能のテスト時は OpenAI の呼び出し部分（_call_openai_api 等）をモックすることで速度とコストを抑えられます。

---

## ライセンス / 貢献

本 README はコードベースの説明用です。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

この README はソース内コメント・ドキュメント文字列に基づいてまとめています。より詳細な利用方法（Signal Queue の仕様、OrderRepository の DB スキーマ詳細、Broker の実装など）は該当のモジュールの docstring を参照してください。