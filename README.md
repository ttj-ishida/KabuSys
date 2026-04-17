# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な Python コンポーネント群です。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算・リサーチ、AI ベースのニュースセンチメント評価などをモジュール化して提供します。

---

## 主要な特徴
- ExecutionEngine（発注・注文管理）と Monitoring（システム/注文/リスク監視）の分離
- Paper Trading モード（本番 DB と分離した専用 SQLite）をサポート
- DuckDB を用いた時系列データ（prices_daily / raw_financials 等）処理
- ニュース NLP（OpenAI）を使った銘柄別センチメントスコアリング（ai.score_news）
- 市場レジーム判定（ETF MA + LLM マクロセンチメントの合成）
- Streamlit を用いた監視ダッシュボード
- Paper Trading の検証レポート生成ツール
- 各種ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算・セクターキャップ等）
- OS に依存しないプロセス優先度・CPU affinity 設定ユーティリティ

---

## 準備（セットアップ）

前提
- Python 3.10+
- 開発環境ではソースルートを PYTHONPATH に含める（例: プロジェクトルートから実行する / パッケージとしてインストール）

必須ライブラリ（主なもの）
- duckdb
- psutil
- requests
- openai
- streamlit

例: 仮想環境でのセットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# 追加の依存があれば適宜インストールしてください
```

環境変数
- .env から自動読み込み（プロジェクトルートに `.env` / `.env.local` がある場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
  - OPENAI_API_KEY （AI 機能利用時に必要）
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（Paper Trading のマッチ挙動）
  - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL（"DEBUG"/"INFO"/...）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（監視アラート用）

初期データディレクトリ（例）
- data/monitoring.db — 監視用 SQLite（init は起動時に自動作成）
- data/paper_trading.db — Paper Trading 用 SQLite（Paper モードで使用）
- data/kabusys.duckdb — DuckDB ファイル（価格や財務データを格納）
- data/execution.pid — ExecutionEngine 用 PID ファイル
- data/kill.flag — KillSwitch が書き込む停止フラグ
- data/stop_requested.flag — 外部からプロセスの停止を伝えるフラグ

注意: 実行スクリプトは必要に応じて DB ファイルや data ディレクトリを作成しますが、アクセス権やパスの確認を行ってください。

---

## 使い方（起動・操作）

パッケージを開発ルートから直接実行する前提での例を示します（project root が PYTHONPATH に含まれるかカレントがプロジェクトルートであること）。

1. Monitoring を起動
- デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒を指定できます（1以上の整数）。
```bash
# プロジェクトルートから
python -m kabusys.run_monitoring
# または短い例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します（KABUSYS_ENV に依存しない）。

2. ExecutionEngine を起動（実際の発注処理）
- Paper Trading モードで起動する場合:
```bash
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- 本番（live）モードで起動する場合:
```bash
KABUSYS_ENV=live python -m kabusys.run_execution
```
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBroker を用い paper_trading 用 SQLite に記録し、本番 DB と分離します。
- ExecutionEngine の停止は data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書き込みます。stop フラグは run_execution 起動時に検査され、既に存在する場合は起動せず終了します。

3. Streamlit ダッシュボード
- 監視 DB（読み取り専用）を使ってブラウザでダッシュボードを表示できます。
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

4. Paper Trading 検証レポート生成（ツール）
- 保存済みの paper_trading DB から検証レポート（稼働率・注文成功率・レイテンシ等）を出力します。
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

5. AI 機能（ニューススコアリング / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必要です。
- ニューススコアリング関数: kabusys.ai.score_news (DuckDB 接続と target_date を渡して呼び出し)
- レジーム判定関数: kabusys.ai.regime_detector.score_regime

---

## 主要設定と動作上の注意点

- 環境読み込み:
  - プロジェクトルートに .env / .env.local があると自動で読み込まれます。OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading のとき、実行エンジンは paper_sqlite_path を使用して取引ログを別 DB に保存します。これにより本番 DB と物理的に分離されます。

- プロセス優先度:
  - run_monitoring/run_execution 起動時に set_process_priority("high") を呼び出します（psutil による優先度設定。権限不足の場合は警告を出して続行）。

- Kill Switch / Stop フラグ:
  - KillSwitch（monitoring.kill_switch）はリスク閾値を超えたときに data/kill.flag を生成し、ExecutionEngine に停止シグナルを送ります。
  - 外部からプロセスを優雅に停止させたい場合は data/stop_requested.flag を作成すると run_* スクリプトが検出して停止します。

- データ鮮度チェック:
  - SystemMonitor は DuckDB の最新価格日を見てデータ鮮度を判定します（_FRESHNESS_DAYS = 3）。price データが古い場合はアラート対象になります。

---

## 開発者向け: 主要モジュール（概要）
- kabusys.config — 環境変数/設定管理（.env 自動ロード、Settings クラス）
- kabusys.execution — 発注系コンポーネント（ExecutionEngine, OrderManager, Reconciler, BrokerFactory 等）
- kabusys.monitoring — 監視コンポーネント（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine, MonitoringDB）
- kabusys.portfolio — 銘柄選定・重み付け・ポジションサイズ計算・リスク調整
- kabusys.research — ファクター計算・将来リターン・IC 計算・統計サマリー
- kabusys.ai — news_nlp（ニュースセンチメント集計）・regime_detector（市場レジーム判定）
- kabusys.tools — 便利スクリプト（paper_verification_report 等）
- kabusys.utils — プロセス優先度 / CPU affinity ユーティリティ 等

---

## ディレクトリ構成（抜粋）
プロジェクトルート配下（src/kabusys を軸に表示）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 broker , engine, order_repository 等)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/  (実行時に生成される想定、リポジトリにはない場合があります)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag

---

## よく使うコマンドまとめ
- Monitoring 起動
  - MONITOR_POLL_INTERVAL を指定して実行:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動 (Paper Trading)
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- パッケージの自動 .env ロードを無効にする（テスト時等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -m your_test

---

## 補足 / 運用上の注意
- OpenAI を利用する機能は API コストとレイテンシが発生します。実運用ではレート管理とエラーハンドリングに注意してください（モジュール内にバックオフ・リトライが組み込まれています）。
- データベーススキーマやマイグレーションは monitoring_db.init_monitoring_db が冪等に作成・変更しますが、本番運用ではバックアップ・移行手順を用意してください。
- psutil のプロセス優先度設定は OS に依存し、権限がないと設定できない場合があります（ログに警告が出ます）。
- Streamlit ダッシュボードは SQLite を読み取り専用で開くため、MonitoringEngine が DB を保持している間は URI 経由で読み取り専用オープンすることを推奨します（スクリプト内で実装済み）。

---

README に書かれている内容で足りない情報や、具体的なセットアップ（requirements.txt 作成や Docker 化、ユニットテストの追加など）をご希望でしたら詳細を教えてください。必要であれば .env.example のテンプレートや systemd / supervisor 用の起動スクリプト例も作成できます。