# KabuSys

日本株自動売買システムの一部コードベース。ポートフォリオ構築、発注エンジン、監視、研究・ファクター計算、ニュースNLP（OpenAI）連携などのユーティリティ群を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の主要コンポーネントを提供します。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じた発注管理、注文状態同期、リスク管理。
- Monitoring（監視）: システム状態、注文滞留、約定異常、ドローダウン等の定期チェックとログ保存、LINE通知連携。
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ算出、セクター制約など。
- Research（調査）: ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン、IC 計算、統計サマリ。
- AI（ニュースNLP / レジーム検出）: raw_news を OpenAI API でスコア化して ai_scores に書き込む、マクロセンチメントとETF MA を合成して市場レジーム判定。

設計方針として、ルックアヘッドバイアス防止やフェイルセーフ（API失敗時のフォールバック）などが組み込まれています。

---

## 主な機能一覧

- システム監視（CPU/メモリ/ディスク、実行プロセス PID チェック、データ鮮度）
- 注文監視（滞留注文検出、約定価格異常検出）
- リスク監視（ドローダウン監視、ポジション上限監視、kill.flag による停止）
- LINE によるアラート通知（AlertManager）
- 発注マネジメント（OrderManager / OrderRepository）
- リコンシリエーション（Reconciler：起動時に注文・ポジションの突合）
- ポートフォリオ構築（候補選定、等重/スコア重み、リスクベースのポジションサイズ算出）
- Research：DuckDB を用いたファクター計算・将来リターン・IC・統計
- AI：OpenAI を用いたニュースセンチメント（score_news）およびレジーム判定（score_regime）
- Streamlit ダッシュボード（監視情報の可視化）
- Paper Trading モード（本番 DB と分離された専用 SQLite を使用）

---

## 前提 / 必要環境

- Python 3.10+
- SQLite（標準ライブラリ）
- DuckDB Python パッケージ
- psutil（プロセス優先度 / CPU affinity 用）
- requests（LINE API 呼び出し用）
- openai（OpenAI API を使う場合）
- streamlit（ダッシュボード起動用）

例（pip インストール）:
pip install duckdb psutil requests openai streamlit

（実プロジェクトでは requirements.txt を作成して pip install -r requirements.txt を推奨）

---

## セットアップ手順

1. リポジトリをクローンし、ワークディレクトリに移動
   - ソースは `src/` 配下に配置されている前提です。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置けます（自動読み込みされます）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨される主要環境変数（一部）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...（AI 機能使用時必須）
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
- PAPER_FILL_MODE=instant | partial | never | reject  （paper_trading 用）
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- MONITOR_POLL_INTERVAL=60  （監視ループの秒数）
- LOG_LEVEL=INFO

例 .env（最低限）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

5. データディレクトリを準備
   - data/ ディレクトリ（PID/flag/DB のデフォルト位置）を作成しておくと便利。
   - sqlite / duckdb ファイルは起動時に作成・初期化されます（init_monitoring_db を通じてテーブルが作られる）。

---

## 使い方（主な実行コマンド）

※ 以下はプロジェクトルート（src の親）で実行することを想定。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を常に使用します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード起動（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring DB に対して読み取り専用で開きます（起動中の MonitoringEngine が必要）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH （PAPER_TRADING_SQLITE_PATH の代替）

- AI（ニューススコア）の呼び出し（スクリプトや Python から）
  - 例（Python）:
    from datetime import date
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="your-openai-key")

- レジーム判定（AI ベース）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・強制停止に関するファイル:
- data/stop_requested.flag: run_execution/run_monitoring スクリプトはこのファイルの存在を検出して安全停止します（スクリプト内で参照）。
- data/kill.flag: KillSwitch により生成される停止フラグ。ExecutionEngine 起動時は Settings.kill_flag_clear_on_start により起動時に消去する設定も可能。

ログ出力:
- 各スクリプトは標準ログ（logging）を使用。環境変数 LOG_LEVEL で閾値を変更できます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主なファイルと役割）

- __init__.py
  - パッケージ定義 / バージョン

- config.py
  - 環境変数 / .env 読み込み、Settings クラス（各種パス・フラグ・しきい値など）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper_trading モードを分離）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- execution/
  - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, broker_factory.py, broker_api.py など
  - 発注ロジック、ブローカー抽象、再同期ロジック

- monitoring/
  - monitoring_db.py — SQLite テーブル初期化と読み書きラッパ
  - system_monitor.py — CPU/メモリ/ディスク、PID、データ鮮度
  - trade_monitor.py — 滞留注文・約定異常検知
  - risk_monitor.py — ドローダウン、ポジション上限
  - kill_switch.py — kill.flag 書き込み
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor の集約、ポーリング管理
  - streamlit_dashboard.py — Streamlit ベースの可視化

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・重み付け・株数計算・セクター制約

- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン、IC、統計ユーティリティ

- ai/
  - news_nlp.py — raw_news を OpenAI に送り銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py — ETF MA + マクロニュースで日次レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - （実行時に生成される SQLite / DuckDB ファイル、PID/flag ファイルなど）

---

## 注意事項・運用上のヒント

- Paper Trading は本番 DB と明確に分離されます。KABUSYS_ENV=paper_trading にすると paper_sqlite_path が使用されます。
- Monitoring は監視用 DB（Settings.sqlite_path）を常に使用します。運用時に監視が本番 DB を参照することを意識してください。
- OpenAI API を使用する機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはレート制限やネットワークエラーを考慮して実装されていますが、料金・利用制限に注意してください。
- kill.flag / stop_requested.flag / execution.pid 等のフラグファイルは手動で操作することが可能です。運用時はこれらのファイルの配置場所（data/）と削除タイミングに注意してください。
- streamlit ダッシュボードは読み取り専用で DB を開くため、MonitoringEngine が稼働していれば最新状態を参照できます。
- tests や CI で .env の自動読み込みを妨げたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はコードベースの概要説明です。各モジュールの詳細はソースの docstring を参照してください。特定の起動・運用手順や追加の依存関係については運用環境に応じて適宜ドキュメント化することを推奨します。