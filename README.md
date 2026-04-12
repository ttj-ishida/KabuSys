# KabuSys

日本株自動売買システムの一部（ライブラリ & 実行スクリプト群）。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、LLM を使ったニュース NLP / レジーム判定などのコンポーネントを含みます。

---

## プロジェクト概要

- 目的: 日本株の自動売買運用に必要な実行・監視・検証・研究ユーティリティを提供する。
- 構成:
  - Execution: ブローカーへの発注、リスク管理、リコンシリエーション
  - Monitoring: システム稼働監視、注文滞留・約定異常検出、Kill Switch、通知
  - Portfolio: 銘柄選定、配分、ポジションサイズ計算、リスク調整
  - Research: DuckDB を使ったファクター・リターン計算・IC 等の解析
  - AI: OpenAI API を使ったニュースセンチメント付与 / 市場レジーム判定
  - Tools: Paper Trading 検証レポート生成など CLI ツール

---

## 主な機能一覧

- 実行（ExecutionEngine）
  - ブローカークライアント抽象化（本番 / モック）
  - 注文管理（OrderManager）、リスク管理（RiskManager）、リコンシリエーション
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度確認
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて停止フラグを書き込み ExecutionEngine を停止
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視用）
- ポートフォリオ構築
  - 候補選定、等分配 / スコア配分、スコア基準での重み付け
  - セクター集中抑制、レジーム乗数適用
  - 単元株丸め・リスクベースの株数算出、投下資金のスケールダウン
- 研究
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI 系
  - ニュースの銘柄別センチメント評価（OpenAI / gpt-4o-mini、JSON モード）
  - マクロニュース + ETF MA200 を使った日次レジーム判定
  - API エラーに対するリトライやフェイルセーフ処理を実装
- 検証ツール
  - Paper Trading 検証レポート生成（orders / system logs / latency 等の指標）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   必要な主要パッケージ（プロジェクトで使用されているもの）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用）

4. データディレクトリの作成
   ```
   mkdir -p data
   ```
   デフォルトの DB は `data/monitoring.db`（監視用 SQLite）および `data/kabusys.duckdb`（DuckDB）です。必要に応じて環境変数で上書きできます（下記参照）。

5. 環境変数の設定  
   よく使う環境変数（必須 / 任意）:
   - 必須（実行で必要になる場合）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - 任意 / 実行時に必要になるもの
     - KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知
     - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB パス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading のモック約定モード（instant, partial, never, reject）
     - PID_FILE_PATH / KILL_FLAG_PATH / MONITOR_POLL_INTERVAL / LOG_LEVEL 等
   - 自動 .env ロード:
     - プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）。
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   .env の例（最小）
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...
   ```

---

## 使い方（主要スクリプト / コマンド例）

- 監視ループ起動（SystemMonitor 単体）
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path を使用して監視ログを保存します（KABUSYS_ENV にかかわらず本番パスを参照する実装上の挙動に注意）。

- ExecutionEngine 起動（実トレード / Paper Trading）
  - paper_trading モードでは BrokerClient のモック実装が使われ、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に出力されます。本番 DB とは完全に分離されます。
  - 実行:
    ```
    export KABUSYS_ENV=paper_trading   # または live / development
    python -m kabusys.run_execution
    ```

- Paper Trading 検証レポート生成
  - 既存の paper trading データベース（data/paper_trading.db）から期間指定でレポートを出力します。
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスを明示する:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- Streamlit 監視ダッシュボード
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB を読み取り専用で開くため、MonitoringEngine を先に起動してデータが作成されていることを確認してください。

- AI / レジーム判定・ニューススコアリング（プログラムから呼び出す）
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 両方とも OpenAI API キー（引数または OPENAI_API_KEY 環境変数）が必要です。API コールは失敗時にフォールバック動作を持ちます（完全失敗では運用停止しない設計）。

---

## 主要設定（Settings） — 環境変数一覧

（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

詳細は src/kabusys/config.py を参照してください。

---

## 開発 / テスト時の注意点

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。必要なら .env/.env.local を用意してください。
- Paper Trading モードを使うと本番 DB と分離して動作しますが、環境変数の設定ミスに注意してください。
- OpenAI を利用する機能はコストが発生します。ローカルテストではモックやパッチ（unittest.mock.patch）で API 呼び出しを置き換えることを推奨します（各モジュールでテストフックが想定されています）。
- DuckDB クエリは prices_daily / raw_financials 等のテーブルを前提としています。研究機能を使う場合は事前にデータをロードしてください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境設定 / .env ロード
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント（OpenAI）
    - regime_detector.py               — レジーム判定（MA200 + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py                 — SQLite 永続化層（監視用）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他: broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (推奨ローカルディレクトリ)
    - kabusys.duckdb (デフォルト)
    - monitoring.db (監視 SQLite)
    - paper_trading.db (paper_trading 用 SQLite)

---

## 参考・補足

- DB 初期化: run_monitoring / run_execution の起動時に監視用テーブルは自動で作成（init_monitoring_db）されます。初回はこれらのスクリプトを実行して DB スキーマを生成できます。
- プロセス優先度設定: 起動スクリプトは最初に set_process_priority("high") を試みます（psutil に依存）。権限不足の場合は警告を出してスキップします。
- Kill Switch: RiskMonitor の判定により data/kill.flag を作成し ExecutionEngine に停止を促す仕組みがあります。ExecutionEngine 起動時にこのフラグをクリアするオプション（設定）を持ちます。

---

不明点や追加で README に含めたい内容（例: 実行例ログ、CI 設定、具体的な API モック導入例など）があれば教えてください。必要に応じて追記・テンプレート化します。