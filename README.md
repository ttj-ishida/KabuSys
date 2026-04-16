# KabuSys

日本株向け自動売買システムの一部モジュール群。ポートフォリオ構築、ポジションサイズ計算、監視・アラート、実行エンジンの起動・リコンシリエーション、ニュースの AI スコアリング、リサーチ用ファクター計算などを含みます。

---

## プロジェクト概要

本リポジトリは KabuSys のコアロジックと補助ツール群を提供します。主な関心領域は以下です。

- 実行エンジン起動（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- 監視（MonitoringEngine）: システム状態、注文滞留、リスク（ドローダウン等）を定期チェックしログ保存・アラート発行
- ポートフォリオ構築: 候補選定、重み算出、ポジションサイズ決定、セクター制約
- リサーチ: ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析
- AI 関連: ニュース NLP によるセンチメントスコアリング、レジーム判定（OpenAI を使用）
- 運用用ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード

---

## 主な機能一覧

- Settings（環境変数経由の設定読み込み / .env 自動読込）
- Execution 起動用スクリプト（run_execution.py）
  - `paper_trading` 環境では MockBroker を使用、専用 SQLite を利用して本番 DB と分離
- Monitoring 起動用スクリプト（run_monitoring.py）
  - system / trade / risk のモニタを定期実行し SQLite にログ保存
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）
- Monitoring DB ラッパー（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理・簡易マイグレーション
- Kill Switch（kill_switch.py）
  - リスク条件で data/kill.flag を書き込み ExecutionEngine に停止シグナルを送信
- AlertManager（alert_manager.py）
  - LINE Messaging API へのプッシュ通知（クールダウン管理あり）
- Streamlit 監視ダッシュボード（streamlit_dashboard.py）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
- Portfolio ライブラリ（選定・重み・サイズ計算・リスク調整）
- Research（factor_research / feature_exploration）: DuckDB を利用したファクターや評価指標
- AI モジュール（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI を用いたニュースセンチメント評価・市場レジーム判定

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（typing の | 記法などを使用）
- SQLite（組み込み）、DuckDB、外部ライブラリが必要

推奨インストール（仮想環境を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

必要に応じて他の依存を追加してください（プロジェクトに requirements.txt があればそれを利用）。

環境変数
- 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — AI 機能で使用
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager の通知で使用
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し paper_trading 用 SQLite を使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視 / 制御用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

例（.env）:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

データディレクトリ
- data/ 配下に DB やフラグファイルを配置する設計です。
  - data/monitoring.db（監視用 SQLite、init_monitoring_db で自動作成）
  - data/paper_trading.db（paper_trading 用）
  - data/execution.pid（ExecutionEngine が書き込む PID）
  - data/kill.flag（KillSwitch により作成される停止フラグ）
  - data/stop_requested.flag（run_* スクリプトの外部停止フラグ）

---

## 使い方

一般的な起動・運用例を示します。

1. 監視ループ起動（Monitoring）
- デフォルトポーリング 60 秒:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- run_monitoring は Settings に従い、常に本番 sqlite_path を使用します（監視は実環境 DB を参照）。

2. 実行エンジン起動（Execution）
- デフォルト（KABUSYS_ENV に従う）:
  - python -m kabusys.run_execution
- paper_trading 環境で起動する例（MockBroker を使い DB を分離）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3. Paper Trading 検証レポート生成
- コマンドラインツール（SQLite を読みレポートを stdout に出力）:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4. Streamlit 監視ダッシュボード
- 起動コマンド（ドキュメントに合わせた起動例）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5. AI 機能（ニュース NLP / レジーム判定）
- プログラムから使用する場合（例）:
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from datetime import date
  - score_news(conn, date(2026, 4, 1), api_key="sk-...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026, 4, 1), api_key="sk-...")

注意点
- OpenAI API を使う機能は API キーが必須（環境変数 OPENAI_API_KEY または引数で指定）。
- paper_trading 環境では発注の挙動（fill モード等）を PAPER_FILL_MODE で制御できます。 有効値: instant | partial | never | reject

停止 / Kill
- 外部から ExecutionEngine を止めたい場合は data/kill.flag を書き込む（KillSwitch / ExecutionEngine が検知）。
- run_* スクリプトはプロジェクトルートの data/stop_requested.flag を検知して優雅に停止します（ファイルを作成するとループ終了）。

ログレベル
- LOG_LEVEL 環境変数で設定可能（DEBUG, INFO, WARNING, ERROR, CRITICAL）

---

## ディレクトリ構成

以下は main なファイル・パッケージの概観（src/kabusys 以下）。実際の tree は一部省略しています。

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
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository, order_record, broker_api など)
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
    - data/  (実行時に利用される想定ディレクトリ)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kabusys.duckdb (デフォルトパス)
      - execution.pid
      - kill.flag
      - stop_requested.flag

主要モジュール説明（短め）
- config.py: 環境変数読み込み・Settings クラス。`.env` / `.env.local` を自動読込（無効化可）。
- monitoring/monitoring_db.py: SQLite のテーブル作成・CRUD ヘルパー。監視ログ永続化。
- monitoring/system_monitor.py: CPU/メモリ/ディスク・プロセス生存・データ鮮度チェック。
- monitoring/trade_monitor.py: 注文滞留・約定価格異常の検出。
- monitoring/risk_monitor.py: ドローダウン・ポジション上限監視と dashboard 更新。
- monitoring/kill_switch.py: リスクトリガで kill.flag を作成。
- execution/order_manager.py: 発注ワークフローと重複チェック。
- execution/reconciler.py: 起動時の自動リコンシリエーション（注文照合・ポジション差分検出）。
- portfolio/*: 候補選定・重み付け・ポジションサイズ等の純粋関数群。
- research/*: DuckDB 上のファクター計算・評価ユーティリティ。
- ai/*: OpenAI を用いたニュースセンチメント、マクロセンチメント、レジーム判定。

---

## 運用上の注意・ベストプラクティス

- 実運用（live）では KABUSYS_ENV=live を設定し、API キーやパスワードは OS 環境変数で安全に管理してください。
- paper_trading を利用するときは PAPER_TRADING_SQLITE_PATH を確認し、本番 DB と分離されていることを確認してください。
- kill.flag / stop_requested.flag / execution.pid ファイルの扱いに注意。手動で削除する必要がある場合は状況を確認してから行ってください。
- OpenAI API 呼び出しはコストとレート制限に注意。ログや retry 実装はありますが運用ポリシーに従ってください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）と実際のデータの整合性に注意してください。research / ai モジュールはこれらを参照します。

---

この README はコードベースの機能と運用方法の概要を示しています。詳細な API や内部実装の仕様は各モジュールの docstring を参照してください。必要であればさらに導入手順（systemd ユニット、コンテナ化、テストの追加方法等）も追記できます。どの情報を優先して追記しますか？