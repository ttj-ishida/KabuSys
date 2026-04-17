# KabuSys

KabuSys は日本株向けの自動売買 / 監視 / 研究用ライブラリ兼実行環境です。  
このリポジトリには、注文実行エンジン、監視（モニタリング）コンポーネント、ポートフォリオ構築・ポジションサイジングロジック、ファクター計算や研究用ユーティリティ、ならびにニュースを LLM で評価する AI モジュールが含まれます。

以下はこのコードベースの概要、機能一覧、セットアップ手順、主要コンポーネントの使い方およびディレクトリ構成です。

プロジェクトの目的
- 自動売買の実行（ExecutionEngine）
- 実行状態・システム状態の常時監視とアラート（MonitoringEngine / AlertManager）
- Paper Trading（本番 DB と完全分離）を用いた検証
- ファクター計算・リサーチ（DuckDB を利用）
- ニュースの NLP スコアリング（OpenAI API を利用）
- Streamlit による監視ダッシュボード

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカーファクトリで本番・モック（paper_trading）クライアントを切り替え
  - 再起動時のリコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による発注管理

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの健全性監視
  - TradeMonitor: 注文滞留（stale order）や約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ（kill.flag）書き込み
  - AlertManager: LINE Messaging API への通知（クールダウン機能付き）
  - MonitoringEngine / run_monitoring スクリプトによるポーリング実行

- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC、統計サマリ等の研究ユーティリティ
  - 銘柄選定、等重・スコア重み・リスクベースのポジション決定、セクター制約、レジーム乗数

- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースを組み合わせて市場レジーム判定（bull/neutral/bear）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の union 演算子 (|) などを使用）
- SQLite、DuckDB を利用します
- OpenAI API を使う場合は API キーが必要
- Windows / Linux / macOS をサポート（プロセス優先度設定は OS に依存）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt を用意し pip install -r requirements.txt を推奨
4. data ディレクトリを作成（PID / flag / DB のデフォルトパスに依存）
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（Settings で必須になっているもの）
- JQUANTS_REFRESH_TOKEN — J-Quants 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

OpenAI を使う機能を使う場合
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）

主な環境変数とデフォルト
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: execution.pid（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: data/kill.flag（デフォルト）
- MONITOR_POLL_INTERVAL: 監視ループ ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

例: .env
    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=xxxxx
    KABU_API_PASSWORD=xxxxx
    OPENAI_API_KEY=sk-...
    LOG_LEVEL=INFO

---

## 使い方（主要スクリプト・コマンド）

※パッケージがインストール済みであればモジュールとして実行できます（python -m kabusys.run_monitoring 等）。

1) 監視ループを起動（Monitoring）
- 実行:
  - python -m kabusys.run_monitoring
  - あるいは python src/kabusys/run_monitoring.py
- 説明:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず常に本番 DB を参照）。
  - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合はログに警告）。

- 停止:
  - プロジェクトルートの data/stop_requested.flag を作成するとループは検出して終了します（run_monitoring と run_execution 両方で参照）。

2) Execution Engine を起動
- 実行:
  - python -m kabusys.run_execution
  - あるいは python src/kabusys/run_execution.py
- 説明:
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading db（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録され本番 DB と完全に分離されます。
  - 起動前に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - エンジンはバックグラウンドスレッドで run_session を実行し、stop フラグ検出で安全に停止します。
  - PID ファイルは data/execution.pid に書き込まれます。

- 停止:
  - data/stop_requested.flag を作成する（または KillSwitch により kill.flag が書き込まれる場合あり）。

3) Paper Trading 検証レポート（コマンドライン）
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で指定可能。
- 出力:
  - システム稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL を表示します。

4) Streamlit ダッシュボード（監視 UI）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用モードで SQLite を開き、ダッシュボード・ポジション一覧・直近注文・システム状態・直近リスクイベントを表示します。

5) AI モジュール（プログラムからの呼び出し）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.connect(...).cursor()）を渡して呼び出します。api_key を None にすると環境変数 OPENAI_API_KEY が使われます。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に DuckDB 接続と日付を渡して実行すると market_regime テーブルに結果を書き込みます。
- 注意: OpenAI API キー未設定時は例外が出ます（ValueError）。

6) ライブラリ / リサーチ機能の利用
- kabusys.research モジュール（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）を import して DuckDB 接続を渡すことで利用可能。

---

## 停止 / 強制停止フロー（flag ファイル）

- 停止要求（graceful stop）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループは検出して終了します。

- KillSwitch による停止
  - Monitoring のロジック（RiskMonitor 等）が条件を満たすと KillSwitch が data/kill.flag を書き込みます（既存なら再書き込みしない）。
  - KillSwitch の理由は flag ファイルに書かれ、ログに WARN レベルで記録されます。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — raw_news を LLM で評価して ai_scores に書き込むロジック
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース + LLM）
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（init, MonitoringDB クラス）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留/約定異常監視
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
    - __init__.py

  - execution/
    - reconciler.py — 起動時リコンシリエーション
    - order_manager.py — OrderState マネージャ
    - order_repository.py, order_record.py, broker_factory 等（注文・ブローカー関連）
    - （実際のブローカー API は broker_api 等で抽象化）

  - portfolio/
    - portfolio_builder.py — 銘柄選定・重み計算
    - position_sizing.py — 株数決定・資金配分・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

- data/  （実行時に使用するファイル群; デフォルトで作成）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid (PID_FILE_PATH)
  - stop_requested.flag
  - kill.flag

---

## 開発時のヒント / 注意点

- 環境読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動読み込みします。OS 環境変数を保護しつつ .env.local で上書き可能です。

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading にすると paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。本番 DB と物理的に分離される設計です。

- OpenAI の利用
  - news_nlp / regime_detector は API のレスポンスエラーに対してリトライやフォールバック（ゼロスコア）を実装していますが、API キーは必須です。テスト時は _call_openai_api をモックしてください（コード中の注記参照）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成します。既存 DB にカラムが欠けている場合の簡易マイグレーションロジック（ALTER TABLE ADD COLUMN）を含みます。

- 権限
  - set_process_priority は OS と実行権限に応じてアクセスが拒否される可能性があります（警告ログのみ、致命的ではありません）。

---

必要に応じて README を拡張して、運用手順（systemd ユニット例 / Dockerfile / コンテナ化手順）や詳細な API 仕様、テストの実行方法を追加できます。ご希望があれば具体的な実行例（systemd ユニット / Docker Compose / CI 設定）も作成します。