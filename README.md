# KabuSys

日本株向けの自動売買 / 研究用ライブラリ群および運用ユーティリティ群のリポジトリです。  
本 README はこのコードベース（src/kabusys 以下）を使い始めるための概要、セットアップ手順、主要スクリプトの使い方、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

概要
- KabuSys は日本株の自動売買システム（Execution Engine）と、それを補助する監視・リスク管理・解析ツール群を提供します。
- 主要機能は発注ロジック（Execution）、ポートフォリオ構築（Portfolio）、ファクター計算・研究（Research）、ニュースAI ベースの NLP（AI）、およびシステム監視（Monitoring）です。
- 運用/開発向けに .env 対話ウィザード、設定検証 CLI、Paper Trading 用レポート出力などのユーティリティが含まれます。

主な特徴（機能一覧）
- Execution
  - 実際のブローカー接続（kabuステーション）または Paper Trading 用の MockBroker を切替（KABUSYS_ENV に依存）
  - リスク管理（最大比率、利用率、回路遮断など）と注文管理
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）・プロセス稼働検査、データ鮮度検査
  - トレードログ・ポジション・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
  - アラート管理（AlertManager を通す想定）
- Portfolio（銘柄選定・重み・株数決定）
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数適用
- Research（DuckDB を想定した時系列/ファクター計算）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュース記事に対する LLM（OpenAI）を用いた銘柄単位センチメントスコアリング（ai_scores）
  - 市場レジーム判定（ETF MA + マクロ記事を LLM で評価）
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

前提・外部依存（主なライブラリ）
- Python 3.9+（型アノテーションなどを参照）
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- sqlite3（標準ライブラリ）
- 必要に応じて他のパッケージ（実運用用ブローカークライアント等）

セットアップ手順（ローカル開発・テスト向け）
1. リポジトリをクローンし、環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
   - ない場合は最低限:
     - pip install duckdb psutil openai
     - （YAML 検証を使うなら）pip install pyyaml

3. data ディレクトリなど初期ディレクトリを作成（実行時に自動作成される場合あり）
   - mkdir -p data logs

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードは .env を作成/更新します（J-Quants トークン、kabu API パスワードなどの入力が必要）
   - あるいは .env を手動で作る（下にサンプル変数一覧）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK、危険な本番設定などは警告が出ます
   - 厳格モード: python -m kabusys.validate_config --strict （警告も失敗扱い）

6. OpenAI（AI 機能）を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、各関数に api_key を渡す

主な環境変数（サンプル・デフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視 DB
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- OPENAI_API_KEY — OpenAI 利用時に必要
- KILL_FLAG_CLEAR_ON_START (0|1) — Execution 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

主要スクリプト・使い方
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱い

- Execution Engine 起動
  - 動作: ExecutionEngine を起動し、発注処理を実行
  - 簡易実行:
    - python -m kabusys.run_execution
  - 動作ポイント:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すれば起動せず終了
    - プロセス優先度を High に設定（psutil 権限による）
    - 実行中は data/execution.pid に PID を書き込む設計（設定参照）

- Monitoring 起動（単体監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（秒、デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）
  - 停止は data/stop_requested.flag を作成することでループを抜ける

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数 or data/paper_trading.db

- AI / ニューススコアリング（プログラム的利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続
    - OPENAI_API_KEY を環境で設定しておくか api_key を渡す
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止方法（安全シャットダウン等）
- Execution 停止信号:
  - Kill Switch により data/kill.flag が書かれると Execution 停止を誘導できます（KillSwitch クラス参照）
- 監視・実行プロセスの即時終了:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution の監視ループが検知して終了します
- PID / フラグファイル:
  - PID ファイルや kill.flag のパスは Settings から取得（デフォルトは data/execution.pid や data/kill.flag）

ログ
- ログは kabusys.utils.logging_setup.setup_logging を通して統一的に設定される
- デフォルト出力先:
  - コンソール（stdout）
  - 日次ローテートファイル → logs/<app_name>.log（30日分保持）
- ログレベルは LOG_LEVEL 環境変数または引数で指定可能

ディレクトリ構成（src/kabusys を基準）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック（.env 自動ロード機能）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py    — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py      — SQLite ベースの永続化層（テーブル作成・ログ API）
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （トレード監視ロジック; ソースに存在）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - monitoring_engine.py  — 各モニタを束ねるエンジン
    - alert_manager.py      — （アラート送信ロジック; ソースに存在）
  - execution/
    - execution_engine.py   — ExecutionEngine のコア
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - ...                   — Execution の実装コンポーネント群
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    — 実行時に利用するファイル (db, flags, pid 等) を期待する場所（not in src）

補足・運用上の注意
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、paper 用 SQLite（デフォルト data/paper_trading.db）に記録し、本番 DB と分離されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、必要なカラム（例: peak_value, latency_ms）がなければ ALTER TABLE で追加します。
- OpenAI 利用:
  - API 呼び出しはリトライとバックオフを実装していますが、API キーやコスト管理は運用者側で注意してください。
- 権限:
  - psutil を使ったプロセス優先度設定は OS と実行権限に依存します（root 権限が必要な場合があります）。失敗すると警告ログを出し続行します。

例: 開発環境での最小実行フロー
1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup （.env 作成）
3. python -m kabusys.validate_config
4. duckdb/SQLite に必要なテーブルは実行時に自動作成されます
5. モニタリングを起動して状態を確認:
   - python -m kabusys.run_monitoring
6. Execution を起動（必要に応じて KABUSYS_ENV=paper_trading を指定）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

この README はコードベース内の主要な使い方と構成を短くまとめたものです。より詳細な設計やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）や運用手順書が別にある場合はそちらも参照してください。質問や追加で欲しいドキュメント（例: API リファレンス、運用チェックリスト、config のサンプル .env）を教えていただければ追記します。