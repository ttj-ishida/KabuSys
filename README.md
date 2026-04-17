# KabuSys

日本株向け自動売買システムの一部実装リポジトリ（モジュール群）。  
このREADMEはコードベース（src/kabusys 以下）を元に、セットアップと利用方法、主要コンポーネントの説明を日本語でまとめたものです。

注意: .env（機密トークン等）を絶対にGitにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な機能には以下が含まれます。

- ExecutionEngine（発注エンジン）とそれを補助する OrderRepository / OrderManager / RiskManager / Reconciler
- Monitoring（システム稼働・注文・リスク監視）
- Portfolio（銘柄選定・重み算出・ポジション決定）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム検知）
- ユーティリティ（設定読み込み、プロセス優先度設定など）
- ツール（ペーパートレード検証レポート生成など）

DBには分析用の DuckDB と監視/発注履歴用の SQLite を使用します。ペーパートレードは本番DBと完全に分離されます。

---

## 主な機能一覧

- 設定管理
  - .env の自動/対話的ロード（config_setup）、環境変数の検証（validate_config）
  - Settings クラスで各種設定へ統一的にアクセス可能

- Execution（発注）
  - 本番・ペーパートレードの切替対応（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント抽象化（ペーパートレード時は Mock）
  - RiskManager（ポジション上限・ドローダウン等のリスク制御）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk/プロセス状態/データ鮮度を監視
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine に停止シグナル
  - MonitoringEngine: これらを束ねてポーリングしアラートを発行

- Portfolio（建玉構築）
  - 銘柄選定（スコア順ソート）、等金額/スコア加重配分
  - セクター集中制限・レジーム乗数適用
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）

- Research（研究用）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）やファクターサマリ
  - DuckDB を用いたオフライン分析

- AI（OpenAI を利用）
  - news_nlp: ニュース記事を LLM でスコアリングし ai_scores テーブルへ書き込み
  - regime_detector: ETF の MA 乖離とマクロニュースの LLM 評価を合成して市場レジーム判定

- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 必要な依存パッケージ（代表例）

コード内で使用される主要ライブラリ：

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を有効にする場合）
- そのほか標準ライブラリ

（実際の requirements.txt は本リポジトリに含まれていない場合があります。用途に応じて上記を pip でインストールしてください）

---

## セットアップ手順

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

3. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成
     - 必須例:
       - JQUANTS_REFRESH_TOKEN=...
       - KABU_API_PASSWORD=...
     - 推奨（デフォルトがあるものは省略可）:
       - KABUSYS_ENV=development|paper_trading|live
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - OPENAI_API_KEY=...（AI 機能使用時）
       - LOG_LEVEL=INFO

   - 自動 env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプト（run_execution/run_monitoring）が起動時に SQLite のテーブル作成を行います。
   - DuckDB のスキーマは分析ワークフローに応じて用意してください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパー両対応）
  - python -m kabusys.run_execution
  - 実行時、KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
  - 起動前に data/stop_requested.flag が存在すると起動しません（停止フラグの扱い）。

- Monitoring を起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を参照します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定して使用
  - news_nlp.score_news / regime_detector.score_regime を呼び出して DB に書き込み

停止フラグ / Kill Switch:
- ExecutionEngine を外部から停止したい場合はプロジェクトの data ディレクトリに `kill.flag` を作成します（KillSwitch が検出して停止処理へ）。
- run_execution/run_monitoring は stop_requested.flag の存在を見て終了します（内部の制御ファイル名に注意）。

注意: run_execution/run_monitoring は process priority を "high" に設定しようとします（psutil を使用）。権限やプラットフォームによって設定に失敗することがありますが、ログで警告されスキップされます。

---

## 主な環境変数一覧（代表）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — 分析用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LOG_LEVEL — ログレベル
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートに src/kabusys 配下がある想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 管理クラス（テーブル初期化・CRUD）
    - system_monitor.py       — CPU/メモリ/プロセス/データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag を書き込むロジック
    - monitoring_engine.py    — 各モニタを束ねるポーリングエンジン
    - alert_manager.py        — （未記載だがアラート管理）
  - execution/                — ExecutionEngine 周りの実装（OrderRepository等、詳細はリポジトリ内）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（LLM + MA 合成）
  - data/                     — 実行時に使用するファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid 等）

---

## 運用上の注意・ベストプラクティス

- .env に書いた機密情報は絶対にバージョン管理に含めないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動クリアは危険）。
- Monitoring は本番 sqlite_path を常に参照するため、環境切替の際に参照先 DB に注意してください。
- OpenAI を使用するスクリプトは API レート制限やエラーに対してリトライ・フォールバック処理が組まれていますが、APIキーと利用料に注意してください。
- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。実運用前の検証にはこちらを活用してください。

---

## 参考コマンド一覧

- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

このREADMEはコードコメントやスクリプトの挙動に基づいて作成しています。実際の運用時は config/*.yaml（存在する場合）や各モジュールのドキュメント、運用手順書に従ってください。必要であれば各モジュールの詳細な開発者向けドキュメント（API、クラス図、データベーススキーマ等）も作成可能です。