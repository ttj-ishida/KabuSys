# KabuSys

日本株向け自動売買システムのコンポーネント集です。シグナル → 注文実行 → 監視・リスク管理・レポート作成までのワークフローを想定したモジュール群を含みます。

## 概要
KabuSys は以下を目的としたモジュール群を提供します:
- 注文作成・発注・状態管理を行う ExecutionEngine（Execution）
- システム状態・注文状態・リスクを定期的に監視する Monitoring
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP / レジーム判定のための OpenAI 統合
- Paper Trading 用検証レポートや Streamlit ダッシュボード等のツール群

このリポジトリは、実運用（live）、ペーパートレード（paper_trading）、開発（development）モードを環境変数で切り替えられる設計です。

## 主な機能一覧
- Execution
  - 注文状態遷移、重複注文防止、リスク管理との統合
  - ブローカー API 抽象化（MockBroker を紙取引時に使用）
  - 再起動時のリコンシリエーション（Reconciler）
- Monitoring
  - CPU / メモリ / ディスク / プロセス存否の監視（SystemMonitor）
  - 注文滞留 / 約定価格異常の検出（TradeMonitor）
  - ドローダウン / ポジション上限監視（RiskMonitor）
  - Kill Switch（危険条件時に外部ファイルにフラグを書き Execution を止める）
  - LINE 通知によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定、等重/スコア重み付け、リスク調整（セクター制限・レジーム係数）、ポジションサイジング
- Research
  - Momentum / Volatility / Value 等ファクター計算（DuckDB 接続）
  - 将来リターン・IC（Information Coefficient）計算・統計サマリ
- AI
  - ニュースのセンチメントを OpenAI で評価して ai_scores に書き込む
  - マクロ + ETF MA200 乖離を組み合わせた市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - 各種ユーティリティ

## 必要条件
- Python 3.10+
- 以下主要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（組み込み）
- （任意）LINE 通知を使う場合はインターネット接続と LINE チャネル設定

依存関係はプロジェクトに requirements.txt / pyproject.toml がある想定です。仮想環境を作成してインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または個別に:
pip install duckdb psutil openai requests streamlit
```

## 環境変数（主要）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。既定は `development`。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）。
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）。
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）。
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用。
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（`paper_trading` 環境で使用、デフォルト: `data/paper_trading.db`）。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）。
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。0以下は無効でデフォルトにフォールバック。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します。

Settings はプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数を上書きしない挙動等を制御）。

## セットアップ手順（簡易）
1. レポジトリをクローン / 取得
2. 仮想環境を作成して依存をインストール
3. プロジェクトルートに `.env`（.env.example を参照）を配置して必要な環境変数を設定
4. data ディレクトリを作成（ログや DB を置く想定）
   ```bash
   mkdir -p data
   ```
5. 必要なら DuckDB / SQLite の初期データ投入や外部データパイプラインを実行

注意:
- MonitoringDB は起動時に自動でテーブルを初期化（冪等）します（init_monitoring_db）。
- Paper trading（KABUSYS_ENV=paper_trading）は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い本番 DB とは分離されます。

## 使い方（主要コマンド例）
- Monitoring を起動（ポーリングループ）
  ```bash
  # デフォルトポーリング 60 秒
  python -m kabusys.run_monitoring

  # ポーリング間隔を変更
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
  ```
  停止は Ctrl+C、またはプロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループは検知して終了します。

- ExecutionEngine を起動（注文実行）
  ```bash
  # 本番/開発は KABUSYS_ENV に従う
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - paper_trading の場合は MockBrokerClient が使用され、`data/paper_trading.db` に記録されます。
  - Execution 側も `data/stop_requested.flag` の存在を確認して停止します。

- Streamlit ダッシュボードを起動（監視ダッシュボード）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11 \
    --db data/paper_trading.db
  ```
  引数を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を参照します。

- AI 機能（ニューススコア / レジーム判定）
  - 必須: `OPENAI_API_KEY` を設定
  - これらはモジュール関数として呼び出すことが想定されています。例えば Python REPL / スクリプトから:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1), api_key="sk-...")
    ```
  - 同様に `kabusys.ai.regime_detector.score_regime` を呼び出して market_regime テーブルに書き込めます。

## 停止 / キルの仕組み
- プロセス中断: Ctrl+C（KeyboardInterrupt）でループが終了します。
- 外部停止要求:
  - `data/stop_requested.flag` を作成すると run_monitoring/run_execution のループで検知して停止します（スクリプト内で該当パスを参照）。
  - Kill Switch（リスクトリガー）は `data/kill.flag`（Settings.kill_flag_path）を作成して ExecutionEngine に停止を促すことができます（KillSwitch クラスが理由を書き込みます）。Execution 起動時に `KILL_FLAG_CLEAR_ON_START` を有効にすると起動時にクリアする設定があります。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（Settings）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (想定)
    - broker_factory.py (想定)
    - order_record.py (想定)
    - ...（ブローカー API 抽象など）
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時に使用する DB / PID / flag を配置する想定)
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - other supporting modules...

各モジュールはできるだけ副作用を抑え、DuckDB / SQLite 接続等を呼び出し元から渡す設計になっています。

## 運用上の注意
- Paper Trading は本番 DB と分離するため `paper_sqlite_path` を使用します。production と混ぜないよう注意してください。
- OpenAI API キーは機密情報です。`.env` を使う際は .gitignore に含める等の管理を行ってください。
- Process priority / CPU affinity は OS により適用可否が異なります。権限不足や未対応 OS の場合は警告が出ますが安全にスキップします。
- Monitoring のログや DB スキーマは保持・マイグレーション処理を備えていますが、本番 DB を操作する前にバックアップを取ってください。

---

README の補足や、特定のモジュール（ExecutionEngine の設定例、Broker 実装、DuckDB データパイプライン、CI テスト手順など）を追加したい場合は、どの項目を詳しくしたいか教えてください。