# KabuSys — 日本株自動売買システム README

本リポジトリは日本株の自動売買に関するコンポーネント群（注文実行、監視、研究、AI ニュース評価、ポートフォリオ構築など）を集めた Python パッケージです。以下はコードベースの概要、主要機能、セットアップと起動方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュールを含む自動売買フレームワークです。

- 注文発行と状態管理（ExecutionEngine, OrderManager, OrderRepository 等）
- 起動時のリコンシリエーション（Reconciler）
- リスク管理（RiskManager, RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine、SQLite に監査ログ保存）
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI を用いたニュースセンチメント評価（OpenAI を利用）
- Streamlit ベースの監視ダッシュボード
- Paper Trading モードでの切替（本番 DB と分離）

設計方針の例：
- DuckDB を用いた時系列データ解析（prices_daily / raw_financials 等）
- 監視ログは SQLite（data/monitoring.db 等）へ永続化
- Paper Trading は本番の DB と完全分離（data/paper_trading.db）
- 環境変数 / .env による設定管理

---

## 主な機能一覧

- 起動 / 実行
  - run_execution.py — ExecutionEngine を起動（本番/紙トレード切替）
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセスの監視、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag による停止シグナル生成
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード: 監視情報可視化
- 注文関連
  - OrderManager: Order State Machine、送信・同期処理
  - Reconciler: 再起動後の注文/ポジションリコンシリエーション
  - BrokerClientFactory: 環境に応じたブローカークライアント生成（paper_trading では Mock）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み付け、セクターキャップ適用、ポジションサイズ計算（単元株丸め、aggregate cap）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC 計算・統計サマリー
- AI
  - news_nlp.score_news: OpenAI でニュースを銘柄毎にセンチメント評価して ai_scores に書き込み
  - regime_detector.score_regime: MA とマクロ記事の LLM センチメントで市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading DB を集計して検証レポートを出力

---

## セットアップ手順（例）

前提：Python 3.9+（実装が typing と標準ライブラリ中心のため近年の Python 推奨）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil requests openai streamlit

   （実行時に使用する追加パッケージやバージョンはプロジェクト配布物に合わせて調整してください。）

3. 環境変数 / .env の用意
   - プロジェクトルートに `.env` / `.env.local` を配置すると Settings モジュールが自動読込します（CWD に依存せず package 内からプロジェクトルートを検出）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（最小例）:
   - KABUSYS_ENV=development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - LOG_LEVEL=INFO
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE=instant|partial|never|reject

   ※ .env の書式やコメント処理は kabusys.config._load_env_file に準拠します。

4. データディレクトリ作成
   - mkdir -p data

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（通常実行）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
    - Execution 起動時にプロセス優先度をセット（set_process_priority("high")）。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔変更:
    - MONITOR_POLL_INTERVAL=30 など（秒、1 以上）。不正値はデフォルト 60 秒へフォールバック。
  - Monitoring は Settings.env にかかわらず本番 sqlite_path を使用して監視ログを書き込みます（monitoring の DB は環境に依存しない仕様）。

- Streamlit ダッシュボード起動（監視画面）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only 接続を行います。MonitoringEngine が DB を作成・更新していることが前提です。

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で SQLite DB を明示（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - レポート内容: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数 等。データが欠けるテーブルは安全に扱われます。

- AI 関連（ライブラリ API）
  - ニュース評価（外部から呼ぶ場合）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キーは引数または環境変数 OPENAI_API_KEY を参照します。API 呼び出しはリトライ/フェイルセーフの実装があります。

---

## 設定と運用上の注意点

- DB
  - DuckDB: 時系列データ（prices_daily / raw_financials 等）。パスは DUCKDB_PATH。
  - SQLite: 監視ログ等は SQLITE_PATH（monitoring.db）。Paper Trading は PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離。

- プロセス優先度
  - 起動時に set_process_priority("high") を呼ぶため、OS によっては権限不足で警告が出ます（psutil に依存）。問題がある場合は環境の権限設定を確認してください。

- kill.flag
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止指示を出します。Execution 起動時に Settings.kill_flag_clear_on_start を有効化すると起動時にクリアできます。

- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします。CWD に依存しない探索ロジックを採用。

- Paper Trading の挙動
  - PAPER_FILL_MODE の値（instant/partial/never/reject）でモック約定動作を制御。無効値はエラー。

- ロギング
  - Settings.log_level、または logging.basicConfig で調整。各モジュールで logger を利用。

---

## ディレクトリ構成

ファイル構成（抜粋 — src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロードと Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite のスキーマ初期化・読み書きラッパー
    - monitoring_engine.py   — 各モニタを束ねるループ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py     — （DB CRUD、OrderRecord 操作）
    - order_record.py
    - reconciler.py
    - execution_engine.py     — Engine 起動ロジック（EngineConfig 等）
    - broker_factory.py       — BrokerClientFactory（paper/live 切替）
    - broker_api.py
    - risk_manager.py
    - ...
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
  - tools/
    - __init__.py
    - paper_verification_report.py

その他:
- data/ (想定) — monitoring.db / paper_trading.db / kabusys.duckdb などのローカルデータファイルを配置

---

## 開発・拡張メモ

- DuckDB / SQLite のスキーマ変更は monitoring_db.init_monitoring_db などに追記してマイグレーションを行う設計です（既存カラムチェックと ALTER を含む）。
- OpenAI 呼び出し部分はリトライ・JSON 検証等の堅牢化が入っているため、API 仕様変更時はレスポンスパース部分を重点的に確認してください。
- ポートフォリオ・ポジション計算は純粋関数群として設計されておりユニットテストが容易です（DB 参照なし）。

---

## よくある質問（FAQ）

- Q: Paper Trading と本番の DB は同じですか？
  - A: いいえ。KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し本番 DB と分離します。一方 Monitoring は常に sqlite_path を使います（監視は環境にかかわらず本番 DB を対象にする方針のコードになっています）。

- Q: .env の自動ロードを止めたい
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: MONITOR_POLL_INTERVAL の単位は？
  - A: 秒です。1 以上の正の整数を指定してください。不正値は 60 秒にフォールバックします。

---

必要であれば、README に含める想定の requirements.txt、サンプル .env.example、起動スクリプト例（systemd / Supervisor）なども作成します。どの内容を追加しますか？