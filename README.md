# KabuSys

日本株向けの自動売買・研究プラットフォーム（軽量プロトタイプ）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算／研究、ポートフォリオ構築、LLM を用いたニュース NLP 等のユーティリティ群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような目的を想定したモジュール群です。

- 発注ロジックの実行（kabuステーションなどのブローカーと連携）
- 実行状況・システム状態の監視とアラート（Kill Switch を含む）
- DuckDB を使ったデータ分析・ファクター計算（研究用）
- Paper Trading（本番 DB と分離された SQLite）向け検証ツール
- OpenAI（GPT 系）を使ったニュースセンチメント評価 / レジーム判定

設計方針の一部：
- 環境変数 / .env による設定管理（`kabusys.config`）
- 各種長時間プロセスはプロセス優先度を高めに設定
- Paper Trading は本番 DB と分離（別 SQLite）
- 監視系は本番の monitoring DB を参照（環境に依らず本番 sqlite_path を使用）

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine による注文の発行 / マネージメント
  - Paper Trading 用の MockBrokerClient サポート（`KABUSYS_ENV=paper_trading`）
  - 発注ログを SQLite（paper または production）に記録
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、プロセス生存確認
  - TradeMonitor / RiskMonitor：滞留注文・ドローダウン等の監視
  - MonitoringEngine：複数モニタの統合ポーリングと Kill Switch 評価
  - `data/kill.flag` による ExecutionEngine 停止シグナル
- Portfolio（銘柄選定・配分）
  - 候補選定・スコア重み・等配分・リスクベースのポジションサイズ計算
  - セクター上限やレジーム乗数の適用
- Research（研究）
  - DuckDB を使ったファクター計算（Momentum, Volatility, Value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI 統合）
  - ニュース記事を LLM でスコアリングし `ai_scores` に書き込む（`kabusys.ai.news_nlp`）
  - マクロニュースと ETF の MA を組合せた市場レジーム判定（`kabusys.ai.regime_detector`）
- ツール
  - 設定ウィザード（`.env` の対話的作成）：`kabusys.config_setup`
  - 設定検証 CLI：`kabusys.validate_config`
  - Paper Trading 検証レポート生成：`kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発環境向け）

1. Python（推奨: 3.10+）環境を用意します。

2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（requirements.txt がある想定、なければ主要依存を個別インストール）：
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML  （設定検証で YAML 内容チェックを行いたい場合）

   ※ SQLite は標準ライブラリに含まれます。

4. プロジェクト直下に `data/` と `logs/` ディレクトリを作成（設定次第で自動作成されますが事前作成推奨）：
   - mkdir -p data logs

5. .env を作成する：
   - 対話式で作る: python -m kabusys.config_setup
   - または `cp .env.example .env` を編集（必要な環境変数は下記参照）

6. 設定検証を実行：
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

7. （OpenAI を使う機能を使う場合）環境変数 `OPENAI_API_KEY` を設定。

---

## 主要環境変数（要約）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要なもの（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使用する際に必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

Kill / stop フラグ:
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine に停止指示）
- data/stop_requested.flag — run_monitoring / run_execution のローカル停止フラグ

その他:
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（開発用、0/1）

---

## 使い方（コマンド例）

プロジェクトのルートで以下のコマンドを実行します（仮想環境を有効にしている前提）。

- 設定ウィザード（.env の生成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、`data/paper_trading.db` に記録されます。
  - Execution 起動時に `data/stop_requested.flag` が存在すると起動しません。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視プロセスは KABUSYS_ENV に関わらず production の sqlite_path（`SQLITE_PATH`）を使用します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI / レジーム判定・NLP（ライブラリ関数として利用）:
  - 例: Python REPL で DuckDB 接続を渡して利用
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

注意:
- 実運用で `KABUSYS_ENV=live` を使う場合は設定（特に API 系・kill flag 等）を慎重に確認してください。

---

## ロギング / PID / 優先度

- ログ: `kabusys.utils.logging_setup.setup_logging` により
  - stdout（StreamHandler）と `logs/<app_name>.log`（日次ローテーション）に出力
  - LOG_DIR 環境変数でログ出力先を上書き可能
- PID ファイル:
  - ExecutionEngine はデフォルトで `data/execution.pid` を使用（Settings.pid_file_path）
- プロセス優先度:
  - 起動スクリプトは起動時にプロセス優先度を "high" に設定します（プラットフォーム依存、`psutil` を使用）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / .env の自動読み込みと Settings クラス
  - config_setup.py       — .env 対話式ウィザード
  - validate_config.py    — 設定検証 CLI
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py    — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py    — SQLite テーブル初期化・永続化層
    - system_monitor.py   — システム状態・データ鮮度チェック
    - risk_monitor.py     — ドローダウン・ポジション上限監視
    - kill_switch.py      — kill.flag の読取/書込ユーティリティ
    - monitoring_engine.py— 各 Monitor を束ねるエンジン
    - ...（TradeMonitor 等が存在）
  - execution/
    - (ブローカー・エンジン用のモジュール群)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py         — ニュース NLP（OpenAI を使用したスコアリング）
    - regime_detector.py  — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py

注意: 上記は主なファイルの抜粋です。各ディレクトリにさらに補助モジュールがあります。

---

## 開発上の注意 / 運用メモ

- 監視（Monitoring）は常に production の監視 DB を参照します（KABUSYS_ENV に依存しません）。
- Paper Trading は SQLite を分離しているため、本番データと混ざりません。`KABUSYS_ENV=paper_trading` を使用。
- `.env` は機密情報を含むため Git にコミットしないこと（`config_setup.py` のヘッダにも注意書きあり）。
- OpenAI API を使う処理はネットワークエラー / 429 / 5xx に対して指数バックオフでリトライする実装が入っていますが、API 利用に伴うコストとレート制限に注意してください。
- Kill Switch（`data/kill.flag`）は本番で非常に強力な操作なので、`KILL_FLAG_CLEAR_ON_START` の値は本番では 0 を推奨します。
- DuckDB の操作はローカルファイルに対する排他等の運用注意が必要です（複数プロセスでの同時書き込み等）。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視エンジン起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載してほしい追加情報や、運用手順（systemd / Supervisor 用のサービス定義例や具体的な .env.example の追記など）があれば教えてください。必要に応じてサンプル systemd ユニットやデプロイ手順を作成します。