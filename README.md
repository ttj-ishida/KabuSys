KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なフレームワークです。本リポジトリは以下の主要機能を含みます。

- 注文生成・発注・状態管理（ExecutionEngine / OrderManager 等）
- モニタリング（システム状況・注文滞留・リスク監視・Kill Switch）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター調整）
- リサーチ（ファクター計算、特徴量探索、IC算出）
- AI 支援モジュール（ニュースのセンチメントスコアリング、マーケットレジーム判定）
- Paper Trading 用検証支援（レポート生成、paper_trading DB の分離）
- Streamlit ベースの監視ダッシュボード

主な設計方針は「外部サービス（ブローカー等）の依存を明確に切る」「ルックアヘッドバイアスを避ける」「失敗時はフェイルセーフで継続する（例：AI API失敗時のデフォルトフォールバック）」などです。

機能一覧
--------
- Execution
  - OrderManager, ExecutionEngine, Reconciler による注文ライフサイクル管理と再同期
  - Paper Trading モード（環境変数 KABUSYS_ENV=paper_trading）では MockBroker を使用し DB を分離
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留／約定異常価格の検出
  - RiskMonitor: ドローダウン／ポジション上限監視（ダッシュボード更新・リスクログ）
  - KillSwitch: しきい値を超えた場合に data/kill.flag を書き込んで Execution を止める
  - AlertManager: LINE push による通知 (cooldown 管理)
  - MonitoringEngine: 監視ループの統合
  - streamlit_dashboard: 監視情報の可視化（Streamlit）
- Portfolio construction
  - 候補選定(select_candidates)、重み計算(calc_equal_weights/calc_score_weights)
  - セクター制限、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - 株数決定・丸め（calc_position_sizes）
- Research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC、統計サマリー（feature_exploration）
- AI
  - news_nlp.score_news: raw_news を集約し OpenAI に送って銘柄別スコアを ai_scores に保存
  - regime_detector.score_regime: ETF(1321)の MA200 乖離 + マクロニュース NLP を合成して market_regime に記録
  - OpenAI 呼び出しはリトライ／エラーハンドリング実装済み
- Tools
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ
------------
前提
- Python 3.10+（typing の | やその他モダンな構文を利用）
- システムに DuckDB、psutil、requests、openai、streamlit 等のパッケージをインストール

推奨手順（簡易）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. 環境変数を設定
   - プロジェクトルートに .env を置く（自動ロード機能あり）。以下は主なキー例。

.env の例
- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
- AI 関連
  - OPENAI_API_KEY=...
- 実行モード / DB
  - KABUSYS_ENV=development|paper_trading|live
  - PAPER_FILL_MODE=instant|partial|never|reject
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
- ロギング / PID / フラグ
  - LOG_LEVEL=INFO
  - PID_FILE_PATH=data/execution.pid
  - KILL_FLAG_PATH=data/kill.flag
  - MONITOR_POLL_INTERVAL=30  # run_monitoring のポーリング秒（オプション）
- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN=...
  - LINE_USER_ID=...

注意事項
- KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- Monitoring は環境に関わらず本番 sqlite_path（Settings.sqlite_path）を使用する設計になっている箇所があります。設定内容に注意してください。
- プロセス優先度変更（psutil を使用）には権限が必要な場合があります。権限不足時は警告が出てスキップされます。

使い方（実行例）
----------------

1) 監視ループを起動（監視だけを行うプロセス）
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
- 実行:
  - python -m kabusys.run_monitoring
  - またはスクリプトファイルを直接実行: python src/kabusys/run_monitoring.py

- 停止:
  - プロセスへの KeyboardInterrupt、またはプロジェクトルートの data/stop_requested.flag を作成すると安全終了します。

2) Execution エンジンを起動（発注処理）
- KABUSYS_ENV に応じて本番/ペーパーが切り替わります。
  - paper_trading モードでは MockBroker を使い、DB は PAPER_TRADING_SQLITE_PATH に保存されます。
- 実行:
  - python -m kabusys.run_execution
  - または python src/kabusys/run_execution.py

- 停止:
  - data/stop_requested.flag を作成すると起動中のエンジンに停止要求を送ります。
  - 実行プロセスの PID は data/execution.pid に書き込まれます（存在チェックにより stale PID を検出して削除する仕組みあり）。

3) Streamlit 監視ダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  開始日
    - --to   YYYY-MM-DD  終了日
    - --db PATH          DB ファイル指定（PAPER_TRADING_SQLITE_PATH より優先）
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5) AI モジュール（ニューススコアリング / レジーム判定）をプログラムから呼ぶ
- 事前に OpenAI API キーを設定（OPENAI_API_KEY）。
- 例（概念）:
  - from kabusys.ai import score_news
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")
  - -> ai_scores テーブルにスコアを書き込む（戻り値は書き込んだ銘柄数）

その他 / 運用時の注意
-------------------
- MonitoringDB（SQLite）初期化:
  - init_monitoring_db(conn) は冪等でテーブルと必要なカラムを作成／マイグレーションします。run_monitoring/run_execution は起動時に呼び出します。
- Kill Switch:
  - RiskMonitor が閾値を超えると KillSwitch が data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグを検査し、存在すれば起動を停止します。
- ログ:
  - 基本的に logging.basicConfig(level=logging.INFO) が使われます。LOG_LEVEL 環境変数で変更可能です。
- 権限:
  - プロセス優先度や CPU affinity の設定はプラットフォームと権限に依存します。失敗時は警告ログでスキップされます。

ディレクトリ構成
----------------
主要なファイル・モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings クラス
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - data/                     — （データファイル置き場、例: data/*.db, *.pid, *.flag）
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py  (他、broker 関連モジュール)
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

ライセンス / 貢献
-----------------
この README ではライセンス情報は含めていません。プロジェクトに適切な LICENSE ファイルを追加してください。バグ報告・機能提案は Issue を立ててください。

最後に
------
この README はコードベースから得られる挙動と設定項目をまとめたものです。実行前に .env（または環境変数）と data ディレクトリのパス・権限を確認してください。何か追加で README に含めたい内容（例:具体的な運用手順、CI 設定、requirements.txt の内容など）があれば教えてください。