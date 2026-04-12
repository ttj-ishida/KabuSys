# KabuSys

日本株自動売買システムの一部実装 (リサーチ・ポートフォリオ構築・発注・監視・AI 補助機能)。  
この README はリポジトリ内の主要モジュールに基づいて、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを想定したモジュール群です。主な責務は以下です。

- ファクター計算・研究（DuckDB 上の株価・財務データを使ったファクター生成）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ算出・セクター制約）
- 発注・注文管理（Broker 抽象化、OrderManager、Reconciler）
- Paper Trading モードと本番モードの分離（SQLite の別ファイルなど）
- システム監視（プロセス状態、データ鮮度、注文滞留・約定異常、リスク警告）
- AI 補助機能（ニュースのセンチメントスコアリング、レジーム判定 — OpenAI を利用）
- 運用用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針として、DuckDB を用いたデータ処理、SQLite による監視ログの永続化、外部 API 呼び出しは抽象化してフェイルセーフに動作するよう実装されています。

---

## 主な機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でのファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索・IC 計算
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定・重み計算
  - calc_position_sizes：発注株数決定・集計制約・lot 単位丸め
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジーム乗数
- execution
  - OrderManager：注文作成・送信・同期ロジック
  - Reconciler：再起動時の自動復旧（OrderSent 照合・ポジション差分検出）
  - Broker クライアント抽象化（本番 / Mock を切替可能）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：定期チェック（CPU/メモリ/ディスク、データ鮮度、滞留注文、約定異常、ドローダウン等）
  - MonitoringDB：SQLite ベースの監視ログ格納層（テーブル作成・マイグレーション含む）
  - MonitoringEngine：各 Monitor を束ねてポーリング・アラート送出
  - AlertManager：LINE Push による通知（設定がある場合）
  - KillSwitch：条件に応じてフラグファイルを書き ExecutionEngine 停止シグナルを送信
  - Streamlit ベースの監視ダッシュボード
- ai
  - news_nlp.score_news：OpenAI を使ったニュースセンチメントスコア生成と ai_scores への書き込み
  - regime_detector.score_regime：MA200 とマクロセンチメントを合成した市場レジーム判定
- tools
  - paper_verification_report：Paper Trading 用検証レポート生成（uptime / fill rate / latency 等）

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントに `|` 演算子を使用）
- SQLite（組み込み）
- DuckDB（Python パッケージ）
- その他 Python パッケージ:
  - psutil
  - requests
  - openai（AI 機能を使う場合）
  - streamlit（ダッシュボードを使う場合）

例（最低限のインストール例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際の運用では requirements.txt を作成して管理してください。）

---

## 設定（環境変数）

設定は環境変数およびプロジェクトルートの `.env` / `.env.local` によって行います。自動読み込みはデフォルトで有効です（テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数（代表）:

- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所で参照）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所で参照）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）を使う場合に必要
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の充填モード（instant / partial / never / reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定取得は `kabusys.config.Settings` クラスでラップされています。必須変数が不足すると ValueError を送出します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil requests openai streamlit
   ```

3. `.env` を作成（例: プロジェクトルートに .env）
   重要な変数を設定してください（例）:
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

   - 本番運用時は `.env` に機密情報を置かないか、アクセス権限を厳格にしてください。

4. データディレクトリ作成
   ```bash
   mkdir -p data
   ```

5. DuckDB / SQLite 用データを準備（prices_daily / raw_financials などのテーブルは事前に用意すること）
   - モジュールは DuckDB の `prices_daily` / `raw_financials` / `raw_news` 等を参照します。運用前にデータロードが必要です。

---

## 実行方法 / 使い方

- ExecutionEngine（本番 or Paper Trading）
  - Paper Trading にするには環境変数 `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient が利用され、`PAPER_TRADING_SQLITE_PATH` に記録します。
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 起動時に PID ファイル（デフォルト: data/execution.pid）を作成します。

- Monitoring（監視ループ）
  - ポーリングループを起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。

- Paper Trading 検証レポート
  - SQLite を指定してレポート生成:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - オプション `--from` / `--to` は YYYY-MM-DD 形式。`--db` で DB パスを指定可能（環境変数 `PAPER_TRADING_SQLITE_PATH` でも可）。

- Streamlit 監視ダッシュボード
  - 起動:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - DB を読み取り専用で開きます（MonitoringEngine が作成する DB と競合しにくい）。

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーを与えて呼び出します（`OPENAI_API_KEY` を設定するか関数引数で指定）。
  - 呼び出し例（Python 内で）:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, datetime.date(2026, 4, 10), api_key="sk-...")
    ```

---

## 運用上のポイント / 注意事項

- Paper Trading と本番は SQLite ファイルで分離されています（`PAPER_TRADING_SQLITE_PATH`）。
- Monitoring は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使用する設計になっている箇所があります（run_monitoring 参照）。
- OpenAI を使う機能は API エラー時にフェイルセーフ（デフォルト振る舞いにフォールバック）するよう実装されていますが、API キーは必須です。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みを無効化できます（テスト用途）。
- `MONITOR_POLL_INTERVAL` に 0 以下など不正な値を指定するとデフォルト（60秒）にフォールバックします。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主な構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env ローダ・Settings クラス
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
    - research/
      - __init__.py
      - factor_research.py     — Momentum / Volatility / Value ファクター計算
      - feature_exploration.py — forward returns / IC / summary utilities
    - portfolio/
      - __init__.py
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 株数計算・スケーリング・lot 丸め
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - execution/
      - order_manager.py       — OrderManager
      - reconciler.py          — 起動時リコンシリエーション
      - ...                    — （ブローカー抽象や OrderRepository 等はこの階層に配置）
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite スキーマ・MonitoringDB
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート
    - utils/
      - __init__.py
      - process_priority.py     — psutil を使ったプロセス優先度 / CPU affinity

その他、DuckDB スキーマや外部データロード用のスクリプトはプロジェクトに合わせて用意してください。

---

## 参考コマンドまとめ

- ExecutionEngine 起動:
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

README に書かれている内容はコードベースの主要部分に基づく要約です。実運用や詳細な設定は各モジュールのドキュメント（コード内 docstring）を参照してください。必要であれば、README に含めるセットアップ手順（例: requirements.txt、DB 初期ロード手順、サンプル .env）や運用手順のテンプレートをさらに追記します。