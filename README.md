# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。  
このリポジトリは注文管理、リコンシリエーション、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用したセンチメント）、および運用監視機能を含みます。

## 主な特徴
- 注文ライフサイクル管理 / ブローカー抽象化（Execution）
- 起動時リコンシリエーション（Reconciler）で安全に復旧
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リスク調整（セクター上限、レジーム乗数）
- 定量ファクター計算（Momentum, Volatility, Value）および研究ユーティリティ（IC, forward returns 等）
- ニュースのLLM（OpenAI）による銘柄センチメント評価（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 監視（System / Trade / Risk）、LINE 通知、kill.flag による停止制御
- Streamlit ベースの監視ダッシュボード
- Paper Trading 用の分離された SQLite DB と検証レポートツール

---

## 構成（短い説明）
- src/kabusys/config.py — 環境変数 / .env の自動読込と Settings
- src/kabusys/execution — 注文発行・管理・リコンシリエーション関連
- src/kabusys/portfolio — 銘柄選定・重み・ポジションサイズ計算
- src/kabusys/research — ファクター計算 / 研究用ユーティリティ
- src/kabusys/ai — OpenAI を使ったニューススコア & レジーム判定
- src/kabusys/monitoring — 監視・アラート・kill switch・Streamlit ダッシュボード
- src/kabusys/tools — 運用向けユーティリティ（例: paper_verification_report）
- src/kabusys/utils — プロセス優先度 / CPU affinity 等ユーティリティ

---

## 要件（例）
Python 3.9+ を想定。主要依存パッケージ（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit

pip でインストールする場合の例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```
（実際は requirements.txt があればそちらを使用してください）

---

## 環境変数 / .env
プロジェクトはルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定時は送信をスキップ）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject。デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KABUSYS_ENV — 実行環境（development | paper_trading | live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...。デフォルト: INFO）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

注意:
- `.env.local` は `.env` の上書き（優先）に使われます。
- OS 環境変数は .env の上書き対象から保護されます。

---

## セットアップ手順（概要）
1. リポジトリをクローン
2. Python 仮想環境を作成して activate
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（.env.example を参考に）
5. データディレクトリを作成:
   ```
   mkdir -p data
   ```
6. DuckDB / SQLite の初期化は各スクリプトが自動で実行します（init_monitoring_db 等）。

---

## 使い方・実行例

- 実行エンジン（発注処理）を起動:
  - 本番/開発:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading（環境を分離して動作）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  Paper Trading 時は MockBrokerClient を使い、データは `data/paper_trading.db` に保存されます。

- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書きできます（秒、デフォルト 60）。例:
  ```
  export MONITOR_POLL_INTERVAL=30
  ```

- Streamlit ダッシュボードを起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB パスを指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 部分（ニューススコア / レジーム判定）:
  - OpenAI API キーを設定した上で、モジュール関数をプログラムから呼び出せます（例）:
    ```py
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    # duckdb_conn: duckdb.connect("data/kabusys.duckdb")
    # score_news(duckdb_conn, target_date, api_key="...")
    # score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - API キー未設定時は例外が発生します（明示的にチェックしてください）。

- 研究用関数:
  - ファクター計算や IC 計算は `kabusys.research` 経由で利用可能です。
    例:
    ```py
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026, 4, 1))
    fwd = calc_forward_returns(conn, date(2026, 4, 1), horizons=[1,5,21])
    ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
    ```

---

## 運用上の注意
- 監視（Monitoring）は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。Paper Trading を使用する場合でも監視 DB は本番 DB を参照する挙動に注意してください（run_monitoring の実装参照）。
- ExecutionEngine 起動時は PID ファイル（デフォルト data/execution.pid）を書きます。kill.flag（data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送ります（KillSwitch）。
- Paper Trading は本番 DB と完全に分離して動作するように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しは外部依存かつコストが発生するため、テスト時はモック化が推奨されています（モジュール内に注釈あり）。

---

## ディレクトリ構成（抜粋）
```
src/kabusys/
├── __init__.py
├── config.py
├── run_execution.py
├── run_monitoring.py
├── utils/
│   └── process_priority.py
├── execution/
│   ├── order_manager.py
│   ├── reconciler.py
│   └── ... (broker, order_repository 等)
├── monitoring/
│   ├── monitoring_db.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   ├── alert_manager.py
│   ├── monitoring_engine.py
│   └── streamlit_dashboard.py
├── portfolio/
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── news_nlp.py
│   └── regime_detector.py
└── tools/
    └── paper_verification_report.py
```

---

## 参考: 重要な挙動・デフォルト値
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒） — デフォルト 60
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
- 監視 DB スキーマは init_monitoring_db() によって自動作成・マイグレーションされます。

---

README に書かれている内容はコードベースの主要部分に基づく概要です。より詳細な設計意図や仕様（PortfolioConstruction.md など）がある場合はそちらも参照してください。必要であれば、セットアップ用の requirements.txt やデプロイ手順、各モジュールの利用例を追加で作成します。