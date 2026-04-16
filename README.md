# KabuSys

日本株自動売買システム（軽量プロトタイプ）  
このリポジトリは、シグナル→発注の ExecutionEngine、監視機能、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ニュースNLP / レジーム判定（LLM 利用）などを含むモジュール群で構成されています。

## 概要
- 実際のブローカー接続（kabuステーション等）または Paper Trading（モック）で注文実行が可能。
- 監視コンポーネントがシステム稼働状況・注文滞留・リスク（ドローダウン等）を定期的にチェックし、リスクイベントをログに残したり、必要に応じて kill.flag により ExecutionEngine を安全に停止します。
- DuckDB / SQLite をデータ層に用い、ファクター計算やニュース集約、検証レポート生成ツールなどを提供します。
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメントおよびマクロ判定機能を実装（APIキーは環境変数で指定）。

## 主な機能一覧
- ExecutionEngine（発注エンジン）
  - 本番 / Paper Trading 切替（KABUSYS_ENV）
  - リコンシリエーション（起動時に未確定注文の同期）
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限検出
  - KillSwitch：重大事象で ExecutionEngine に停止シグナルを発行
  - AlertManager：LINE push による通知（任意）
  - Streamlit ダッシュボード（監視用）
- ポートフォリオ構築（純粋関数群）
  - 候補選定 / 等比率・スコア加重配分 / 単元株丸め / セクター制約 / レジーム乗数
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算 / IC 計算 / 統計サマリー
- AI 系
  - news_nlp: ニュースセンチメントを LLM でスコア化して ai_scores に保存
  - regime_detector: ETF MA200 とマクロ記事センチメントを合成して market_regime を判定
- ツール
  - paper_verification_report: Paper Trading DB の検証レポート生成

## セットアップ手順（開発用）
注意：プロジェクトに requirements.txt が無い場合は下記パッケージが必要になります（例示）。環境に合わせて仮想環境を使ってください。

1. Python 仮想環境の作成・有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに依存パッケージ一覧がある場合はそれを利用してください。

3. データディレクトリの作成
   - mkdir -p data

4. 環境変数の設定
   - .env または OS の環境変数で設定します。自動ロードはプロジェクトルートに .env / .env.local があれば優先的に読み込まれます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（主なもののみ、デフォルト値や必須性を示します）:

   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - paper_trading にすると MockBrokerClient を使用し、Paper 用 DB に書き込みます。
   - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
   - KABU_API_PASSWORD — 必須（kabuステーション API 用）
   - OPENAI_API_KEY — LLM 呼び出し用（news_nlp / regime_detector）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（任意）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE — Paper 報告の約定モード (instant|partial|never|reject)（デフォルト: instant）
   - PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（デフォルト 60）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

   .env の簡易例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

## 初期 DB（監視テーブル）作成
多くの起動スクリプトは内部で監視 DB の初期化を行います（init_monitoring_db が呼ばれます）。手動で実行したい場合は Python REPL 等で次を呼んでください:

- from kabusys.config import Settings; import sqlite3
- settings = Settings(); conn = sqlite3.connect(str(settings.sqlite_path)); from kabusys.monitoring.monitoring_db import init_monitoring_db; init_monitoring_db(conn); conn.close()

## 使い方（主要コマンド）

- ExecutionEngine を起動する
  - デフォルト（本番 / 設定に依存）:
    - python -m kabusys.run_execution
  - Paper Trading モードで動かす:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper トレードは専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

  実行挙動:
  - 起動時にプロセス優先度を high に設定し、Broker クライアントや依存コンポーネントを組み立て、エンジンをスレッドで実行します。
  - data/stop_requested.flag（プロジェクトルート配下の data/stop_requested.flag）で停止シグナルを検出して安全に停止します。
  - PID ファイル（data/execution.pid）を使用してプロセス生存を検出します。

- Monitoring を起動する（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを永続化します。

- Streamlit ダッシュボード（監視）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - Read-only モードで SQLite に接続し、ダッシュボードを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム経由）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # 書き込み数を返す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

## 停止・強制停止
- run_execution / run_monitoring は data/stop_requested.flag をチェックして停止します（手動で停止する場合はこのフラグを作成してください）。
- KillSwitch は重大リスク検出時に data/kill.flag を書き込み、ExecutionEngine 起動時にこのフラグがあれば起動を回避します。kill.flag の削除は KillSwitch.clear() または手動でファイル削除してください。

## ログ・優先度
- 起動時にプロセス優先度を可能なら high に変更します（プラットフォーム依存）。この処理は psutil を使っていますが、権限不足などで設定できない場合は警告ログでスキップします。
- ログレベルは環境変数 LOG_LEVEL で指定可能（DEBUG/INFO/...）。

## ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュース NLP スコアリング
    - regime_detector.py — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定、リスク調整
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算
    - feature_exploration.py — IC 等の解析ユーティリティ
  - monitoring/
    - monitoring_db.py — 監視ログ（SQLite）永続化層
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 注文監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — モニタ群のオーケストレーション
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ...（発注・同期関連）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/  （実行時に作成）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading の場合）
    - kabusys.duckdb（デフォルトの DuckDB ファイル）
    - execution.pid, kill.flag, stop_requested.flag

（上記はコードベースの主要モジュール名と機能を抜粋したものです。詳細は各モジュールの docstring を参照してください。）

## 注意点 / 設計上のポイント
- Paper Trading は本番 DB と分離：KABUSYS_ENV=paper_trading の場合、Paper 用 SQLite に記録されます。
- 監視データは（run_monitoring によって）常に sqlite_path（本番）へ書き込みます（環境に依らず）。
- LLM 呼び出し（OpenAI）を行う際は APIKey を環境変数または関数引数で与える必要があります。API の失敗時はフェイルセーフとして処理を続行する設計の箇所が多くあります（完全失敗が必ずしも致命的ではない設計）。
- .env の自動ロードはプロジェクトルートの判定を行い、OS 環境変数を保護します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

## 開発 / 貢献
- コードは各コンポーネントが比較的疎結合になるよう設計されています（DB 接続や client を注入してテスト可能）。
- 単体テストや CI 設定が無い場合は、まずユニットテストを追加し、API 呼び出し部分はモック化してテストしてください。

---

不明点や README に追加したい内容（例えば具体的な依存パッケージ一覧、実運用時の systemd 例、より詳細な .env.example など）があれば教えてください。必要に応じて README を拡充します。