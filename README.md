# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を支援するPythonパッケージのサンプル実装です。本リポジトリは以下の主要機能群を提供します。

- 注文作成・送信・状態管理の Execution コンポーネント
- ポートフォリオ構築・ポジションサイズ決定 (等配分 / スコア重み / リスクベース)
- ファクター計算・リサーチユーティリティ（モメンタム、バリュー、ボラティリティ等）
- ニュースを用いた LLM ベースのセンチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF + マクロニュース + LLM）
- 監視（System / Trade / Risk）とアラート（LINE Push）
- 監視ダッシュボード（Streamlit）
- Paper Trading の検証レポート生成スクリプト

この README では概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は以下の設計方針で構築されています。

- ビジネスロジックと永続化層（SQLite / DuckDB）を分離
- 多くの機能は純粋関数設計（副作用を最小化）でテストしやすい実装
- Paper Trading 環境は本番 DB と分離（data/paper_trading.db）
- ニュース解析・レジーム判定は OpenAI API を使用（失敗時はフェイルセーフ）
- 監視は SQLite にログを残し、Streamlit で可視化可能

---

## 機能一覧

- Execution
  - 注文ライフサイクル管理（OrderManager、OrderRepository）
  - ブローカー抽象化（BrokerClientFactory）
  - 起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Portfolio
  - 候補選択（select_candidates）
  - 重み計算（等配分・スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター制限・レジーム乗数の適用
- Research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite のスキーマ初期化と CRUD）
  - KillSwitch（フラグファイルによる ExecutionEngine 停止）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - Streamlit ダッシュボード（監視、ポジション、注文、システムステータス）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要な環境・依存

- Python 3.10+
  - （型ヒントに | 演算子等を使用しているため 3.10 以上を推奨）
- 主な依存パッケージ（実際の requirements.txt を用意する場合は適宜記載してください）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ）
- ネットワークアクセス（LINE API / OpenAI を使う場合）

---

## 環境変数（主なもの）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須または重要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient が使用され、Paper DB（data/paper_trading.db）へ記録されます
- PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject、デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — Execution PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）

ログレベル等:
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

監視しきい値（任意上書き可能）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

---

## セットアップ手順（例）

1. リポジトリをクローン / 移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （実際は requirements.txt を用意して pip install -r requirements.txt を推奨）
4. .env をプロジェクトルートに作成して必要な環境変数を設定
   - 例: .env:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=paper_trading
5. 初回実行時は data ディレクトリ等を作成しておく（自動作成される箇所もありますが手動作成を推奨）
   - mkdir -p data

---

## 使い方（主要スクリプト / コマンド）

以下は典型的な起動例です。パッケージはモジュールとして起動できます（python -m kabusys.<module>）。

- ExecutionEngine を起動する（本番 / paper_trading を KABUSYS_ENV で切替）
  - 環境変数例:
    - export KABUSYS_ENV=paper_trading
    - export PAPER_FILL_MODE=instant
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB とは分離）
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）

- Monitoring（ポーリング監視）を起動する
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 実行:
    - python -m kabusys.run_monitoring
  - 挙動:
    - Settings.sqlite_path（デフォルト data/monitoring.db）に接続し、監視ログを永続化
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視は常に同一 DB）

- Streamlit ダッシュボード（監視用）
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで表示されるダッシュボードからポートフォリオ値、ポジション、注文ログ、システム状態、リスクイベントを確認できます。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 日付指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パス指定:
      - python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

- AI 関連（OpenAI を使う機能）
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（引数で渡すことも可）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらはモジュール関数として呼び出す想定です（CLI エントリは用意されていないためスクリプトから呼ぶか、小さなラッパーを用意してください）。
  - API 呼び出しは 429 / タイムアウト / 5xx をリトライするロジックを持ちますが、キー未設定時は例外を送出します。

---

## 監視 / 制御関連のポイント

- kill.flag（デフォルト: data/kill.flag）
  - RiskMonitor や KillSwitch によって書き込まれ、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は起動時に kill.flag を削除する設定（KILL_FLAG_CLEAR_ON_START）があります。
- PID ファイル（デフォルト: data/execution.pid）
  - ExecutionEngine が起動時に書き込む想定のファイル。SystemMonitor はこのファイルが存在し、PID が生存しているかを確認します。stale PID は削除され、リスクイベントが記録されます。
- 監視は MonitoringDB（SQLite）に下記テーブルを作成します（init_monitoring_db により冪等に作成）
  - system_status, trade_logs, positions, risk_logs, dashboard

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル構成です（抜粋）。実際のリポジトリにはさらにファイルが含まれる場合があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み / Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — レジーム判定（ETF + マクロ + LLM）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー / repository / engine 実装が存在)
  - utils/
    - process_priority.py    — プロセス優先度・CPU Affinity 設定ユーティリティ

---

## 開発上の注意点 / 補足

- Python のバージョンは少なくとも 3.10 以上を想定しています（型ヒントで | を使用）。
- OpenAI の呼び出しは外部 API のため料金やレート制限に注意してください。APIキーは必ず環境変数か引数で渡してください。
- Paper Trading は本番 DB と完全分離されるよう設計されています。paper_trading モードでは PAPER_TRADING_SQLITE_PATH を使用します。
- Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV に依存しません）。
- process priority / CPU affinity の変更は OS の権限に依存します。権限不足の場合は警告を出してスキップします。
- Streamlit ダッシュボードは SQLite を読み取り専用で開くことを推奨します（起動オプションで ?mode=ro を付与）。

---

## よくある操作例（短いクイックスタート）

1. 環境変数設定（例）
   - export JQUANTS_REFRESH_TOKEN=xxxxx
   - export KABU_API_PASSWORD=yyyyy
   - export OPENAI_API_KEY=zzzzz
   - export KABUSYS_ENV=paper_trading

2. Execution 起動（PaperTrading）
   - python -m kabusys.run_execution

3. Monitoring 起動（別プロセス）
   - export MONITOR_POLL_INTERVAL=60
   - python -m kabusys.run_monitoring

4. Streamlit 監視ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5. PaperTrading レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

もし README に追加したい内容（例: 実際の requirements.txt、CI / テスト手順、より詳細なデプロイ手順、運用チェックリストなど）があれば教えてください。必要に応じて追記・拡張します。