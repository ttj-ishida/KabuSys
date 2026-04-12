# KabuSys

日本株向け自動売買システムの簡易実装。  
取引実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含みます。

概要・使い方・設定・ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

KabuSys は以下の主要機能を提供します。

- ExecutionEngine（発注エンジン）
  - ブローカークライアント抽象化（本番 / Paper Trading 切替）
  - OrderManager / OrderRepository による状態管理
  - Reconciler による再起動後の自動復旧
  - RiskManager による発注ルール・レート制限等
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor の定期ポーリング
  - MonitoringDB（SQLite）にログ永続化
  - KillSwitch（フラグファイルで ExecutionEngine を停止）
  - AlertManager（LINE Push で通知）
  - Streamlit ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定・等加重 / スコア加重・リスクベースサイズ算出
  - セクターキャップ、レジーム乗数などの調整関数
- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）・統計サマリ
- AI モジュール
  - news_nlp: ニュースを OpenAI（gpt-4o-mini）でセンチメント付与 → ai_scores へ格納
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポート出力

---

## 機能一覧（抜粋）

- ブローカ抽象化（本番 / Paper Trading）
- 注文ライフサイクル（作成 → 送信 → 同期 → ログ）
- 再起動時のリコンシリエーション（注文・ポジション差分検出）
- リスク監視（ドローダウン・ポジション数上限・滞留注文・約定異常）
- システム監視（CPU/MEM/Disk、データ鮮度、PID 生存確認）
- 通知（LINE Push、クールダウン制御）
- Streamlit による監視ダッシュボード
- DuckDB を利用した時系列 / ファクター計算
- OpenAI を用いたニュースセンチメント・マクロセンチメント集約
- Paper Trading 向け検証レポート生成ツール

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `|` を使用しているため）
- SQLite（標準ライブラリ）
- DuckDB（外部パッケージ）

推奨環境構築（例）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （必要に応じて他ライブラリを追加してください。プロジェクトには requirements.txt は含まれていません）

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数（.env）を用意
   プロジェクトルートに `.env`（もしくは `.env.local`）を置くと自動読み込みされます（既存 OS 環境変数は保護される）。
   代表的な環境変数（Defaults は Settings クラスの定義を参照）:

   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須）
   - KABU_API_PASSWORD: （必須）
   - OPENAI_API_KEY: OpenAI を利用する場合に設定
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定モード）
   - PID_FILE_PATH: data/execution.pid
   - KILL_FLAG_PATH: data/kill.flag
   - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用、デフォルト 60）

注意
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を探索して行います。必要があれば環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## 使い方

基本的な起動例（プロジェクトルートで実行）:

- ExecutionEngine を起動（本番 / paper_trading に応じて DB とブローカー挙動が変わる）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - あるいは（環境変数は .env で事前設定）
    - python -m kabusys.run_execution

  挙動:
  - paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 起動時にプロセス優先度を "high" に変更します（set_process_priority）。

- Monitoring を起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルト間隔: 60秒
  - 監視は Settings.sqlite_path（本番用 monitoring DB）を使用します（KABUSYS_ENV に関係なく本番 sqlite_path を参照）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（コードとして利用）
  - ニューススコアを付与: kabusys.ai.score_news（DuckDB 接続 & target_date を渡して呼び出す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime

注意点
- Monitoring 実行時に PID ファイルや kill.flag の取り扱いがあります（KillSwitch／Execution 停止制御）。
- LINE 通知はトークンと user_id が設定されていない限り送信されず、ログ出力だけ行います。
- OpenAI を使用する機能は API キー（OPENAI_API_KEY）が必須です。

---

## 主要設定（Settings クラスに定義されているもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant / partial / never / reject; default: instant)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（モニタ閾値）
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL

（詳細は src/kabusys/config.py を参照してください）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定の読み込み・検証
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 単体の起動スクリプト

サブパッケージ
- execution/
  - broker_factory.py, broker_api.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...  
  - 発注ロジック・ブローカ抽象・再同期ロジック
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 + CRUD 用クラス MonitoringDB
  - system_monitor.py — CPU/MEM/Disk、データ鮮度、PID チェック
  - trade_monitor.py — 滞留注文・約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限の監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE Push 通知 + クールダウン
  - monitoring_engine.py — 複数モニタを統合してポーリング
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（複数手法）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計
- ai/
  - news_nlp.py — ニュース集約 → OpenAI でセンチメント → ai_scores に書込
  - regime_detector.py — MA + マクロニュースで日次レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading DB を解析して検証レポートを出力
- utils/
  - process_priority.py — プラットフォームを吸収したプロセス優先度・CPU affinity 設定ユーティリティ
- monitoring/monitoring_db.py — 監視用 DB スキーマと MonitoringDB クラス

data/
- デフォルトで利用する DB ファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）

---

## 運用上の注意 / 実装上の留意点

- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 monitoring DB）を使用します。Paper Trading 用に完全分離するには別設定を検討してください。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（失敗した場合は警告）。
- kill.flag を使用した停止は冪等に実装されています（既存フラグがあれば上書きしない）。
- ai モジュールは外部 API（OpenAI）に依存します。API 呼び出しの失敗はフォールバック（多くの箇所で安全に 0.0 やスキップ）するよう実装されていますが、利用時は API キー管理・コストに注意してください。
- DuckDB をデータ分析用途で利用しています。テーブル名やスキーマは research / ai のコードを参照してください。

---

## 参考コマンド集

- ExecutionEngine（Paper）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DuckDB / スクリプトからファクター計算を呼ぶ（例）
  - python -c "from kabusys.research import calc_momentum; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(calc_momentum(conn, datetime.date(2026,4,1))[:5])"

---

この README はコードベースの主要機能と運用方法を概説したものです。より詳細な実装や仕様は各モジュール（src/kabusys 以下の各ファイル）内の docstring とコメントを参照してください。必要であれば README を拡張してデプロイ手順や CI 設定、運用 Runbook（ログローテーション、バックアップ、監視アラート運用）を追加できます。