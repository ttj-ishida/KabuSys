# KabuSys — README (日本語)

日本株自動売買システムのコンポーネント群（モニタリング、実行、調査、ポートフォリオ構築、AI/ニュース処理など）を含むコードベースの説明書です。本 README はリポジトリ内の主要スクリプトと設定、起動方法、ディレクトリ構成をまとめています。

注意: 実行には外部 API キーや各種依存パッケージが必要です。Paper Trading と本番データは分離されています。

## プロジェクト概要
KabuSys は日本株自動売買のためのライブラリ兼実行環境です。主な責務は次のとおりです。
- 注文管理・発注（ExecutionEngine, OrderManager, BrokerClient）
- リコンシリエーション（Reconciler）
- リスク監視（RiskMonitor）
- システム監視（SystemMonitor）とアラート（LINE 経由）
- モニタリング DB（SQLite）へのログ永続化
- 価格・ファクター計算（DuckDB を利用した research モジュール）
- ニュースを用いた NLP スコアリング（OpenAI）
- Paper Trading 用の検証レポート生成ツール
- Streamlit による監視ダッシュボード

設計方針として、ルックアヘッドバイアスを避ける、Paper Trading と本番 DB を分離する、外部 API 呼び出しにフォールバック動作を持たせる等が採用されています。

## 主な機能一覧
- SystemMonitor: CPU/メモリ/ディスク利用率、プロセス生存確認、データ鮮度チェック
- TradeMonitor: 注文滞留（stale order）、約定価格の異常検出
- RiskMonitor: ドローダウン・ポジション数上限の監視とアラート記録
- KillSwitch: 条件に応じて停止フラグ（data/kill.flag）を書き込み、ExecutionEngine を安全停止
- MonitoringEngine: 上記モニタを束ねて定期実行、LINE 通知（AlertManager）
- ExecutionEngine: ブローカーとのやり取り、発注・注文状態管理、再起動時のリコンシリエーション
- Portfolio モジュール: 候補選定、重み付け（等分・スコア加重）、ポジションサイズ計算、セクター制限、レジーム適用
- Research モジュール: Momentum/Volatility/Value 等のファクター計算、将来リターン、IC 計算、統計要約
- AI モジュール: news_nlp（OpenAI を使ったニュースセンチメント -> ai_scores）、regime_detector（MA + マクロニュースで市場レジーム判定）
- Tools: paper_verification_report（Paper Trading 検証レポート生成）
- Streamlit ダッシュボード（監視情報の可視化）
- ユーティリティ: 環境変数の自動読み込み（.env/.env.local）、プロセス優先度設定ユーティリティなど

## セットアップ手順

前提
- Python 3.9+（型ヒントの Union 表記などに対応していることを想定）
- SQLite、DuckDB（Python パッケージ duckdb）
- ネットワーク接続（LINE / OpenAI / ブローカー API を使う場合）

1. リポジトリをクローン・配置
   - この README はパッケージが `src/kabusys` 配下にある前提です。
   - プロジェクトルートに `data/` ディレクトリを作成しておくと便利です（PID/フラグ/DB を配置するため）。
     ```
     mkdir -p data
     ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   必要となる主なパッケージ（例）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数の準備
   プロジェクトルートに `.env`（および必要なら `.env.local`）を配置できます。自動読み込み機能が有効であれば起動時に読み込まれます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 時の SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の MockBroker の約定ポリシー（instant|partial|never|reject）
   - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒, デフォルト 60）
   - PID_FILE_PATH / KILL_FLAG_PATH 他

   例 .env（最小例、実際にはトークン類を設定してください）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB 初期化
   - Monitoring 用 SQLite は起動スクリプトが自動で init します（init_monitoring_db を呼び出すため冪等に作成されます）。
   - DuckDB は prices_daily / raw_financials / raw_news などのテーブルが想定されています。データをロードする ETL は別途必要です（本 README では割愛）。

## 使い方（主要なコマンド／スクリプト）

プロジェクトがパッケージとして参照できる状態（例えば `PYTHONPATH=src`）で以下を実行します。あるいはリポジトリルートから `python -m kabusys.<module>` を指定します。

1. Monitoring の常駐起動
   - ポーリングして system/trade/risk のチェックとログ書き込みを行うプロセス。
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
   ```
   PYTHONPATH=src python -m kabusys.run_monitoring
   ```
   - 実行時はプロセス優先度が "high" に試みて設定されます（プラットフォーム依存）。
   - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとループが検出して終了します（または Ctrl+C）。

2. ExecutionEngine 起動（実行エンジン）
   - 本番/ペーパートレードを環境変数 KABUSYS_ENV により切り替え（paper_trading の場合は MockBrokerClient を使用し、Paper 用 SQLite に書き込む）。
   ```
   PYTHONPATH=src python -m kabusys.run_execution
   ```
   - 起動時に data/execution.pid を使ってプロセスの存在を管理。停止フラグ（data/stop_requested.flag）が立っていると起動を行いません。
   - Paper Trading は settings.is_paper により sqlite パスを paper_sqlite_path に切り替えます。

3. Streamlit ダッシュボード（監視 UI）
   - read-only で monitoring DB を開いて監視情報を表示します。
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - DB が存在しない場合は開始メッセージが表示されます。

4. Paper Trading 検証レポート生成
   - Paper Trading の SQLite を分析して検証レポートを標準出力に出します。
   ```
   PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - `--db` オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できます。

5. AI 機能（ニューススコア / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要です。
   - プログラムからは kabusys.ai.score_news（news_nlp.score_news）や kabusys.ai.regime_detector.score_regime を呼び出します。
   - 例（Python REPL）:
     ```py
     from pathlib import Path
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
     ```

6. 停止フラグ / キルフラグの扱い
   - 実行停止：data/stop_requested.flag を作成すると run_monitoring / run_execution が順次終了します。
   - KillSwitch（自動停止）: RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止指示を出す運用を想定しています。kill.flag は Settings.kill_flag_clear_on_start によって起動時にクリアできます（環境変数で制御）。

## 設定（Settings）と重要な環境変数
Settings クラスにより環境変数をラップしています。主要な設定とデフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
- SQLITE_PATH: data/monitoring.db（監視 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の fill 模擬）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値など

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）に .env/.env.local がある場合、自動で読み込みます。
- OS 環境変数を保護しつつ .env.local で上書き可能。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

## 監視 DB（monitoring_db）について
init_monitoring_db(conn) により以下テーブルを作成します（冪等）:
- system_status: cpu/memory/disk/process 状態ログ
- trade_logs: 発注イベントログ（latency_ms カラムあり）
- positions: 保有ポジション
- risk_logs: リスクイベントログ（dedup 機能有り）
- dashboard: ダッシュボード集計（id=1 の単一行）

既存 DB へのマイグレーションも一部自動で行います（例: dashboard に peak_value カラム追加、trade_logs に latency_ms 追加）。

## ディレクトリ構成（主要ファイル）
リポジトリの主要構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py        — Monitoring DB 初期化・読み書き
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py     — (一部ファイルが存在)
    - ...                     — ブローカー関連、engine 実装等
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
  - tools/
    - paper_verification_report.py
    - __init__.py

その他、data/ 以下に DB/フラグ/PID ファイルを置く想定です。

## 運用上の注意 / ベストプラクティス
- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading を利用してください。
- AI（OpenAI）を利用する機能は API 呼び出しの障害を想定してフォールバック（スコア 0.0、部分失敗時の保持等）していますが、API キーの漏洩には注意してください。
- stop/kill フラグは冪等に扱われます。kill.flag の自動作成はリスク管理が目的なので、運用手順を明確にしてください。
- プロセス優先度設定はプラットフォーム依存で失敗する場合があります（権限不足等）。その場合はログに警告が出ますが処理は継続します。
- DuckDB / SQLite のファイルパスは Settings による設定で変更できます。バックアップ / バージョン管理に注意してください。
- streamlit ダッシュボードは DB を read-only で開ける URI を使っています。監視プロセスが動いているか確認するために便利です。

---

追加で README に含めたい情報（例: API スキーマ、ETL 手順、Broker 接続設定、テストの実行方法など）があれば指示してください。必要に応じてサンプル .env.example や運用手順 (runbooks) を作成します。