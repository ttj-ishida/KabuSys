# KabuSys

日本株向けの自動売買・調査プラットフォームの一部を実装したコードベースです。ポートフォリオ構築、注文実行・再同期、監視（アラート・キルスイッチ）、ファクター計算、ニュース NLP（OpenAI 経由）のスコアリング、Paper Trading 検証ツールなどの機能を含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文の生成・管理・発注（Execution）
- 再起動時のリコンシリエーション（Reconciler）
- リスク管理（RiskManager）と監視（Monitoring）
- 監視データ永続化（SQLite）とダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- 研究（ファクター計算、将来リターン、IC、統計サマリ）
- ニュース NLP による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF MA + マクロセンチメント）
- Paper Trading 向けの検証レポート生成ツール

設計上のポイント:
- DuckDB をデータ分析（prices_daily / raw_financials 等）に利用
- 監視ログは SQLite（data/monitoring.db）へ永続化
- Paper Trading は本番 DB と分離して `data/paper_trading.db` を利用可能
- 外部 API（OpenAI 等）はキーを環境変数または引数で注入

---

## 機能一覧

- Execution
  - OrderManager: 注文作成 / 発注 / 同期
  - Reconciler: 再起動後の注文・ポジション突合
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（MockBrokerClient を使用、DB 分離）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス有無、データ鮮度を監視
  - TradeMonitor: 滞留注文、約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とイベント記録
  - KillSwitch: 条件により ExecutionEngine 停止フラグ（kill.flag）を書き込み
  - AlertManager: LINE Push による通知（クールダウン機能付）
  - MonitoringEngine / run_monitoring.py: ポーリングループで監視を実行
  - SQLite による監視ログ（monitoring_db.py）

- Research / Portfolio
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC、統計サマリ
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限・レジーム調整

- AI
  - news_nlp: raw_news から銘柄別のセンチメントスコアを OpenAI で算出し ai_scores に保存
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定（OpenAI を使用）

- Tools
  - paper_verification_report: Paper Trading データからの検証レポート（稼働率・成功率・レイテンシ等）
  - streamlit_dashboard: 監視データの簡易ダッシュボード

---

## 必要条件（推奨）

- Python 3.9+
- 必要な外部パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード使用時)
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI / LINE API を利用する場合）

（実際の requirements.txt はリポジトリに合わせて用意してください。例: `pip install duckdb psutil openai requests streamlit`）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - あるいは個別に: pip install duckdb psutil openai requests streamlit

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。
   - 主要な環境変数（一部、デフォルト値や必須性に注意）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (news_nlp / regime_detector で使用)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信用; 空なら送信はスキップ)
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - SQLITE_PATH (監視DB, デフォルト: data/monitoring.db)
     - DUCKDB_PATH (DuckDB ファイル, デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (Paper Trading DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の約定挙動: instant|partial|never|reject; デフォルト: instant)
     - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト: 60)
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値 等（Settings クラス参照）

5. データディレクトリ
   - デフォルトの DB 等は `data/` を使用します。必要に応じてディレクトリを作成してください。
   - 例: mkdir -p data

注: run_* スクリプトは起動時に監視用 DB テーブルを自動で初期化（冪等）します（init_monitoring_db）。

---

## 使い方（主要コマンド例）

- 監視ループを起動（監視は常に production sqlite_path を使用）
  - 環境変数でポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py
  - 特記事項:
    - run_monitoring は起動時にプロセス優先度を "high" に設定を試みます（psutil を使用）。
    - 停止は Ctrl+C、またはプロジェクトルート `data/stop_requested.flag` ファイルを作成すると次回ポーリングで終了します。

- ExecutionEngine を起動
  - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading 時は MockBrokerClient が使用され、専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行中は `data/execution.pid`（デフォルト）に PID を書きます。停止フラグは `data/stop_requested.flag`、kill.flag は KillSwitch によって書かれます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合: --db path/to/paper_trading.db
  - レポートは稼働率・注文成功率・送信率・レイテンシなどを出力します。

- Streamlit ダッシュボード（監視ビュー）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードからポートフォリオ値・オープンポジション・最近の注文・最新システムステータス等を確認できます（読み取り専用推奨）。

- AI モジュールの利用（プログラム的）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="xxxx")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="xxxx")

---

## 監視・停止の仕組み（概略）

- stop_requested.flag（data/stop_requested.flag）:
  - run_monitoring / run_execution のループ内でチェック。存在するとループを終了します（外部からの停止要求）。

- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が条件（ドローダウン超過等）に合致した際に作成します。ExecutionEngine 側は起動時や定期監視でこのフラグを検知して安全停止を行います。
  - KillSwitch.clear() を使ってフラグを削除できます（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定して自動クリアする運用も可能）。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine など) — 発注/同期関連
    - reconciler.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - ... （BrokerFactory, risk_manager 等）
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
  - data/ (実行時に利用するディレクトリ; DB / pid / flag 等)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (DuckDB)
    - paper_trading.db (paper_trading 用)

（上記はリポジトリ内ファイルを抜粋したもので、他にも補助モジュールが存在します。）

---

## 開発上の注意点 / 運用メモ

- 環境（KABUSYS_ENV）:
  - development / paper_trading / live の3種。`Settings.env` で検証される。
  - run_monitoring はドキュメントにもある通り「環境にかかわらず本番 sqlite_path を使用」する点に注意。

- DB 初期化:
  - monitoring 用テーブルは起動時に `init_monitoring_db()` で作成（マイグレーションも簡単なものは含む）。

- OpenAI / LINE など外部 API:
  - API キーやトークンが未設定の場合、多くの機能はフェイルセーフ（ログ出力して処理を継続）を採用していますが、NLP/レジーム機能や通知は実行されません。

- 権限:
  - set_process_priority や CPU affinity の設定は権限が必要な場合があります。権限不足時は警告を出してスキップします。

---

## 参考コマンドまとめ

- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースの主要点を簡潔にまとめたものです。詳細（各モジュールの引数や内部実装、追加の運用手順等）は該当ソースファイルの docstring / コメントを参照してください。必要であれば README にインストール手順（requirements.txt の具体化）や運用ガイド（systemd ユニット例、ログローテーション、バックアップ方針等）を追加します。