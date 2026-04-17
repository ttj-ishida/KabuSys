# KabuSys README

日本株自動売買システムのコードベース README（日本語）

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（実行コマンド例）
- 環境変数 / 設定項目
- 停止・フラグ制御
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。戦略（ファクター計算・シグナル生成）・ポートフォリオ構築・発注エンジン・モニタリング・ツール（検証レポート、ダッシュボード）や、ニュースを用いた AI スコアリング等を含むモジュール群で構成されています。

設計上の特徴：
- DuckDB を用いた履歴データの分析（prices_daily / raw_financials 等）
- SQLite による監視・発注ログ保存（monitoring.db / paper_trading.db）
- Paper Trading（環境分離）をサポート
- OpenAI を用いたニュース NLP（gpt-4o-mini を想定）
- モジュールは純粋関数・DB 分離でテストしやすい実装

---

## 主な機能一覧

- ポートフォリオ構築
  - 銘柄候補選択（スコア順）
  - 等重・スコア重み付け
  - セクター上限適用、レジーム乗数適用
  - 発注株数計算（リスクベース、単元丸め、aggregate キャップ）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上）
  - 将来リターン、IC（情報係数）、統計サマリ等のユーティリティ

- 発注・実行
  - ExecutionEngine（ブローカークライアント経由で発注）
  - OrderManager / OrderRepository / Reconciler による状態管理と再同期

- 監視
  - SystemMonitor（CPU/メモリ/ディスク、PID、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - MonitoringEngine（各監視の統合ポーリング）
  - AlertManager（LINE push による通知）
  - streamlit ベースの監視ダッシュボード

- AI（ニュース）
  - news_nlp.score_news：raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を作成
  - regime_detector.score_regime：ETF の MA200 乖離とマクロニュース（LLM）を合成して市場レジーム判定

- ツール
  - paper_verification_report：Paper Trading DB から検証レポートを出力

---

## セットアップ手順（開発環境向け）

前提：
- Python 3.10+ を想定（型ヒントに union 型や typing の利用あり）
- SQLite は標準ライブラリ、外部依存パッケージは以下

主な依存（例）：
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)

インストール例（仮に venv を使用する場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests openai streamlit
```

.env ファイル:
- リポジトリルートに `.env.example` がある想定のもと、`.env` を作成してください。
- 環境変数は `Settings` クラスで読み込まれます。自動ロードはデフォルトで有効（プロジェクトルートに .git または pyproject.toml があれば読み込む）。
- 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（実行するコンポーネントにより異なる）：
- JQUANTS_REFRESH_TOKEN （J-Quants を使用する機能がある場合）
- KABU_API_PASSWORD （kabu API を使う場合）
- OPENAI_API_KEY（AI 機能を使う場合）
- その他、`.env` 内の説明に従って設定してください。

データディレクトリ:
- デフォルトの DB や PID/flag は `data/` 配下に作られます（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）。

---

## 使い方

主要な実行スクリプトとオプション例：

1. 監視ループを起動（SystemMonitor を継続ポーリング）
```bash
# 環境変数でポーリング間隔を変更可能（秒）
export MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
```
- 補足:
  - MONITOR_POLL_INTERVAL（デフォルト 60 秒）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します
  - 停止はプロジェクトルート `data/stop_requested.flag` を作成すると検知して終了します

2. ExecutionEngine（発注エンジン）を起動
```bash
# Paper Trading 環境にしたい場合:
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- 補足:
  - KABUSYS_ENV: development | paper_trading | live（Settings.env）
  - paper_trading の場合は MockBroker を使用し、データは `data/paper_trading.db`（Settings.paper_sqlite_path）に分離されます
  - エンジンは起動時に `data/execution.pid` を作成し、停止は `data/stop_requested.flag` を作成して検知します

3. Paper Trading 検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB は data/paper_trading.db。--db で変更可能。
```

4. Streamlit ダッシュボード（監視）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

5. AI 関連（ライブラリ API として）
- ニューススコアを生成して ai_scores テーブルに書き込む:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（関数引数で渡すことも可能）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数 / 設定（主なもの）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。Settings.env で検証される。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト data/monitoring.db）。
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）。
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）。
- PAPER_FILL_MODE: paper_trading の MockBroker の fill mode（instant|partial|never|reject）。不正値は例外。
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）。
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用。Settings で必須チェックされるプロパティがある。

その他 Settings で多くの閾値とパスを提供しています（log_level、pid_file_path、kill_flag_path、cpu_threshold_pct 等）。

---

## 停止・フラグ制御

- グローバル停止フラグ:
  - ファイル: project_root/data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を検知して安全に終了します。

- Kill Switch（ExecutionEngine に停止指示を出す）:
  - ファイル: Settings.kill_flag_path（デフォルト data/kill.flag）
  - KillSwitch はリスク条件を満たすとこのファイルを書き込みます。ExecutionEngine はこの flag を参照して停止します。
  - KillSwitch.clear() で削除可能（起動時のクリーンアップに使用）

- PID 管理:
  - Execution 起動時に pid ファイル（data/execution.pid）を作成します。SystemMonitor は PID を監視し stale（存在しない PID）なら削除してアラートを出します。

---

## 開発者ノート / 実装上のポイント

- Settings モジュールはプロジェクトルートを自動検出し `.env` / `.env.local` を自動ロードします（無効化可）。
- monitoring_db.init_monitoring_db は冪等で実行可能。既存 DB が古いスキーマを持つ場合は必要なカラム追加マイグレーションを行います。
- AI モジュールは OpenAI の API 呼び出しをラップし、429/タイムアウト/5xx に対して指数バックオフを実装しています。API キーは関数引数でも渡せます。
- process priority / CPU affinity は `psutil` を用いて OS 別に差分を吸収します（utils/process_priority.py）。
- DuckDB クエリは prices_daily / raw_financials / raw_news などを利用するため、データの投入（ETL）は別途必要です（data.pipeline 等参照）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（Settings）
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — monitoring DB レイヤ（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー / engine / repository 実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (想定: ETL / pipeline 実装はここに関連)
  - tools/
    - paper_verification_report.py

（上記は主要ファイルを抜粋した一覧です。詳細はソースを参照してください。）

---

## よくある操作例

- 監視をデバッグ的に一度だけ回す（テスト）:
  - MonitoringEngine をテスト用にインスタンス化して run_once() を呼ぶ（テストコード内で直接利用）

- Paper Trading レポート出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば、セットアップのための requirements.txt の例や、.env.example の雛形、起動スクリプトの systemd ユニット例、CI 用のテスト実行手順なども作成します。どの情報を追加したいか教えてください。