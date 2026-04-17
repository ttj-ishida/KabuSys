# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステムです。本リポジトリは取引実行、モニタリング、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などのモジュール群を含みます。

以下はこのコードベースの概要と利用方法をまとめた README です。

---

## プロジェクト概要

- 目的: 日本株の自動売買システム（Execution）と、それを支える監視（Monitoring）・リサーチ機能を提供する。
- 主なコンポーネント:
  - ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
  - MonitoringEngine（システム状態・注文状態・リスク監視、LINE 通知・Kill Switch）
  - Portfolio construction（候補選定・重み付け・ポジションサイジング）
  - Research（ファクター計算・将来リターン・IC 計算）
  - AI モジュール（ニュースのセンチメント解析／レジーム判定）
  - ユーティリティ（設定読み込み、プロセス優先度設定など）

設計上の特徴:
- 設定は環境変数（.env / .env.local の自動ロード対応）で管理
- Paper Trading モードでは本番 DB と完全分離（専用 SQLite を使用）
- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等）
- OpenAI API を用いたニュース NLP（失敗時はフェイルセーフ設計）

---

## 機能一覧

- 実行系
  - ExecutionEngine：ブローカーとの注文送信、状態管理、リスク管理
  - Reconciler：再起動時の注文/ポジション照合（自動復旧）
  - BrokerClientFactory により本番 / モックブローカーを切り替え可能（KABUSYS_ENV に依存）
- 監視系
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス存在チェック
  - TradeMonitor：滞留注文検出、約定価格の異常検知
  - RiskMonitor：ドローダウン・ポジション上限の監視、Dashboard の維持
  - KillSwitch：重大リスク時に stop フラグ（data/kill.flag）を書き込む
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視用 UI）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクター調整、ポジションサイジング（単元株丸め・集計キャップ）
- リサーチ
  - ファクター計算（Momentum/Volatility/Value）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - news_nlp.score_news：OpenAI でニュースを集約して銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime：ETF MA とマクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py：Paper Trading DB を解析して検証レポート出力

---

## 必要環境 / 依存パッケージ

- Python 3.9+
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワーク（OpenAI / LINE API を利用する場合）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

設定は環境変数から読み込まれます。.env / .env.local をプロジェクトルートに置くことで自動ロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数（Settings で利用）:
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabu API 用）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し DB を分離
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）

その他、各モジュールで利用する閾値等の環境変数あり（Settings を参照）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてソースルートに移動
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに .env（または .env.local）を作成し必要な環境変数を設定
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合: OPENAI_API_KEY を設定
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
5. data ディレクトリを作成（PID / flag / DB の保存先）
   ```bash
   mkdir -p data
   ```
   実行スクリプトが自動で DB テーブルを初期化します（init_monitoring_db）。

注意:
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading に設定。paper_trading 用の SQLite は PAPER_TRADING_SQLITE_PATH で上書きできます。
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。

---

## 使い方（主要スクリプト）

プロジェクトはモジュールとして実行可能です。スクリプトは src/kabusys 内にあります。

1. 監視ループ起動（Monitoring）
   - 説明: SystemMonitor をポーリングして監視ログを SQLite に記録します。MONITOR_POLL_INTERVAL で間隔を上書き可（秒、デフォルト 60）。
   - 実行:
     ```bash
     python -m kabusys.run_monitoring
     ```
   - 環境変数:
     - MONITOR_POLL_INTERVAL（例: 30）
   - 備考: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

2. 実行エンジン起動（Execution）
   - 説明: ExecutionEngine を起動して発注ループを実行。paper_trading モードでは MockBrokerClient と専用 DB を使用。
   - 実行:
     ```bash
     python -m kabusys.run_execution
     ```
   - 備考:
     - 実行中は data/execution.pid が作成される想定（PID ファイルの扱いは Settings で制御）。
     - data/stop_requested.flag を作成すると外部から停止指示が送られる（起動スクリプトが検出して停止）。

3. Paper Trading 検証レポート
   - 説明: Paper Trading の SQLite（デフォルト data/paper_trading.db）を解析してレポートを出力
   - 実行:
     ```bash
     python -m kabusys.tools.paper_verification_report
     # 期間指定例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     # DB パス指定:
     python -m kabusys.tools.paper_verification_report --db path/to/db
     ```

4. 監視ダッシュボード（Streamlit）
   - 説明: streamlit を使った監視ダッシュボード（読み取り専用で SQLite を参照）
   - 実行:
     ```bash
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```

5. AI 関連（ニューススコア・レジーム判定）
   - モジュール API を直接呼び出して使います（Python から import）。
   - 例:
     ```python
     from kabusys.ai.news_nlp import score_news
     # duckdb_conn: duckdb.connect(...)
     # score_news(duckdb_conn, target_date, api_key="...")
     ```
   - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）。

---

## 注意点 / 運用上のポイント

- Paper Trading と Live は DB を分離する設計です（誤って本番 DB を汚さないため）。
- SystemMonitor は PID ファイルの stale 判定やデータ鮮度をチェックし、stale PID 発見時に PID ファイルを削除します。
- KillSwitch は RiskMonitor の結果に応じて data/kill.flag を書き込み、Execution 側に停止を促します。
- AlertManager は LINE に通知しますが、トークンや user_id が未設定の場合は送信をスキップしてログのみ出力します。クールダウン管理あり。
- OpenAI 呼び出しは再試行（指数バックオフ）やレスポンス検証・クリッピング等の保護処理が入っています。API エラー時は基本的にフェイルセーフ（代替値で継続）する設計です。
- Settings が必須の環境変数を見つけられない場合は起動時に ValueError を raise します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・モジュール構成（リポジトリの全ファイルではありません）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュースセンチメント（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース + LLM）
    - __init__.py
  - monitoring/
    - monitoring_db.py              — SQLite テーブル初期化 / MonitoringDB ラッパ
    - system_monitor.py             — CPU/MEM/DISK/データ鮮度/プロセス監視
    - trade_monitor.py              — 注文滞留 / 約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 操作 (停止トリガ)
    - alert_manager.py              — LINE 通知ラッパ
    - monitoring_engine.py          — 各 Monitor を束ねるループ
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - ...（ブローカー API / リスク管理等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/                            — 実行時に使われる DB / PID / flag 等（自動生成されることが多い）

---

## よく使うコマンドまとめ

- 仮想環境の作成／依存インストール
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt  # もし用意されていれば
  pip install duckdb psutil requests openai streamlit
  ```

- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  # 例: ポーリング間隔を 30 秒に設定
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 最後に

- コードはモジュール化されており、各コンポーネント（Execution / Monitoring / Research / AI / Portfolio）はテストや差し替えがしやすい設計になっています。
- 実運用前に .env を整備し、Paper Trading で十分に検証してください。
- 何か追加で README に載せたい項目（例: 詳細な .env.example、DB スキーマ説明、開発ワークフロー等）があれば教えてください。こちらで追記します。