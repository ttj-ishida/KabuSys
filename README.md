# KabuSys

KabuSys は日本株の自動売買・研究・監視を支援する内部ライブラリ群です。本リポジトリには、ExecutionEngine（発注エンジン）／Monitoring（監視）／Research（ファクター計算、特徴量解析）／AI（ニュースセンチメント・レジーム判定）等の主要コンポーネントが含まれます。

以下の README はリポジトリ内のソースコードに基づき作成しています。実行や運用に必要な主要情報、セットアップ手順、起動コマンド例、ディレクトリ構成をまとめています。

目次
- プロジェクト概要
- 機能一覧
- 要求環境 / 依存パッケージ
- セットアップ手順
- 環境変数（主要なもの）
- 使い方（起動例）
- 注意点 / 運用メモ
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群です。

- 自動売買の実行エンジン（ExecutionEngine）と関連コンポーネント（OrderManager、RiskManager、Reconciler 等）
- 実行状況・システム状態の監視（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager）
- ポートフォリオ構築の純関数群（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算 / 特徴量解析（DuckDB を利用）
- ニュースの NLP による銘柄スコアリング・市場レジーム判定（OpenAI API を利用）
- 運用補助ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード等）

---

## 機能一覧

- 監視（monitoring）
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID ファイル・データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクイベント記録
  - KillSwitch: 条件により ExecutionEngine 停止フラグ（data/kill.flag）を書き込み
  - AlertManager: LINE Push による通知（トークン未設定時はログ出力）
  - Streamlit ベースの監視ダッシュボード（読み取り専用で SQLite を参照）

- 実行（execution）
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアントのファクトリ（paper_trading 環境では MockBrokerClient を使用）
  - 起動時のリコンシリエーション（Reconciler）による注文・ポジション同期
  - RiskManager による各種取引規制（ポジション上限、利用率等）

- 研究（research）
  - ファクター計算: momentum / volatility / value
  - 特徴量探索: 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - DuckDB を用いた高速な時系列集計

- ポートフォリオ（portfolio）
  - 候補選定（score 降順）、等配分 / スコア加重配分
  - セクター制約の適用（apply_sector_cap）
  - ポジションサイズ計算（risk_based / equal / score）および単元株（lot）丸め、aggregate cap のスケーリング

- AI（ai）
  - ニュース記事をまとめて OpenAI（gpt-4o-mini）に投げ、銘柄毎のセンチメントを ai_scores に書き込む
  - レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメントで bull/neutral/bear を判定）
  - API 呼び出しはリトライ・バックオフを行い、失敗時はフォールバックして継続する実装

- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

---

## 要求環境 / 依存パッケージ（代表）

- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit（ダッシュボード利用時）
- （標準ライブラリ）sqlite3, logging, datetime, os 等

※ 実際の requirements.txt がない場合は上記パッケージをインストールしてください。バージョンは利用環境に合わせて調整してください。

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリルートに移動し、仮想環境を作成して有効化する（推奨）。
2. 依存パッケージをインストールする（上記参照）。
3. 環境変数を設定する（.env / .env.local をプロジェクトルートに置けます。自動ロードを行います）。
   - 自動ロードはデフォルトで有効。無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
4. 必要に応じて data ディレクトリを作成する:
```
mkdir -p data
```
5. SQLite / DuckDB のデフォルトパス（存在しない場合は起動時に作成されます）:
   - data/monitoring.db（SQLite: monitoring 用）
   - data/paper_trading.db（paper_trading 用、Paper Trading 環境）
   - data/kabusys.duckdb（DuckDB: 価格・ファクター等）

---

## 主要な環境変数

（Settings クラスに定義されている主要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector 利用時に必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。既定は development。
  - paper_trading の場合、発注は MockBrokerClient を使用し、Paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む。
- PAPER_FILL_MODE — paper_trading 時の成行処理等（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動消去するか（"1"なら消去）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE通知）用（未設定時は送信せずログ出力）

簡易 .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 使い方（起動コマンド例）

※ パッケージがソースツリー下の `src` にある構成を想定。モジュールとして実行する際は PYTHONPATH に src を含める必要があります（またはパッケージとしてインストールしてください）。

一般的な方法:
```
# プロジェクトルートから
PYTHONPATH=src python -m kabusys.run_monitoring
PYTHONPATH=src python -m kabusys.run_execution
```

1) 監視ループを起動（Monitoring）
```
# ポーリング間隔を 30 秒に上書きする例
MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
```
- run_monitoring は起動時にプロセス優先度を "high" に試みます（psutil を使用）。
- monitoring は Settings.env にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを永続化します。
- Ctrl+C（KeyboardInterrupt）で終了します。

2) 実行エンジンを起動（Execution）
```
# 本番 / 開発で通常実行
PYTHONPATH=src python -m kabusys.run_execution

# Paper Trading（MockBroker を使用）で起動する例
KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
```
- paper_trading 環境では専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- 起動時に Reconciler による同期（未確定注文の照合など）を実行します。
- プロセス優先度を "high" に設定しようとします（権限がない場合は警告でスキップ）。

3) Paper Trading 検証レポート生成（ツール）
```
PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB は data/paper_trading.db。--db で指定可能
```

4) Streamlit ダッシュボード（監視）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- `--` の後に script へ渡す引数（--db）を指定します。
- ダッシュボードは読み取り専用で監視用 SQLite を参照します（read-only URI で接続）。

5) AI 周りの関数呼び出し（ライブラリから直接利用）
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

いずれも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

---

## 注意点 / 運用メモ

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env → .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- プロセス優先度・CPU affinity:
  - set_process_priority() / set_cpu_affinity() は psutil を使用します。権限不足や未対応 OS の場合は警告が出て設定はスキップされます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使用し Paper 専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と完全分離されます。
- Kill Switch:
  - RiskMonitor 等がトリガーした場合、KillSwitch が data/kill.flag を作成して ExecutionEngine 停止の合図を送ります。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にフラグを消去します（必要に応じて運用ルールを定めてください）。
- DB マイグレーション:
  - init_monitoring_db() は起動時に呼ばれ、必要なテーブルやカラム（例: trade_logs.latency_ms, dashboard.peak_value）を冪等に作成・追加します。
- OpenAI 利用:
  - ニュース NLP / レジーム判定は OpenAI を使います。API レスポンスのパースや API エラー時のフォールバックが組み込まれていますが、API キーの管理やコストに注意してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス（主要設定項目）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視データ永続化層（init / MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — Monitor を束ねるエンジン（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - reconciler.py — 起動時の注文・ポジション再照合ロジック
    - order_manager.py — 注文状態遷移外向け API
    - order_repository.py, order_record.py, broker_* 等 （発注ロジック周り）
    - execution_engine.py, broker_factory.py, risk_manager.py 等（実行系）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 等配分 / スコア配分
    - position_sizing.py — 株数決定ロジック（単元丸め、aggregate cap）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュース集約 → OpenAI でセンチメント → ai_scores に書き込み
    - regime_detector.py — MA200 + マクロセンチメントでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI

（上記は主要ファイルの抜粋と要約です。細かなユーティリティや補助モジュールも多数含まれます。）

---

この README はソースコードの注釈・実装内容に基づいて作成しています。実際の運用では、環境変数や API キーの管理、DB のバックアップ、監視・通知ポリシーを組織ルールに従って設定してください。追加の操作手順やデプロイ方法（systemd ユニット、Docker コンテナ化など）を希望される場合は、その要件に合わせたドキュメントを追記できます。