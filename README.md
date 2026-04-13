# KabuSys

日本株向けの自動売買システム用ライブラリ群 / 実行用スクリプト集です。  
本リポジトリは主に以下の責務を含みます：発注エンジン起動・監視、Paper Trading 検証、ファクター計算、ニュース NLP によるセンチメント評価、ポートフォリオ構築ユーティリティなど。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提・依存
- セットアップ手順
- 使い方（実行コマンド例）
- 主要環境変数（代表）
- ディレクトリ構成（主要ファイル説明）
- 補足・注意事項

---

## プロジェクト概要
KabuSys は、日本株自動売買システムのコンポーネント群を提供します。  
主に次の領域を実装しています：

- Execution（発注エンジン）: Broker クライアント、注文管理、リコンシリエーション
- Monitoring（監視）: システム稼働・注文/約定の監視、Kill Switch、LINE 通知、Streamlit ダッシュボード
- Research（リサーチ）: ファクター計算、将来リターン計算、IC 計算など
- AI（NLP）: ニュース記事の LLM によるセンチメントスコア付与、市場レジーム判定
- Portfolio（ポートフォリオ構築）: 候補選別、重み計算、ポジションサイジング、リスク調整
- Utils: プロセス優先度 / CPU affinity 設定などのユーティリティ

設計方針として、「本番口座・発注 API へ直接アクセスしないリサーチ関数」「Paper Trading と本番 DB を分離」「LLM 呼び出しはリトライ／フェイルセーフを行う」等の安全策が組み込まれています。

---

## 主な機能一覧
- Execution
  - BrokerClientFactory 経由で実ブローカーまたは MockBroker を利用
  - OrderManager / OrderRepository / Reconciler による注文の作成・送信・同期
  - 起動時の自動リコンシリエーション（再起動後の同期）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数の監視とリスクイベント記録
  - KillSwitch: 条件を満たした場合フラグファイルを書き込み ExecutionEngine 停止シグナルを送出
  - AlertManager: LINE Push による一方向通知（クールダウン機能付き）
  - Streamlit ダッシュボード（監視 DB の可視化）
- Research
  - モメンタム / ボラティリティ / バリューファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp.score_news: raw_news から銘柄別センチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロ記事の LLM センチメントを合成して market_regime を生成
- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・成功率・レイテンシ等）

---

## 前提・依存（代表）
- Python 3.9+（型記述や一部挙動を考慮）
- 主要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを利用する場合）
- SQLite（ローカル DB ファイル利用）
- （実運用）ブローカ API の接続情報等

依存はプロジェクトの requirements.txt / pyproject.toml を参照してください（存在する場合）。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements があれば）pip install -r requirements.txt
4. データディレクトリ作成（デフォルト）
   - mkdir -p data
5. 環境変数を設定（.env をプロジェクトルートに置くことが可能）
   - 例（.env）
     - KABUSYS_ENV=development
     - KABU_API_PASSWORD=your_password
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=sk-...
     - PAPER_FILL_MODE=instant
     - (必要に応じて) PAPER_TRADING_SQLITE_PATH=./data/paper_trading.db
6. DB 初期化
   - run_monitoring または run_execution を起動すると、monitoring DB スキーマは自動作成されます（init_monitoring_db は冪等）。

---

## 使い方（起動例・コマンド）
- ExecutionEngine を起動（本番 / Paper Trading は KABUSYS_ENV で切替）
  - 環境を指定して起動:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 補足:
    - paper_trading の場合は MockBrokerClient を使用し、DB は settings.paper_sqlite_path（デフォルト: data/paper_trading.db）へ記録され、本番 DB と分離されます。
    - 起動時にプロセス優先度を "high" に設定します（utils.process_priority を利用）。
- Monitoring（ポーリングループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。無効値は 60 にフォールバック。
  - 監視は常に settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（KABUSYS_ENV にかかわらず）。
- Streamlit ダッシュボード（監視表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス変更:
    - --db /path/to/paper_trading.db
- AI (ニューススコア / レジーム判定)
  - duckdb コネクションを用意し、関数を呼び出す（コードベース利用向け）
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - score_news(conn, target_date, api_key="...")  # OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用
    - score_regime(conn, target_date, api_key="...")

---

## 主要な環境変数（抜粋）
- KABUSYS_ENV: 実行モード (development | paper_trading | live)。デフォルト: development
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

設定は OS 環境変数のほか、プロジェクトルートの `.env` / `.env.local` を自動読み込みできます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。

---

## ディレクトリ構成（主要ファイルの役割）
（src/kabusys 以下を示します）

- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - Settings クラス。環境変数の解決、デフォルト値、バリデーションを提供。
- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV により paper_trading を分離。
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL を参照。
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py など
  - 発注フロー、注文状態管理、リコンシリエーションロジックなどを実装
- monitoring/
  - monitoring_db.py : SQLite スキーマ定義と永続化 API（MonitoringDB）
  - system_monitor.py : CPU/メモリ/ディスク/データ鮮度/プロセスチェック
  - trade_monitor.py : 滞留注文・約定異常の検出
  - risk_monitor.py : ドローダウン・ポジション上限の監視
  - kill_switch.py : フラグファイルによる強制停止シグナル
  - alert_manager.py : LINE push API を用いた通知
  - monitoring_engine.py : 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py : 可視化用 Streamlit アプリ
- portfolio/
  - portfolio_builder.py : 候補選定、重み計算
  - position_sizing.py : 発注株数計算、単元丸め、aggregate cap
  - risk_adjustment.py : セクターキャップ、レジーム乗数
- research/
  - factor_research.py : momentum/value/volatility の計算（DuckDB）
  - feature_exploration.py : 将来リターン、IC、統計サマリー
- ai/
  - news_nlp.py : raw_news を LLM で評価し ai_scores に書き込むロジック（OpenAI と連携）
  - regime_detector.py : ETF MA とマクロ記事センチメントの合成によるレジーム判定
- tools/
  - paper_verification_report.py : Paper Trading の検証レポート出力ツール
- utils/
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

（上記以外にも補助モジュールが存在します。詳細はソースを参照してください。）

---

## 補足・注意事項
- データベースの初期化は init_monitoring_db() により自動作成・マイグレーションを行います。run_monitoring / run_execution 起動時に適切な DB ファイルが作られます。
- Paper Trading は本番 DB と分離されるよう設計されています。KABUSYS_ENV=paper_trading を使用することで data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録されます。
- AI（OpenAI）呼び出しは外部 API に依存するため、OPENAI_API_KEY を設定してください。API 呼び出しはエラー時にリトライやフォールバック（無害化）処理を行いますが、使用時はコストとレート制限に注意してください。
- run_* スクリプトは起動時にプロセス優先度を "high" に設定しようとします。権限がない場合は警告ログが出ますが処理は継続します。
- KillSwitch は監視ロジックによって data/kill.flag を作成すると ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側ではこのフラグをチェックして安全に停止する運用が期待されます。
- データ鮮度チェック（SystemMonitor）は DuckDB の prices_daily から最終日付を取得して判定します。DuckDB のデータが古いと data_freshness_ok が False になります。
- テスト・CI のため自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README を拡張して、運用手順（systemd / Docker / Kubernetes 用の起動例）、テスト手順、CI ワークフロー、さらに詳しい設定例を追加できます。必要であればその内容に沿った具体例を作成します。