# KabuSys

日本株自動売買システムの一部コードベース。  
このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などのモジュールを含みます。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システム向けユーティリティ群です。主な目的は以下：

- 注文の作成・送信・状態同期（Execution）
- 監視（プロセス生存、データ鮮度、注文滞留、ドローダウン等）
- ポートフォリオ構築・銘柄配分・ポジションサイズ計算（Portfolio）
- ファクター計算・リサーチ（Research）
- ニュースの NLP を使ったセンチメント付与・市場レジーム判定（AI）
- Paper Trading 用検証ツールや Streamlit ダッシュボード等の運用支援ツール

設計方針の例：
- DuckDB / SQLite を使ったデータ管理（DuckDB は時系列ファクター計算、SQLite は監視ログ等）
- 環境に応じた挙動（`KABUSYS_ENV=paper_trading` では MockBroker を使用し、本番 DB と分離）
- OpenAI を使った NLP 機能（API キーは環境変数で指定）
- フェイルセーフ設計（API 失敗時のフォールバック、部分書き込み保護、データマイグレーションなど）

---

## 主な機能一覧

- Execution（発注・リコンシリエーション）
  - OrderManager / OrderRepository / Reconciler による注文管理と復旧処理
  - BrokerClientFactory による実ブローカー or MockBroker の切替（`KABUSYS_ENV` に従う）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイル (data/kill.flag) による ExecutionEngine 停止
  - AlertManager: LINE Push によるアラート送信（オプション）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（配分・サイズ計算）
  - 候補選定、等金額/スコア加重、リスクベースの数量計算、セクターキャップ、レジーム乗数
- Research（ファクター計算・探索）
  - Momentum / Volatility / Value などのファクター、将来リターン計算、IC や統計サマリー
- AI（ニュース NLP / レジーム判定）
  - raw_news を OpenAI に送り銘柄別センチメントを ai_scores に保存
  - ETF（1321）MA200 とマクロニュースで日次レジーム判定を行い market_regime に保存
- ツール
  - Paper Trading 検証レポート生成スクリプト（過去期間の稼働率・注文成功率・レイテンシ等を集計）
  - Streamlit ダッシュボード（監視データ可視化）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成・有効化します。

   - Linux / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存ライブラリをインストールします（プロジェクトに requirements.txt があればそれを利用してください）。最小限の主なパッケージ例：

   ```
   pip install duckdb psutil requests openai streamlit
   ```

   - 実際のプロジェクトでは追加の依存（DB ライブラリやテストツール等）がある可能性があります。

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を配置できます。`kabusys.config` は自動でプロジェクトルートの `.env` を読み込みます（OS 環境変数が優先）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（用途に応じて設定）：
   - JQUANTS_REFRESH_TOKEN （必須：J-Quants API 用）
   - KABU_API_PASSWORD （必須：kabuステーション API 用）
   - OPENAI_API_KEY （AI 機能を使う場合必須）
   - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - `paper_trading` の場合は MockBroker を使用し DB は `data/paper_trading.db` に記録
   - SQLITE_PATH（監視 DB）デフォルト: `data/monitoring.db`
   - DUCKDB_PATH（分析データ）デフォルト: `data/kabusys.duckdb`
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト `data/paper_trading.db`）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に使用）
   - LOG_LEVEL（例: INFO, DEBUG）
   - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

4. データディレクトリを作成します（必要な場合）：

   ```
   mkdir -p data
   ```

   - 初回実行時に監視 DB のテーブルは `init_monitoring_db()` により作成されます。

---

## 使い方（起動・ツール）

各スクリプトは package モードで実行できます（src 配下を PYTHONPATH に含めている前提）。例:

- 監視ループを起動（SystemMonitor 単体ランナーも同様）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を常に使用します（環境にかかわらず）。

- ExecutionEngine（取引実行）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、`data/paper_trading.db` に記録して本番 DB と完全に分離します。
  - 起動時にプロセス優先度を "high" に設定しようと試みます（権限により失敗することがあります）。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で別の SQLite ファイルを指定可能（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）。

- Streamlit 監視ダッシュボード起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（ニューススコア / レジーム判定）はプログラムから呼び出します。例（概念）:
  ```py
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
  ```

注意:
- AI 機能を使うには `OPENAI_API_KEY` が必要です。設定がないと例外が発生します。
- LINE 通知は token / user_id が空だと送信せずログのみ行います。

---

## 主要設定（要点）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - `paper_trading` は実トレードを行わず、MockBroker と専用 DB を使用。
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH: DB ファイルパス
- OPENAI_API_KEY: OpenAI 利用時に必須
- LOG_LEVEL: ログレベル（INFO など）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセスの PID / kill flag のファイルパス

.env の読み込みルール（kabusys.config）
- 自動読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env パーサは `export KEY=val` やクォートをサポートし、コメント処理も備えています。

---

## ディレクトリ構成（抜粋）

（ファイルは src/kabusys 配下にあります。ここでは主要モジュールを示します）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理 (.env ロード等)
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite による監視ログ永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py        — LINE プッシュ通知管理
    - monitoring_engine.py    — 複数 Monitor を束ねる実行ループ
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ... (注文関連)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数・投下資金制御
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別スコア付与
    - regime_detector.py      — MA200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - run_monitoring.py         — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト

---

## 運用上の注意・ヒント

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成および簡易マイグレーション（カラム追加）を行います。初回実行で自動的にテーブルが作られます。
- Paper Trading
  - `KABUSYS_ENV=paper_trading` にすると実ブローカーは使われず、paper 用 SQLite（デフォルト data/paper_trading.db）へ全記録されます。本番データベースと完全に分離されます。
- プロセス優先度 / CPU affinity
  - 起動スクリプトは可能ならプロセスを high 優先度に設定します（権限によっては失敗しログが出ます）。
- Kill Switch
  - KillSwitch は `data/kill.flag`（デフォルト）を作成して ExecutionEngine に停止シグナルを送ります。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でフラグを消します（Settings による挙動）。
- ロギング
  - run_* スクリプトはデフォルトで INFO レベルでログを出力します。`LOG_LEVEL` 環境変数で変更可能です。

---

## 開発・テスト

- モジュールは多数の純粋関数（副作用の少ない関数）で設計されているため、ユニットテストが書きやすくなっています。外部依存（OpenAI / ブローカー / DB）部分はモック可能です。
- OpenAI 呼び出し箇所は `_call_openai_api` をテストで patch して差し替えることを想定した実装になっています。

---

この README はコードベースの主要点をまとめたものです。実際のデプロイや運用ルール、追加の依存関係・初期データロード手順などはプロジェクト固有の運用ドキュメントに従ってください。必要であれば、特定モジュールの詳細説明（API 仕様、例、テスト方法）を別途作成します。