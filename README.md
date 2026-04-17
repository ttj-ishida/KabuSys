# KabuSys

日本株向けの自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
本リポジトリには、注文実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、
LLM を用いたニュースセンチメント評価など、バックテスト・運用に必要な主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 注文の生成・送信・状態管理（ExecutionEngine, OrderManager, BrokerClientFactory 等）
- 実行・監視の分離（Execution と Monitoring の別プロセス／DB）
- 監視ログの蓄積とアラート（SQLite ベースの monitoring DB, LINE 通知）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・リスク調整）
- リサーチ／ファクター計算（DuckDB を用いた prices_daily / raw_financials の解析）
- LLM を用いたニュースセンチメント・レジーム判定（OpenAI API）
- 運用ユーティリティ（Streamlit ダッシュボード、Paper Trading 検証レポート生成 等）

設計上の特徴：
- monitoring 用の SQLite は運用環境に依らず本番の sqlite_path を使用（監視は本番状態を前提）
- paper_trading モードでは実行系の DB が分離され、実際のブローカー呼び出しはモック化される
- .env / .env.local を自動読み込み（環境変数が優先）。自動読み込みを無効化するフラグあり

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine：注文生成・送信・状態遷移管理
  - Reconciler：起動時のリコンシリエーション（注文・ポジションの突合）
  - RiskManager：注文リスク制御（設定に基づく制限）
- Monitoring
  - SystemMonitor：CPU／メモリ／ディスク／プロセス状態／データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウンやポジション上限の監視
  - KillSwitch：閾値超過時に flag ファイルを書いて Execution を停止
  - AlertManager：LINE 通知の送信（クールダウン管理あり）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定（スコア順）、等重・スコア重み付け、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（単元株丸め・aggregate cap のスケーリング）
- Research
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI / NLP
  - news_nlp: raw_news をまとめて OpenAI（gpt-4o-mini 等）に送信し銘柄ごとのスコアを ai_scores に書込
  - regime_detector: ETF MA200 乖離＋マクロニュースの LLM 評価で市場レジームを判定。結果を market_regime に保存
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ等）
  - streamlit_dashboard: 監視 DB を参照するリアルタイムダッシュボード

---

## 要件（推奨）

- Python 3.10+
- SQLite（標準ライブラリ）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- OS: Linux / macOS / Windows（psutil によりプロセス優先度設定の差異を吸収）

（実際の requirements.txt がある場合はそちらを使用してください）

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。  
自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（抜粋）：

- 必須（機能を使う場合）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API 用
- AI 関連
  - OPENAI_API_KEY — OpenAI API を使う場合に必要
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- 実行モード
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- ロギング
  - LOG_LEVEL — DEBUG, INFO, ...
- モック・paper 設定
  - PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 時の約定モード）
- 監視設定（例）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## セットアップ手順（簡易クイックスタート）

1. リポジトリをクローンし、仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # ある場合
   # または最低限:
   pip install duckdb psutil requests openai streamlit
   ```

2. .env を作成（.env.example を参照）  
   例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

3. data ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   # 監視 DB / paper DB は起動時に自動で初期化されるため空ファイルは不要
   ```

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading（本番 DB と分離）
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    paper_trading 時は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録される。

  - 本番または開発
    ```bash
    export KABUSYS_ENV=development  # または live
    python -m kabusys.run_execution
    ```

  - 注意: エンジン起動時に `data/execution.pid` を利用・更新します。停止は `data/stop_requested.flag` / `data/kill.flag` を使用して制御します。

- 監視ループを起動
  ```bash
  # ポーリング間隔を変更したい場合
  export MONITOR_POLL_INTERVAL=30  # 秒
  python -m kabusys.run_monitoring
  ```
  監視プロセスはモニタリング用 SQLite（settings.sqlite_path）を使用してログを蓄積します。`MONITOR_POLL_INTERVAL` は 1 秒以上の正の整数で指定します。

- Streamlit ダッシュボード（監視可視化）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db PATH で DB を指定可能
  ```

- AI / レジーム判定（プログラムから呼ぶ例）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

---

## 運用メモ / ファイル・フラグ

- data/execution.pid — ExecutionEngine が書き込む PID ファイル。SystemMonitor はこのファイルを参照してプロセス生存を確認。
- data/stop_requested.flag — run_execution / run_monitoring の停止監視に使われるフラグファイル（存在を検出するとループを終了）。
- data/kill.flag — KillSwitch が書き込む停止理由ファイル。存在すると Execution を停止させるための信号。
- 監視 DB（デフォルト data/monitoring.db）は init_monitoring_db により起動時に必要なテーブルが作成されます（冪等）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動読み込み 等）
- run_execution.py — ExecutionEngine のエントリポイント
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト
- ai/
  - news_nlp.py — ニュース → LLM による銘柄センチメントスコア化
  - regime_detector.py — レジーム判定（MA200 + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE 通知送信
  - monitoring_engine.py — 各 Monitor を束ねる実行ロジック
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ... — 注文周りのロジックと同期処理
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み付け
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum / volatility / value）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください）

---

## 開発 / テストのヒント

- Settings は .env 自動読み込みを行いますが、ユニットテスト等で自動ロードを防ぎたければ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使う機能は API キーが未設定だと例外を投げる箇所があります（score_news / score_regime）。テストでは _call_openai_api を patch して外部 API 呼び出しをモック化してください。
- DuckDB を使ったリサーチ系は prices_daily / raw_financials 等のテーブルを前提としています。ローカル検証用に DuckDB に適切なテーブルを用意してください。

---

必要に応じて README を拡張します（例：依存パッケージの正確なバージョン、開発フロー、CI 設定、デプロイ方法、詳細な環境変数ドキュメントなど）。必要なセクションがあれば指示してください。