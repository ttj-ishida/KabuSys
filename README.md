# KabuSys

日本株向け自動売買システムの軽量実装。本リポジトリは以下を含みます：シグナル→ポートフォリオ構築→発注→監視・アラート・検証ツール・研究ユーティリティなど。

以下はコードベースから抜粋した README です。実行例・環境変数・主要モジュールの説明を日本語でまとめています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド / ツール）
- よく使う環境変数
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたシステム群です。
- 戦略・ポートフォリオ構築・発注エンジン・監視・リスク管理・AI（ニュース NLP / レジーム判定）・検証ツールを含みます。
- SQLite（監視用 / paper_trading 用）と DuckDB（時系列・財務データ分析）をデータストアとして利用します。
- OpenAI（gpt-4o-mini 相当）を用いたニュースセンチメント解析やマクロセンチメント評価を行うモジュールを含みます（APIキー必須）。

---

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実発注クライアントまたは paper_trading 用の Mock ブローカーを起動
  - 発注管理、リスク管理、再コンシリエーション等を含む
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態、データ鮮度、注文滞留、約定異常、ドローダウン等をポーリングしてログ・アラートを行う
  - LINE 通知（AlertManager）や kill.flag による Execution 停止シグナル発行
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio（portfolio パッケージ）
  - 候補選定・重み計算・ポジションサイズ算出・セクター上限・レジーム乗数などの純関数実装
- Research（research パッケージ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）や特徴量探索、IC 計算、forward return 計算
- AI モジュール（ai パッケージ）
  - news_nlp: ニュースを LLM に送信して銘柄別センチメントを ai_scores テーブルへ保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 結果を合成して market_regime に書き込む
- ツール
  - paper_verification_report: Paper Trading 実行結果（data/paper_trading.db）を集計してレポートを表示

---

セットアップ手順（開発環境想定）
1. Python 環境を用意
   - 推奨: Python 3.9+（コードは型ヒントで 3.9+ 想定）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 最低限必要な主要ライブラリ（例）:
     - pip install duckdb psutil requests openai streamlit
   - （実際の requirements はプロジェクトの配布物を参照してください）

3. データディレクトリ作成
   - data フォルダを作成（デフォルト DB / PID / フラグファイルがここに配置されます）
     - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートの .env / .env.local を用意できます（config モジュールが自動で読み込みます）
   - 主要な環境変数は後述します
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に監視用テーブルの初期化（init_monitoring_db）を行います。
   - DuckDB 内のテーブル（prices_daily / raw_financials / ai_scores / market_regime 等）は別途用意してください（研究・AI処理で参照されます）。

---

使い方（実行コマンド例）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は監視用 SQLite（settings.sqlite_path）に接続します。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に注意。

- ExecutionEngine（発注エンジン）を起動
  - デフォルト（development / live の想定）:
    - python -m kabusys.run_execution
  - Paper trading 実行（MockBroker を使用し DB を paper_trading 専用に分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中の停止は data/stop_requested.flag を作成すると検知して終了します（run_execution / run_monitoring が参照）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは SQLite を読み取り専用で開きます（監視デーモンが DB を更新している前提）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI モジュールの利用（コード呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に API キーが必要

停止・制御
- stop フラグ: data/stop_requested.flag を作成すると run_monitoring.py / run_execution.py が検知して安全に終了
- kill.flag: KillSwitch が条件を満たした場合 data/kill.flag を書き込み、ExecutionEngine 側で参照してプロセスを停止させる設計
- PID ファイル: data/execution.pid を生成／検査して起動中プロセスの存在確認を行う

---

主要な環境変数（代表）
- KABUSYS_ENV (default: development)
  - 有効値: development | paper_trading | live
- LOG_LEVEL (default: INFO)
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- OPENAI_API_KEY — OpenAI を使う機能で必須（news_nlp / regime_detector）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (default: instant)
  - instant | partial | never | reject
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動で消去するかどうか
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

.env 例（参考）
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant

---

ディレクトリ構成（主要ファイル・モジュールの説明）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading を分離）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算（等重・スコア重み）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
    - position_sizing.py — 株数算出 / aggregate cap / lot 単位丸め
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル初期化・DB 操作用クラス（MonitoringDB）
    - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / プロセス検査
    - trade_monitor.py — 注文滞留・約定異常を検出
    - risk_monitor.py — ドローダウン・ポジション上限監視 & dashboard 更新
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知送信（クールダウン管理）
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py — 発注ワークフローの外向き API（OrderManager）
    - reconciler.py — 起動時の発注リコンシリエーション
    - その他（broker_factory, execution_engine, order_repository 等はコードベースに含まれています）
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM に投げて ai_scores を生成
    - regime_detector.py — MA200 と LLM で市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading DB を集計して検証レポートを出力

---

運用上の注意
- 環境分離:
  - paper_trading モードは発注・DB 書き込みを本番 DB と分離するよう設計されています。運用時は KABUSYS_ENV を適切に設定してください。
- データの整合性:
  - DuckDB のテーブル（prices_daily / raw_financials 等）は研究・AI モジュールが前提とするスキーマを満たしている必要があります。データロード・スキーマは別途ドキュメントを参照してください。
- OpenAI API:
  - API を利用する処理はコストとレイテンシに注意してください。news_nlp はバッチ化・リトライ/バックオフを実装していますが、API キーと使用量制御（料金管理）を行ってください。
- 停止 / 強制停止:
  - kill.flag や stop_requested.flag の運用方法を運用手順として定義しておくと安全です。
- 権限:
  - set_process_priority() は OS や権限によって失敗することがあります（警告でスキップされます）。運用環境での権限を確認してください。

---

補足
- 本 README はリポジトリ内スクリプトの docstring / コードコメントを元にまとめた概要です。各モジュールの詳細な仕様（DB スキーマ、モックブローカーの挙動、Engine の設定項目など）は該当ソースと設計ドキュメント（もしあれば PortfolioConstruction.md / StrategyModel.md 等）を参照してください。

---

必要であれば、以下を追加で作成できます：
- requirements.txt の推奨セット
- sample .env.example
- 運用手順（起動順序、監視フロー、障害時対応）
- DB スキーマ定義書（DuckDB / SQLite の詳細テーブル説明）

ご希望があれば上記のどれかを作成します。