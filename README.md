# KabuSys

日本株向け自動売買システム（モジュール群）。  
本リポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース処理など、実運用を想定したコンポーネントを含んでいます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買システムを構成するライブラリ群および起動スクリプト群です。主な目的は以下です。

- 注文の生成・送信・状態管理（Execution）
- 実行環境の監視、リスク検出、アラート送信（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- DuckDB 上でのファクター計算・リサーチ（Research）
- ニュースを LLM（OpenAI）で評価して銘柄別スコア化（AI）
- Paper Trading 検証・レポート生成、Streamlit ダッシュボード

設計方針の一部:
- DuckDB / SQLite を使ったローカル分析・ログの保管
- 環境に応じた切替（development / paper_trading / live）
- フェイルセーフ（API 失敗時はフォールバック）と冪等性を重視
- 外部 API 呼び出し箇所は明確化されテスト容易性に配慮

---

## 主な機能一覧

- Execution
  - Broker クライアントの切替（paper_trading 時は MockBrokerClient）
  - OrderManager / RiskManager / Reconciler による発注・自動再同期
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 滞留注文 / 約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 各 Monitor の統合ループ、KillSwitch（kill.flag）生成
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定 / スコア重み・等分配 / セクター制限 / レジーム乗数 / 株数決定（単元丸め・集約キャップ）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI
  - news_nlp: raw_news を OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector: ma200 とマクロニュースセンチメントを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL レポートを生成

---

## セットアップ手順

前提: Python 3.9+（適宜バージョンを合わせてください）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール  
   （requirements.txt がない場合は代表的なパッケージを手動で入れてください）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   - 実行環境に応じて追加で必要なパッケージがある可能性があります。

4. 環境変数の準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既定では OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
   - PAPER_FILL_MODE — paper_trading 時のフィルモード: instant | partial | never | reject（デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視 DB （デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB のパス（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH — PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

---

## 使い方

各主要スクリプトの起動例です。src 配下を Python のモジュールパスとして実行します。プロジェクトルートを PYTHONPATH に含めるか、リポジトリルートで実行してください。

- ExecutionEngine 起動（本番 / paper_trading の切替は KABUSYS_ENV）
  ```bash
  # 本番想定（env を設定）
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。

- Monitoring（SystemMonitor の単体簡易スクリプト）
  ```bash
  # ポーリングループで監視を継続実行
  export MONITOR_POLL_INTERVAL=60  # 省略可（デフォルト60秒）
  python -m kabusys.run_monitoring
  ```

  - MONITOR_POLL_INTERVAL は 1 以上の整数。無効な値はデフォルトにフォールバックします。
  - 実行時にプロセス優先度を "high" に設定します（権限によってはスキップされます）。

- Streamlit ダッシュボード（監視 DB の読み取り専用ビュー）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（例）
  - ニューススコアリング（プログラムから呼ぶ API）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    print(f"scored {count} codes")
    ```

  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    count = score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## 設定（主な環境変数の説明）

- KABUSYS_ENV: 実行モード
  - development / paper_trading / live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う際の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定挙動）
- PID_FILE_PATH: ExecutionEngine が書き込む PID ファイル（data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（INFO 等）

注意: Settings モジュールはプロジェクトルートの `.env` / `.env.local` を自動で読み込もうとします（自動ロードを無効化可）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (※別ファイル群)
    - execution_engine.py (Engine の本体)
    - broker_factory.py
    - broker_api.py
    - ... (発注関連)
  - monitoring/
    - monitoring_db.py              — SQLite 用永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (想定されるデータ格納場所)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
  - utils/
    - process_priority.py
    - __init__.py

---

## 開発・運用時の注意事項

- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブル・列を追加します。既存 DB の互換性を保つ簡易マイグレーションが含まれます。
- Paper Trading と本番 DB は分離されています（settings.is_paper に従う）。Paper 実行時の DB は PAPER_TRADING_SQLITE_PATH を確認してください。
- AI 呼び出し（OpenAI）はキー必須。API 失敗時のフォールバック動作が組み込まれていますが、API 制限等は考慮して実行してください。
- プロセス優先度設定や CPU affinity 設定は OS に依存します。権限不足や未対応 OS では警告を出してスキップします。
- kill.flag による停止シグナル（KillSwitch）を採用しています。実稼働時は kill.flag の扱い（手動クリア・自動クリア設定）に注意してください。

---

## 貢献 / 拡張案

- Broker 実装の追加（実ブローカー API 連携）
- 単元株や手数料モデルの銘柄別対応
- duckdb テーブルの自動作成/ETL パイプラインの整備
- テストカバレッジの拡充（特に AI 呼び出しのモック）

---

この README はコードベースの主要部分をまとめたものです。実際に運用する際は `src/kabusys/config.py` や各モジュールの docstring を参照し、環境変数・DB パス・API キーなどを適切に設定してください。必要であれば README に追加したい項目（例: 依存関係の完全な list、運用手順、Docker 化 など）を教えてください。