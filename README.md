# KabuSys README

以下はこのリポジトリ（KabuSys）の概要、セットアップ手順、使い方、ディレクトリ構成の説明です。日本株自動売買システムを想定したモジュール群が含まれます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコードベースです。主な目的は次のとおりです。

- 戦略（ファクター計算・特徴量探索）とポートフォリオ構築のためのリサーチ機能
- 実行（ExecutionEngine）を通じた発注管理（実口座／ペーパートレード対応）
- 監視（Monitoring）とリスク管理（ドローダウン、ポジション上限など）
- ニュースの NLP を用いたセンチメント評価（OpenAI API を利用）
- ペーパートレード結果の検証レポート生成

設計方針の特徴:
- 設定は .env または環境変数で管理
- DuckDB／SQLite を使用したデータ格納と分析
- OpenAI を利用した NLP 機能（API キーが必要）
- 開発 / paper_trading / live の環境区別

---

## 機能一覧

主な機能（抜粋）:

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 起動前設定検証: python -m kabusys.validate_config

- 実行エンジン
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - paper_trading 環境では MockBroker を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録

- 監視
  - System / Trade / Risk モニタリング機能
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - Kill Switch（一定条件で ExecutionEngine を停止するフラグファイル書き込み）

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン・IC 計算、統計サマリー

- ポートフォリオ構築
  - 候補選定、重み付け（等配分・スコア加重）
  - ポジションサイジング（単元株丸め、リスクベース等）
  - セクター集中制限・レジーム乗数

- AI（OpenAI）
  - ニュース NLP による銘柄センチメント評価（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（kabusys.ai.regime_detector）

- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成スクリプト:
    python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
     （本リポジトリにない場合は最低限次をインストールしてください）
     - duckdb
     - psutil
     - openai
     - PyYAML （config 検証で推奨）
   - 例:
     pip install duckdb psutil openai PyYAML

4. データ / ログディレクトリを作成（任意、起動時に自動作成されることもあります）
   - mkdir -p data logs

5. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabu API のトークン等を入力

6. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

環境変数の主な一覧（代表）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログファイル保存先）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

注意:
- .env は機密情報を含むため Git にコミットしないでください。
- 本番起動時は KABUSYS_ENV=live の設定を慎重に行ってください（validate_config は警告を出します）。

---

## 使い方（主要コマンド）

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/stop_requested.flag の存在で停止する
    - 実行中の PID は data/execution.pid に保存される

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は settings.sqlite_path（monitoring DB）を使用（環境にかかわらず本番 sqlite_path を参照）
  - 停止: data/stop_requested.flag を作成すると監視ループが終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI（OpenAI）機能の呼び出し（プログラム内部 API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（kabusys.data のテーブルを参照）
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- ログは stdout に出力され、加えて logs/<app_name>.log に日次でローテートして保存されます（ログディレクトリは LOG_DIR 環境変数で変更可）。
- 起動時に setup_logging(app_name="execution" など) が呼ばれます。

停止・Kill Switch:
- KillSwitch は監視コンポーネントが判定したときに data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（Execution 側はこのフラグを参照して停止処理を行います）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアする設定になります（本番では 0 を推奨）。

---

## ディレクトリ構成（主なファイル）

（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （存在する想定の監視モジュール）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知管理、存在する想定）
    - __init__.py
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
    - broker_factory.py      — Broker クライアント生成（Mock/実装切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - __init__.py
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
  - data/                    — デフォルトの DB / flag / pid 等を配置（実行時に作成）
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper_trading 用)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/                    — デフォルトのログ出力先（logs/<app_name>.log）

（注）一部ファイル/モジュールは本 README の抜粋コードに基づく。実際のリポジトリでは追加ファイルや差分がある場合があります。

---

## 補足・運用上の注意

- 本番環境（KABUSYS_ENV=live）では特に以下に注意してください:
  - 環境変数・認証情報（J-Quants / kabu API 等）を厳密に管理すること
  - KILL_FLAG_CLEAR_ON_START は 0 を推奨（自動クリアは危険）
  - LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定しないとアラートが届きません

- OpenAI を使う機能を運用する場合は API 利用料・レート制限、エラーハンドリング（モジュール内でリトライ実装あり）に留意してください。

- DB への書き込み・マイグレーションは monitoring_db.init_monitoring_db 等で冪等に行われますが、運用でのバックアップや権限管理を行ってください。

---

この README はコードベースの主要点をまとめたものです。より詳細な実装・設計はソースコメント（各 .py の docstring）とドキュメントファイル（存在する場合）を参照してください。必要であれば使用例やデプロイ手順を追記します。