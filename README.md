# KabuSys

KabuSys は日本株の自動売買システムのコードベースです。本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および一部の AI 補助機能（ニュースセンチメント／レジーム判定）を含みます。

以下はこのコードベースの概要、機能、セットアップ方法、使い方、およびディレクトリ構成の説明です。

---

## プロジェクト概要

- 日本株自動売買のためのモジュール群（Execution / Monitoring / Portfolio / Research / AI）。
- SQLite（監視ログ等）および DuckDB（時系列価格・財務データの分析）を使用。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）環境を切り替え可能。
- LINE によるアラート通知、OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価・レジーム検出機能を備える。
- フラグファイルによる安全停止（kill flag / stop flag）やプロセス優先度設定など、運用を意識した設計。

---

## 主な機能一覧

- Execution（発注周り）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - OrderManager / OrderRepository / Reconciler による状態管理・再同期
  - paper_trading 時は MockBrokerClient を使い DB を分離

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db.init_monitoring_db）
  - LINE でのアラート送信（AlertManager）
  - kill.flag を書き込む KillSwitch による実行エンジン停止トリガー
  - Streamlit ベースの監視ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- ポートフォリオ構築
  - 候補選定、重み計算（等重／スコア重み）、ポジションサイズ計算、セクター制約など
  - 純粋関数群で副作用なし（kabusys.portfolio）

- リサーチ / ファクター計算
  - モメンタム／ボラティリティ／バリューなどのファクター計算（DuckDB を利用）
  - 将来リターン計算・IC 計算・統計サマリー等のユーティリティ

- AI 関連
  - ニュースをまとめて OpenAI に投げセンチメントスコアを ai_scores テーブルへ格納（kabusys.ai.news_nlp）
  - マクロニュース + ETF ma200 を合成して市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI 呼び出しは冪等・フェイルセーフなリトライロジックを持つ

- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
  - その他開発／運用支援スクリプト

---

## 事前準備（推奨）

- Python 3.10 以上（新しい型記法（X | Y）等を使用しているため）
- 必要なパッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- 典型的なインストール例:
  - python -m pip install duckdb psutil requests openai streamlit

（リポジトリに requirements.txt があればそちらを使用してください。）

---

## 環境変数（主要なもの）

config.py で多くの設定を環境変数から読み込みます。主なキー:

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動読み込みを無効化

- API トークン
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合必須）
  - LINE_CHANNEL_ACCESS_TOKEN（通知用、任意）
  - LINE_USER_ID（通知用、任意）

- データベース / パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- Paper Trading 関連
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- Monitoring 関連
  - MONITOR_POLL_INTERVAL（秒） — run_monitoring でポーリング間隔を上書き可能（デフォルト: 60）

- ログ
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

注意: .env / .env.local をプロジェクトルートに置くと自動読み込みされます（ただし OS 環境変数は保護される）。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存ライブラリをインストール
   - python -m pip install -r requirements.txt   （存在する場合）
   - 又は: python -m pip install duckdb psutil requests openai streamlit

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポートしてください。
   - 例（.env）:
     - KABUSYS_ENV=paper_trading
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

4. データディレクトリ作成
   - mkdir -p data

5. 初回起動時、Monitoring DB の初期化は run_monitoring / run_execution 内で自動的に行われます（init_monitoring_db を呼び出します）。

---

## 使い方（起動・主要コマンド）

- Execution Engine を起動（本番・paper_trading に応じて挙動が変わります）
  - python -m kabusys.run_execution
  - プロセス優先度を High に設定し、PID ファイル（data/execution.pid）を利用します。
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録されます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。例: export MONITOR_POLL_INTERVAL=30

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、ポジション/オーダー/システム状態を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（プログラム的に呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...") など
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 停止フラグ / キル
  - 実行中のエンジンを停止させたい場合、data/kill.flag に理由を書き込む（KillSwitch を通して自動生成もされます）。
  - また run_* スクリプトはプロジェクトルートの data/stop_requested.flag が存在すると安全に停止します。

---

## 運用上の注意

- paper_trading 環境では本番 DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しやブローカー API 呼び出しはリトライ・フェイルセーフの実装がありますが、API キーやネットワークの設定は必ず確認してください。
- PID ファイルや flag ファイル（data/execution.pid, data/kill.flag, data/stop_requested.flag）を使ってプロセスの状態管理・停止を行います。これらのファイルは適切に管理してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動読み込みロジック含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント評価（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
- execution/
  - order_manager.py, reconciler.py, ... — 発注管理、再同期ロジック等
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル定義・マイグレーション）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 管理
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター・リサーチ関連
- tools/
  - paper_verification_report.py — Paper Trading 検証レポートツール
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/  （実行時に作成されるファイル群）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（paper_trading 用 DB）
  - kabusys.duckdb（DuckDB データベース）
  - execution.pid, kill.flag, stop_requested.flag など

---

## 主要テーブル（monitoring DB）

init_monitoring_db により作成される主要テーブル（監視用）:

- system_status (cpu_percent, memory_percent, disk_percent, process_ok, recorded_at)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の集計行: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

---

## 開発・拡張メモ

- DuckDB を使ったファクター計算は SQL + Python を組み合わせて高速に実行する設計です。prices_daily / raw_financials テーブルを前提とします。
- AI 呼び出し周りはテスト容易性を考慮して内部呼び出し箇所をモックしやすい構造になっています（_call_openai_api を patch する等）。
- ポートフォリオ構築・ポジション決定ロジックは純粋関数で設計されているためユニットテストが書きやすいです。

---

## よくある実行例

- 監視ループを 30 秒間隔で起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- ペーパートレード実行:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- レポート出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれている内容はコード内のドキュメンテーション（モジュール docstring）と整合しています。必要であれば、この README をベースに導入ガイド（.env.example のテンプレート、systemd / Supervisor のサービス定義例、より詳しい運用手順）を追加できます。どの情報を追加したいか教えてください。