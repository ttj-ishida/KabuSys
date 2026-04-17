# KabuSys

日本株向けの自動売買システムのコードベース（ライブラリ＋CLI）。  
本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB を用いたファクター計算）、および AI を使ったニュース解析機能を含みます。

> バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

KabuSys は次を目的としたコンポーネント群を提供します：

- 発注ロジックを含む ExecutionEngine（本番 / ペーパートレード分離）
- 稼働状況・注文状況・リスク監視のポーリング（Monitoring）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限等）
- DuckDB を用いたリサーチ／ファクター計算モジュール
- OpenAI を使ったニュース NLP（銘柄ごとのセンチメント算出）および市場レジーム判定
- ユーティリティ群（.env ウィザード、設定検証、プロセス優先度設定など）
- ペーパートレード用の検証レポート生成ツール

設計上、安全性のためにペーパートレード時は発注（Broker）をモックし、本番 DB と完全分離します。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（環境変数・config/*.yaml 検査）: kabusys.validate_config
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス状態、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視、ダッシュボード更新）
  - KillSwitch（危険トリガで data/kill.flag を作成 → ExecutionEngine を停止）
  - AlertManager（LINE Push による通知、クールダウン管理）
- Execution
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）
  - OrderManager、OrderRepository、RiskManager、Reconciler 等（発注管理）
- Portfolio（純粋関数）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- Research（DuckDB）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC、統計サマリ等
- AI
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント算出（ai_scores へ書込）
  - regime_detector: ETF(1321) の MA とマクロニュースの LLM 判定を合成して市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - （任意）PyYAML（config YAML 検証時）
- SQLite（標準ライブラリに含まれます）

package のインストールはプロジェクト側で requirements.txt がある場合はそちらを利用してください。なければ以下のように個別にインストールします例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests PyYAML
```

---

## セットアップ手順

1. リポジトリをチェックアウトする
2. 仮想環境を作成・有効化して依存パッケージをインストール
3. 環境変数を用意する（.env ファイル推奨）

推奨：対話式ウィザードで .env を作成

```
python -m kabusys.config_setup
```

ウィザードは J-Quants トークンや kabuステーション API パスワードなどの必須項目を入力して .env を生成します。

4. 設定検証

```
python -m kabusys.validate_config
# 警告もエラーとして扱う場合:
python -m kabusys.validate_config --strict
```

5. DB 初期化は各コンポーネント起動時に自動で行われます（monitoring DB のテーブル作成等）。

---

## 環境変数（主要なもの）

以下はコード内で参照される主な環境変数とデフォルト（存在する場合）：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager 用)
- KABUSYS_ENV: one of development, paper_trading, live (デフォルト: development)
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
- PAPER_FILL_MODE: instant|partial|never|reject (デフォルト: instant)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1, デフォルト 0) — Execution 起動時に kill flag を自動クリアするか
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60

注意: Settings モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor 単体のデーモン的起動）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視プロセスは data/stop_requested.flag が置かれると終了します（停止制御）。

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を使うとペーパートレードモードになり、専用の SQLite（PAPER_TRADING_SQLITE_PATH, default data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 実行中は data/execution.pid に PID が書き込まれ、停止は data/stop_requested.flag を作るか、監視側の kill.flag（data/kill.flag）で行います。

- Paper Trading 検証レポート（SQLite DB を読みレポート出力）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db path/to/paper_trading.db
  ```

- AI 関連（スクリプト化された関数を呼ぶ）
  - news NLP（例: 日次で target_date のニュースを評価して ai_scores に書き込む）
    - 必要: OPENAI_API_KEY
    - 実行例（スクリプトから関数呼び出し）:
      ```
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news

      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 10), api_key="sk-...")
      ```
  - regime_detector 同様に OPENAI_API_KEY を要します。

---

## 停止・安全機構

- stop_requested.flag
  - run_monitoring / run_execution がチェックする停止フラグ: data/stop_requested.flag
  - このファイルが存在するとポーリングループの終了処理が行われます。

- kill.flag
  - KillSwitch が作成するファイル（data/kill.flag）。ExecutionEngine に対する緊急停止命令を表します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にこれを自動クリアします（本番では推奨しません）。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル / モジュールの一覧（src/kabusys 以下）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 + MonitoringDB ラッパ
    - system_monitor.py      — システム監視
    - trade_monitor.py       — 注文監視
    - risk_monitor.py        — リスク監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — LINE Push 通知
    - kill_switch.py         — KillSwitch ロジック
  - execution/                — Execution 関連（OrderManager 等）（一部実装は省略）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py

（実際のリポジトリにはさらに細かいモジュール・補助ファイルがあります）

---

## データベース（デフォルトパス）

- DuckDB: data/kabusys.duckdb
  - リサーチ / ファクター計算や raw_news / prices_daily 等のテーブルを想定
- SQLite (monitoring): data/monitoring.db
  - MonitoringDB が管理するテーブル群（system_status, trade_logs, positions, risk_logs, dashboard）
- SQLite (paper trading): data/paper_trading.db （ペーパートレード時に使用）

MonitoringDB は起動時にテーブルを自動作成（冪等）し、必要があれば簡単なマイグレーション（カラム追加）も行います。

---

## 注意事項 / 開発者向けメモ

- KABUSYS_ENV を `live` に設定すると本番モードになります。LINE 通知や Kill Switch の挙動、DB の取り扱い等に注意してください。
- OpenAI を使う機能は API キーが必須で、レート制限・エラーを考慮したリトライロジックがあります。API コストに注意してください。
- ペーパートレードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- Settings モジュールはプロジェクトルートの `.env` / `.env.local` を自動ロードします。環境変数による上書きや自動読込無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。
- process_priority の設定は psutil に依存し、一部 OS では権限不足で失敗する可能性があります（警告のみ出力し継続）。

---

もし README に追記してほしい具体的な情報（例: 実行例のログ、設定ファイルテンプレート、CI/CD 手順、モジュール間の詳細な依存図など）があれば教えてください。必要に応じて README を拡張します。