# KabuSys

日本株向けの自動売買 / 研究 / 監視フレームワーク（モジュール群の一部実装）。  
このリポジトリは、発注エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価などの機能を備えています。

---

## 概要

KabuSys は以下の主要コンポーネントで構成されます。

- ExecutionEngine（発注エンジン）：ブローカーへの注文送信、注文状態管理、リスクチェック、再同期（リコンシリエーション）
- Monitoring（監視）：システムリソース、データ鮮度、注文滞留、ドローダウンなどの監視とログ永続化（SQLite）
- Portfolio（ポートフォリオ構築）：候補選定、重み付け、単元丸め、リスク調整
- Research（調査）：DuckDB を使ったファクター計算、将来リターン・IC 計算など
- AI（ニュース NLP / レジーム判定）：OpenAI を使用したニュースセンチメント、マーケットレジーム判定
- Tools：Paper Trading の検証レポート生成、Streamlit ダッシュボードなど

設計上のポイント：
- 環境変数または .env(.env.local) から設定を読み込み（自動読み込みは無効化可能）
- Paper Trading 環境は本番 DB と厳密に分離（専用 SQLite を使用）
- DuckDB は時系列・ファクターデータの集計に利用
- 監視ログは SQLite（data/monitoring.db）へ永続化

---

## 主な機能一覧

- 実行系
  - 発注作成／送信（OrderManager）
  - リスク制御（RiskManager）
  - 再起動時の自動リコンシリエーション（Reconciler）
- 監視系
  - システム（CPU / メモリ / ディスク）監視とプロセス生存チェック（SystemMonitor）
  - 注文滞留・約定異常監視（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード（read-only）
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等金額 / スコア重み配分
  - リスク調整（セクター上限、レジーム乗数）
  - 株数算出（単元丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングし ai_scores に書込む
  - マクロニュース + ETF MA200 を用いた market_regime 判定
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - 監視 DB 用 Streamlit ダッシュボード

---

## セットアップ手順

前提
- Python 3.10 以上（typing で X | Y を使用）
- システムに応じて psutil の機能利用のための権限が必要な場合があります

1. リポジトリをクローン／配置
   - ソースは `src/kabusys/` 配下に配置されている想定です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例（最低限）:
     - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨

4. 環境変数 / .env
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既存の OS 環境変数は保護されます）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（デフォルト値 / 必須）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API）
     - OPENAI_API_KEY — AI 機能を使う場合は必須
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（監視・停止制御に使用）

5. data ディレクトリ
   - 一部のスクリプトは data/ 以下にファイルを作成します（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）。実行ユーザーが書き込み可能であることを確認してください。

---

## 使い方（実行例）

基本的にモジュールとして main() を提供しているので `python -m` で起動できます（プロジェクトルートから）。

1. 監視プロセス起動（SystemMonitor ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）
   - 注意: 監視は環境にかかわらず Settings.sqlite_path（本番）を使って監視テーブルを初期化します

2. ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
   - 起動時に data/stop_requested.flag が立っていると起動をスキップします
   - 実行中に data/stop_requested.flag が作成されると安全に停止します

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で DB を開き、Overview / Positions / Orders / System を参照できます

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB は `--db` でパス指定、未指定時は環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を参照

5. AI 関連
   - ニュース NLP（ai.score_news）や regime_detector.score_regime は OPENAI_API_KEY が必要
   - DuckDB 接続と target_date を渡して実行します（CLI のラッパーは実装例に合わせて作成してください）

---

## ファイル / ディレクトリ構成

以下は主要なパッケージ構成（src/kabusys 以下）です。モジュールはさらに細分化されています。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env ロード、Settings クラス
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化 API (MonitoringDB)
    - system_monitor.py — CPU/メモリ/ディスク、プロセス PID、データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理（Execution 停止シグナル）
    - alert_manager.py — LINE Push API 経由の通知
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード
  - execution/
    - order_manager.py — 発注 API の上位ロジック
    - reconciler.py — 起動時の自動復旧 / 同期
    - （その他: broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・丸め・cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value などの計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングして ai_scores へ書込む
    - regime_detector.py — マクロ+MA200 を使った市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度設定（Windows / POSIX 対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

その他：
- data/ 以下は実行時に使用する PID / flag / DB ファイル格納先（例: data/monitoring.db, data/paper_trading.db, data/execution.pid）

---

## 重要な動作・運用上の注意

- .env の自動読み込み
  - プロジェクトルートは .git や pyproject.toml を基準に自動検出されます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は paper_trading 用 SQLite を使用します（本番側 DB を汚しません）。
  - ただし Monitoring の初期化（init_monitoring_db）は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用する実装に注意してください（run_monitoring の設計上の仕様）。
- 停止 / 強制停止
  - data/stop_requested.flag: run_monitoring / run_execution で監視して安全にループを抜けるために使用
  - data/kill.flag: KillSwitch による ExecutionEngine 停止指示に使用
- OpenAI / 外部 API
  - OpenAI 呼び出しはネットワークエラー・429・5xx に対してリトライを行う設計ですが、API キーは環境変数 OPENAI_API_KEY で与える必要があります
- 権限
  - psutil によるプロセス優先度設定や CPU affinity 設定は権限により失敗する場合があり、失敗時は警告のみで処理を継続します

---

## 例 .env（参考）

例（プロジェクトルート/.env）:

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
MONITOR_POLL_INTERVAL=60
PAPER_FILL_MODE=instant

---

この README はコードベースの要点をまとめたもので、実運用の手順（CI/CD、デプロイ、監視・ロギングの詳細設定、ブローカークライアントの実装差分等）は別途ドキュメント化することを推奨します。必要であれば、起動フロー図・環境変数一覧（必須/任意分離）・デプロイ手順のテンプレートも用意します。