# KabuSys

日本株向けの自動売買システム試作実装です。  
このリポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース NLP などのモジュールを含み、実運用に近い設計思想で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された日本株自動売買システムです。

- Execution（発注・注文管理・リコンシリエーション）
- Monitoring（システム状態・注文滞留・リスク監視・アラート）
- Portfolio（銘柄選定、重み付け、株数算出、リスク調整）
- Research（ファクター計算、特徴量解析、IC 評価）
- AI（ニュースセンチメント算出・市場レジーム判定）
- Tools（検証レポート、ダッシュボード起動スクリプトなど）
- Utils（プロセス優先度設定など OS 周りユーティリティ）

設計方針の一部:
- DuckDB/SQLite をローカルに保持してデータ処理・ログ永続化を行う
- Paper Trading と Live の DB を分離（環境変数 KABUSYS_ENV）
- 外部 API（OpenAI など）呼び出しはリトライやフォールバックを備える
- ルックアヘッドバイアス対策（date.today() 等の直接参照を避ける設計）

---

## 主な機能一覧

- 発注ワークフロー（OrderManager / OrderRepository）
  - OrderCreated → OrderSent → OrderAccepted 等の状態遷移管理
  - ブローカー同期・再起動時の自動リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
  - ドローダウン検出、ポジション上限監視、リスクログ出力
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留、約定価格の異常検出
  - MonitoringEngine: 各モニタのポーリングとアラート発行
  - AlertManager: LINE Push による一方向通知（設定がある場合）
  - KillSwitch: フラグファイル（data/kill.flag）で ExecutionEngine 停止シグナル発行
  - Streamlit ダッシュボード (data/monitoring.db の読み取り専用ビュー)
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア加重配分、リスクベースの株数算出
  - セクターキャップ、レジームに基づく投下資金乗数
- リサーチ（research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI（ai）
  - news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント算出 → ai_scores へ保存
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して market_regime に書き込み
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: Monitoring DB を可視化するダッシュボード

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型などを使用）
- OS により psutil の優先度設定権限が必要な場合があります（Linux の nice 値変更や Windows の権限）

1. リポジトリをクローン
   - git clone <このリポジトリ>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai requests streamlit
   - （実際のプロジェクトでは requirements.txt を用意して `pip install -r requirements.txt` を推奨）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数は上書きされません）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数例（.env）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=... (必須)
   - KABU_API_PASSWORD=... (必須)
   - OPENAI_API_KEY=... (AI 機能を利用する場合)
   - LINE_CHANNEL_ACCESS_TOKEN=... (AlertManager を使う場合)
   - LINE_USER_ID=... (AlertManager を使う場合)
   - SQLITE_PATH=data/monitoring.db (監視用 DB、デフォルト)
   - DUCKDB_PATH=data/kabusys.duckdb (時系列・ファクタ DB、デフォルト)
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (paper_trading 用 DB)
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE=instant|partial|never|reject

5. データディレクトリ作成
   - mkdir -p data

注意:
- paper_trading 環境では Execution は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存され、本番 DB と分離されます。

---

## 使い方

主な起動例・使い方を示します。

1. Execution（取引エンジン）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を用いた検証モードとなり、paper_trading 用の SQLite に記録されます。
   - 実行時にプロセス優先度が "high" に設定されます（プラットフォーム制約で失敗する場合は警告ログ）。

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
     例: export MONITOR_POLL_INTERVAL=30
   - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）へ永続化します（監視用 DB は常に本番 sqlite_path を使用）。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を指定する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

4. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - Monitoring DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

5. AI 関連
   - ニューススコアリング（programmatic）
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - OPENAI_API_KEY 環境変数を設定しておくか、api_key 引数を渡します。
   - レジームスコア算出
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

6. Kill Flag（実行停止）
   - kill_flag は Settings.kill_flag_path（デフォルト data/kill.flag）に書き込まれると ExecutionEngine が停止する設計になっています。
   - KillSwitch が発動するとファイルに理由が書き込まれます。手動で削除するには:
     - rm data/kill.flag
   - ExecutionEngine 起動時に kill_flag の自動消去を有効にする設定（Settings.kill_flag_clear_on_start）があります。

---

## 主要な設定（Settings の解説）

Settings（kabusys.config.Settings）は環境変数を読み込み、以下のようなプロパティを提供します（一部抜粋）:

- jquants_refresh_token (必須)
- kabu_api_password (必須)
- kabu_api_base_url (デフォルト http://localhost:18080/kabusapi)
- line_channel_access_token, line_user_id (通知用)
- duckdb_path (デフォルト data/kabusys.duckdb)
- sqlite_path (デフォルト data/monitoring.db)
- paper_sqlite_path (デフォルト data/paper_trading.db)
- paper_fill_mode (instant|partial|never|reject)
- pid_file_path, kill_flag_path
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- KABUSYS_ENV: development | paper_trading | live

.env 自動読み込みのルール:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して、`.env`、`.env.local` を順にロードします。
- OS 環境変数は保護され、.env が上書きしません（ただし .env.local は override=True でロードされます）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

主要ファイルと役割（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/
  - execution_engine.py     — ExecutionEngine（起動ロジック） ※実装ファイルは省略ベース
  - broker_factory.py       — Broker クライアント生成
  - order_manager.py        — 発注ワークフロー（OrderManager）
  - order_repository.py     — 注文永続化（SQLite）
  - reconciler.py           — 再起動時の状態同期（Reconciler）
  - risk_manager.py         — 発注時リスク管理
  - order_record.py         — OrderRecord・OrderState（enum）
- src/kabusys/monitoring/
  - monitoring_db.py        — SQLite 監視ログ永続化層（init + MonitoringDB）
  - system_monitor.py       — システム状態・データ鮮度のチェック
  - trade_monitor.py        — 注文滞留 / 約定異常検出
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — フラグファイル生成（Execution 停止）
  - alert_manager.py        — LINE Push 通知
  - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py  — Streamlit ダッシュボード（読取専用）
- src/kabusys/portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数算出・スケール調整
  - risk_adjustment.py      — セクター上限、レジーム乗数
- src/kabusys/research/
  - factor_research.py      — Momentum/Volatility/Value 等ファクター計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- src/kabusys/ai/
  - news_nlp.py             — ニュース NLP（OpenAI）で銘柄スコアを算出
  - regime_detector.py      — マクロニュース + ETF MA200 によるレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py     — プロセス優先度 / CPU affinity セットユーティリティ

データファイル（デフォルト）
- data/kabusys.duckdb       — 時系列・ファクター DB（DuckDB）
- data/monitoring.db        — 監視ログ（SQLite）
- data/paper_trading.db     — Paper Trading 用 SQLite（分離）
- data/execution.pid        — ExecutionEngine の PID ファイル（存在でプロセス監視）
- data/kill.flag            — KillSwitch による停止指示ファイル

---

## トラブルシューティング / 注意点

- OpenAI API を利用する機能は OPENAI_API_KEY の設定が必要です。未設定の場合は関連関数が ValueError を投げます。
- psutil による優先度設定や CPU affinity は OS 権限に依存します。権限不足の際はログに警告が出ますがプロセスは継続します。
- Monitoring は常に Settings.sqlite_path（本番 DB）を参照します。paper_trading のみ分離されるのは Execution 側の DB です。
- DuckDB の操作や executemany に関してはバージョン依存の注意（コード中に互換性対策あり）。
- kill.flag は存在する限り ExecutionEngine による起動を阻害または停止させるトリガーとなります。手動で削除することで解除できます。

---

もし README に追加したい内容（詳細な API ドキュメント、実行時のログ例、CI 設定、requirements.txt など）があれば指示ください。必要に応じてサンプル .env.example も作成できます。