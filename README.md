# KabuSys

日本株自動売買システムのコードベース（ライブラリ + 実行スクリプト群）。

このリポジトリは、戦略の調査（research）、ポートフォリオ構築（portfolio）、実行（execution）、監視（monitoring）、および AI を使ったニューススコアリング（ai）などを含むモジュール群で構成されています。

---

## 概要

KabuSys は以下を提供します。

- 株価データ（DuckDB）を用いたファクター計算・研究ツール
- ポートフォリオ構築（候補選定・重み計算・株数算出）
- 注文発行・状態管理・再起動時のリコンシリエーション（ExecutionEngine）
- 実行と運用を支える監視基盤（System / Trade / Risk Monitor）、アラート（LINE）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- Streamlit ベースの監視ダッシュボード

---

## 主な機能一覧

- research:
  - ファクター（モメンタム／バリュー／ボラティリティ）計算
  - 将来リターン・IC・統計サマリー等の解析ユーティリティ
- portfolio:
  - 候補選定（スコア順）/ 等金額・スコア加重配分 / リスク調整（セクター上限・レジーム乗数）
  - 株数決定（risk_based / equal / score）と単元丸め・aggregate cap
- execution:
  - OrderManager（注文作成・送信・同期）
  - Reconciler（注文・ポジションの起動時リコンシリエーション）
  - Broker クライアント工場（本番 / mock 切替）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログを永続化する SQLite 層（monitoring_db）
  - KillSwitch（条件を満たしたら data/kill.flag を書き込み Execution 停止）
  - AlertManager（LINE Push 通知）
  - Streamlit ダッシュボード（read-only 接続）
- ai:
  - ニュースを LLM でスコア化（ai_scores テーブルへ保存）
  - 市場レジーム判定（ma200 とマクロニュースの LLM 評価の合成）
- tools:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提 / 必要なソフトウェア

- Python 3.10+
- SQLite （標準で同梱されます）
- 外部パッケージ（少なくとも以下が必要）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt があればそれを使ってください）

---

## 環境変数と設定

設定は環境変数（またはプロジェクトルートの `.env` / `.env.local`）から読み込みます。自動読み込みはデフォルトで有効です（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

主に使用される環境変数（一部）:

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker fill 動作（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行管理・停止フラグ設定
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、run_monitoring で上書き可）

設定内容は `kabusys.config.Settings` を参照してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を準備
2. 必要パッケージをインストール（上記参照）
3. プロジェクトルートに `data/` ディレクトリを作成（DB・PID・flag を置く場所）
   ```bash
   mkdir -p data
   ```
4. `.env` を作成して必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定
5. DuckDB / SQLite の初期テーブルは各スクリプトが必要に応じて初期化します。監視 DB の初期化は `init_monitoring_db()` が実行されます。

---

## 使い方（主要な実行例）

- 監視ループの起動（SystemMonitor を周期実行し SQLite にログ保存）:

  ```bash
  # モジュールとして直接実行
  python -m kabusys.run_monitoring
  # または
  python src/kabusys/run_monitoring.py
  ```

  - ポーリング間隔を変更する場合:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視プロセスは内部で常に本番用の sqlite_path を使用する点に注意（monitoring は環境に関係なく Settings.sqlite_path を参照）。

- 実行エンジン（ExecutionEngine）の起動:

  ```bash
  python -m kabusys.run_execution
  # または
  python src/kabusys/run_execution.py
  ```

  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行中の停止はプロジェクトルートの `data/stop_requested.flag` を作成すると安全に停止処理されます。
  - KillSwitch（リスクトリガー）による停止シグナルは `data/kill.flag` が書き込まれることで発行されます。

- Streamlit ダッシュボード（監視 DB を読み取り専用で表示）:

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポートの生成:

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（ニューススコアリング / レジーム判定）を Python API として使う例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, date(2026, 4, 10), api_key="sk-...")
  r = score_regime(conn, date(2026, 4, 10), api_key="sk-...")
  ```

  - OpenAI API キーが未設定の場合、これらの関数は ValueError を投げます。

---

## 停止とフラグ

- 実行スクリプトは以下のフラグファイルを監視します:
  - data/stop_requested.flag: run_monitoring / run_execution のループ停止トリガー（手動停止用）
  - data/kill.flag: KillSwitch が書き込む停止指示（運用上の自動停止）
- `KILL_FLAG_CLEAR_ON_START=1` を Settings に設定すると、Execution 起動時に既存の kill.flag を自動で削除できます（設定により挙動を変えられます）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                    — ニュースの LLM スコアリング
    - regime_detector.py             — 市場レジーム判定
  - research/
    - factor_research.py             — ファクター計算
    - feature_exploration.py         — 将来リターン / IC / 統計
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数計算・スケーリング
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - execution/
    - order_manager.py               — 発注・状態管理
    - reconciler.py                  — 起動時リコンシリエーション
    - ...（Broker API / リポジトリ等）
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py              — システム・データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定異常監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - monitoring_engine.py           — 各 Monitor を束ねる
    - kill_switch.py                 — kill.flag 書き込みロジック
    - alert_manager.py               — LINE プッシュ通知
    - streamlit_dashboard.py         — 監視ダッシュボード（Streamlit）
  - utils/
    - process_priority.py            — プロセス優先度・CPU affinity ユーティリティ

（上は主要モジュールの抜粋です。実際のリポジトリにはさらに補助モジュールやテストが含まれる可能性があります。）

---

## 運用上の注意点

- Monitoring は本番用 sqlite_path を参照するため、監視 DB を運用データと誤って混在させないでください。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_sqlite_path を使用して本番 DB と分離される設計です。必ず環境変数を正しく設定してください。
- OpenAI（LLM）を使う処理は API コストやレート制限の影響を受けます。API キーの管理とレート制御に注意してください。
- process priority / cpu affinity の設定は OS により権限が必要な場合があります。権限不足時は警告が出てスキップされます。
- SQLite / DuckDB のファイルパスは環境変数で変更可能です。バックアップやパーミッションに注意してください。

---

## さらなる情報

- 詳細実装や設計方針・数式等は各モジュールの docstring やコメントに記載されています。まずは `kabusys/config.py` と `kabusys/monitoring/monitoring_db.py`、`run_execution.py` / `run_monitoring.py` を読むことを推奨します。

---

もし README に追加したい内容（例: デプロイ手順、CI、テスト実行方法、requirements.txt 生成など）があれば教えてください。必要に応じてサンプル .env.example も作成できます。