# KabuSys

軽量な日本株自動売買フレームワークのリポジトリ（抜粋）。  
本 README は提供されたコードベースに基づく使い方・構成の説明です。

---

## プロジェクト概要

KabuSys は、日本株向けの自動売買・モニタリング・リサーチ機能を持つモジュール群です。主な責務は次の通りです。

- ExecutionEngine：注文の発行・管理・リコンシリエーション（ブローカー API 統合）
- Monitoring：システム稼働監視、注文監視、リスク監視、アラート（LINE）送信、Kill Switch
- Portfolio：銘柄選定・重み計算、ポジションサイジング、セクター制約・レジーム補正
- Research：DuckDB を利用したファクター計算・特徴量探索
- AI：ニュース N LU によるセンチメント算出（OpenAI）・市場レジーム判定
- Tools：Paper Trading の検証レポート生成、監視用 Streamlit ダッシュボード など

設計上の特徴：
- 本番用 DB と Paper Trading の DB を分離して動作可能
- .env / .env.local による環境変数自動ロード（任意で無効化可）
- OpenAI を使った NLP 機能はフェイルセーフに設計（API 失敗時は安全側にフォールバック）

---

## 機能一覧（主なモジュール）

- run_execution.py
  - ExecutionEngine 起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い、Paper 専用 SQLite に記録。
  - 起動時にプロセス優先度を上げる（psutil 使用）。
  - stop フラグファイルで安全停止。
- run_monitoring.py
  - SystemMonitor ポーリングループを起動。MONITOR_POLL_INTERVAL で間隔指定（デフォルト 60 秒）。
  - 監視ログは sqlite（monitoring.db）に永続化。
- monitoring/*
  - SystemMonitor / TradeMonitor / RiskMonitor：各種チェックと永続化（monitoring_db）
  - KillSwitch：条件が揃うと data/kill.flag を書き込み、ExecutionEngine 停止を誘発
  - AlertManager：LINE Push API による通知（クールダウンあり）
  - streamlit_dashboard.py：監視 DB を可視化する Streamlit アプリ
- execution/*
  - OrderManager / Reconciler / RiskManager 等：注文管理・再同期・リスク管理
- portfolio/*
  - 銘柄選定・重み付け・ポジションサイズ計算・レジーム乗数・セクター制限
- research/*
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計サマリー
- ai/*
  - news_nlp.score_news：raw_news から銘柄別センチメントを計算し ai_scores に書き込み（OpenAI）
  - regime_detector.score_regime：ETF MA とマクロニュースで日次レジーム判定（OpenAI）
- tools/paper_verification_report.py
  - Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

---

## 必要依存パッケージ（代表）

最低限必要な主なパッケージ（環境によってバージョン選定してください）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit

例:
pip install duckdb psutil requests openai streamlit

（requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. プロジェクトルートに `.env`（必要な環境変数）を作成（自動読み込みされます）
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

.env の例:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

---

## 主な環境変数（重要）

- KABUSYS_ENV: 起動モード（development, paper_trading, live）
  - paper_trading の場合、Broker は Mock を使用し DB は PAPER_TRADING_SQLITE_PATH に分離される
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須: 使う機能に依存）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須: 実ブローカー使用時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant/partial/never/reject）

---

## 使い方（実行例）

- ExecutionEngine を起動（production/paper を切り替えるには KABUSYS_ENV を設定）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

  細かい挙動:
  - 起動時に data/stop_requested.flag があれば起動を中止
  - 実行中に stop flag が書かれると終了処理を行う
  - paper_trading 時は専用 DB（PAPER_TRADING_SQLITE_PATH）に記録

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔。MONITOR_POLL_INTERVAL に 0 や負の値を与えるとデフォルトにフォールバック。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db PATH` で DB を指定可能。デフォルトは data/paper_trading.db

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 機能（スクリプトから直接呼ぶ）
  - ニューススコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  いずれも OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / .env 自動ロード / Settings
- run_execution.py                 — ExecutionEngine 起動スクリプト
- run_monitoring.py                — SystemMonitor ポーリング起動スクリプト

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py            —（存在は示唆されるが抜粋では省略）
  - broker_factory.py
  - broker_api.py
  - order_record.py
  - risk_manager.py
  - ...

- monitoring/
  - monitoring_db.py                — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
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

- utils/
  - process_priority.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

その他:
- data/                            — 実行時生成: monitoring / paper DB、pid、flag ファイル 等

---

## 主要ファイルと役割（ポイント）

- config.py
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数が優先）
  - Settings クラス経由で設定値にアクセス

- monitoring/monitoring_db.py
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブル作成とマイグレーション同期
  - MonitoringDB はログ追記 / upsert / risk イベントの de-dup 等のユーティリティを提供

- monitoring/kill_switch.py
  - リスク検出時に data/kill.flag を書き込み、Execution を止める仕組みを提供

- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI を使ったセンチメント評価・レジーム判定。API エラーや非 200 をフェイルセーフで扱う実装

- utils/process_priority.py
  - psutil を使いプラットフォーム差異を吸収してプロセス優先度や CPU affinity を設定

---

## 運用上の注意点

- DB 間の分離:
  - paper_trading モードはデフォルトで data/paper_trading.db を使い、本番用 monitoring.db とは分離されます。Paper 用 DB を本番環境に誤って接続しないよう注意してください。
- フラグファイル:
  - data/stop_requested.flag, data/kill.flag, data/execution.pid などでプロセスの起動／停止を制御します。手動で削除すると再起動などに影響を与えます。
- OpenAI 利用:
  - API キーは必須。API 呼び出しはレート制限・ネットワーク断・5xx を考慮したリトライロジックがありますが、コスト管理と失敗時挙動を理解して運用してください（失敗時は安全側のフォールバックが採られます）。
- 権限:
  - プロセス優先度の設定や CPU affinity の変更はプラットフォーム依存で権限が必要となる場合があります（特に nice の負値など）。

---

## 開発者向けメモ

- 設定は Settings() を介してアクセスしてください（直接 os.environ を参照するよりテストしやすい）。
- DuckDB 接続は読み取り専用でパスを URI で指定すると Streamlit 等の同時アクセスに便利（例: sqlite の場合は URI mode=ro）。
- テスト時に .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

疑問点や追加で README に載せたい情報（例: 実際の依存バージョン、CI 手順、運用 runbooks）があれば教えてください。必要に応じて README を拡張して CI/デプロイ手順や運用チェックリストも作成します。