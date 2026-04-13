# KabuSys

KabuSys は日本株向けの自動売買・研究・監視基盤ライブラリです。  
本リポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などの機能を含みます。

以下はこのコードベースの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は以下を主目的としたモジュール群を提供します。

- 自動売買の実行基盤（ExecutionEngine、Order 管理、ブローカ抽象化）
- 監視機構（System / Trade / Risk の監視、アラート送信、kill-switch）
- ポートフォリオ構築（銘柄選定、重み算出、ポジションサイズ計算、セクター制限）
- 研究向けファクター計算（モメンタム・ボラティリティ・バリュー等）
- AI を使ったニュースセンチメント評価と市場レジーム判定（OpenAI を利用）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計上の特徴：
- DB（SQLite / DuckDB）を使ったローカル永続化
- 環境切替（development / paper_trading / live）
- フェイルセーフ（API失敗時のフォールバックやリトライ、冪等操作）
- プロセス優先度設定・CPU affinity のユーティリティ

---

## 主な機能一覧

- 実行（run_execution.py）
  - 環境に応じて MockBroker / 本番ブローカーを切り替え
  - Paper Trading は専用 SQLite に完全分離
  - Reconciler による起動時の注文・ポジション同期

- 監視（run_monitoring.py, MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じてフラグファイルを書き ExecutionEngine を停止させる
  - AlertManager: LINE Messaging API による通知（クールダウン機構あり）
  - Streamlit ダッシュボード（read-only モードで monitoring DB を表示）

- ポートフォリオ（kabusys.portfolio）
  - 銘柄選定、等分配／スコア加重、リスクベースサイズ計算、セクター制限、レジーム乗数

- 研究（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（kabusys.ai）
  - ニュースを LLM（OpenAI）で評価して ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA200 乖離から日次レジーム（bull/neutral/bear）を判定

- ツール
  - paper_verification_report: Paper Trading DB を読み検証レポートを生成

---

## セットアップ手順

前提：
- Python 3.9+（プロジェクト要求に合わせて適宜調整）
- SQLite（標準で同梱）
- DuckDB（Python パッケージ）

1. リポジトリをクローン／チェックアウトする

2. 仮想環境を作成して有効化
   - Linux / macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール（例）
   pip install duckdb psutil openai requests streamlit

   補足（推奨）:
   - duckdb: 研究・ファクター計算用
   - psutil: プロセス情報・優先度設定
   - openai: LLM 呼び出し
   - requests: LINE 通知
   - streamlit: ダッシュボード

4. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   自動読み込みを無効にするには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   代表的な環境変数（例）:
   - KABUSYS_ENV=development|paper_trading|live
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - OPENAI_API_KEY=sk-xxxx
   - LINE_CHANNEL_ACCESS_TOKEN=xxxxx
   - LINE_USER_ID=Uxxxxxxxxxxxx
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60

5. データディレクトリ作成
   デフォルトは `data/` 以下を使用します。事前に作っておくと良いです:
     mkdir -p data

---

## 使い方

基本的な起動とツールの利用方法を示します。

- 実行エンジン（ExecutionEngine）起動
  - 本番／開発共通:
    python -m kabusys.run_execution
  - KABUSYS_ENV を切り替えると挙動が変わります:
    - development: 開発モード（制約あり）
    - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番ブローカーと接続

  起動時にプロセス優先度が "high" に設定されます（set_process_priority を使用）。

- 監視ループ起動
  python -m kabusys.run_monitoring

  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に production sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  ダッシュボードは monitoring DB を read-only で開きます。MonitoringEngine を先に起動してデータを投入してください。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

  レポートは uptime（稼働率）、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定します。

- AI モジュール（プログラムから利用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")
    - conn: duckdb connection（kabusys.data で作成した DuckDB 接続）
    - target_date: date オブジェクト（評価対象日）
    - api_key: OpenAI API キー（省略時は OPENAI_API_KEY 環境変数を参照）

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

  どちらも OpenAI API の呼び出しを行うため API キーが必要です。API 呼び出し失敗時はフェイルセーフ（例: macro_sentiment=0）で継続する設計です。

---

## 環境設定の注意点

- .env のパースは独自実装を備え、コメント、クォート、export 形式に対応します。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行います。
- KABUSYS_ENV の有効値: development, paper_trading, live
- Paper Trading の DB はデフォルト `data/paper_trading.db`。実際の取引 DB と分離されます。
- Monitoring は常に Settings.sqlite_path（デフォルト `data/monitoring.db`）を使用します。
- kill.flag（Settings.kill_flag_path）を監視・書き込みする仕組みがあります。ExecutionEngine はこのファイル存在を停止トリガーとして利用します。

---

## ディレクトリ構成（主要ファイルと概要）

以下は主要なモジュール配置と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数と Settings クラス（自動 .env ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py — 実行エンジン（起動・セッション管理）※詳細実装は本ベースに一部存在
  - order_manager.py — 発注ワークフロー（作成 → 送信 → 同期）
  - reconciler.py — 起動時の注文・ポジション同期
  - order_repository.py / order_record.py — DB レコード操作・Order 型定義
  - broker_factory.py / broker_api.py — ブローカー抽象・ファクトリ（Mock / 実装切替）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込み/クリア
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数決定・投下資金上限適用
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Value / Volatility 算出（DuckDB 使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリ等

- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメント評価（OpenAI）
  - regime_detector.py — ETF MA200 + マクロニュースでレジーム判定（OpenAI）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading DB の検証レポート生成ツール

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity セットユーティリティ

---

## 実運用上の補足

- DB マイグレーション: MonitoringDB の init 関数は既存 DB に対しても安全にカラム追加（例: peak_value, latency_ms）を行います。
- 冪等性: 多くの書き込み（dashboard upsert、market_regime 等）は冪等に設計されています（BEGIN/COMMIT/ROLLBACK を適宜使用）。
- フェイルセーフ: OpenAI API 呼び出しやブローカー API の一時障害に対してリトライや安全なフォールバックが入っています。
- ロギング: 各モジュールで標準的な logging が使われています。ログレベルは Settings.log_level を利用できます。

---

## よく使うコマンドまとめ

- 実行エンジン（開発 / paper_trading / live 判定は環境変数 KABUSYS_ENV に依存）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張できます（依存関係固定の requirements.txt、Dockerfile、CI 設定、より詳しい開発ガイドなど）。他に追記したい項目があれば教えてください。