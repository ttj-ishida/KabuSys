# KabuSys

日本株自動売買システムの一部コードベース（ライブラリ＋実行スクリプト群）の README（日本語）。

このリポジトリはトレード実行エンジン、監視機構、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

## プロジェクト概要
KabuSys は日本株の自動売買を想定したモジュール群です。主な役割は次の通りです。

- Execution: ブローカーとのやり取り、注文管理、再起動時のリコンシリエーションを行う ExecutionEngine。
- Monitoring: システム状態、注文の滞留や約定の異常、ドローダウンなどを監視しログ／アラートを生成する監視モジュール群と簡易ダッシュボード。
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター調整などポートフォリオ構築ロジック。
- Research: DuckDB 上の価格・財務データを使ったファクター計算や特徴量解析ユーティリティ。
- AI: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントスコアリングと市場レジーム判定。
- Tools: Paper Trading の検証レポート生成スクリプトなど運用補助ツール。

主要コンポーネントは全てテスト可能な純粋関数／明確な I/O を備えるよう設計されています（DB 接続や API 呼び出し箇所は分離）。

## 機能一覧
- Execution
  - Broker クライアントの抽象化（本番／モック切替）
  - 注文作成・送信・状態同期（OrderManager）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - システム（CPU/メモリ/ディスク）監視（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン／ポジション上限監視（RiskMonitor）
  - Kill Switch（条件に応じて停止フラグを書き込み ExecutionEngine を停止）
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio
  - 候補選定（スコア順／トップN）
  - 等分／スコア加重配分
  - 単元丸め・リスクベースサイズ計算
  - セクター上限適用、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC 計算、ファクター統計サマリー
- AI
  - ニュース記事のセンチメントを LLM でスコア化（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（market_regime へ書き込み）
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

## セットアップ手順（開発 / 実行）
1. リポジトリをクローン、プロジェクトルートへ移動（pyproject.toml がルートに必要）。
2. Python 環境の準備（推奨: venv / poetry 等）。
3. 依存パッケージをインストール（例）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   - その他（実際の requirements.txt / pyproject.toml を参照してください）
   例（pip）:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
4. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API、使用する場合）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知
     - PID_FILE_PATH / KILL_FLAG_PATH / PID ファイル・停止フラグパス（デフォルトは data 下）
5. data ディレクトリと DB 用ファイルを作成（必要に応じて）。多くの起動処理は存在しない場合に自動作成しますが、権限やパスに注意してください。

## 使い方（主要スクリプト例）
- ExecutionEngine を起動（通常は Production で起動）
  - paper_trading（サンドボックス）モード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に隔離されます。
  - live / development でも同様に `KABUSYS_ENV` を切り替えて起動。

- Monitoring を起動（監視ループ）
  - ポーリング間隔を環境変数で変更できます（秒、デフォルト 60 秒）:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path（SQLITE_PATH）を使用します（monitoring は本番 DB を参照する想定）。

- Streamlit ダッシュボード（ローカル閲覧）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  あるいは `python -m streamlit run ...`。読み取り専用で DB を開きます。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB は `data/paper_trading.db`。`--db` オプション / `PAPER_TRADING_SQLITE_PATH` 環境変数で変更可能。

- AI 機能（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続（prices_daily, raw_news 等のテーブル）を受け取ります。直接呼び出すには `OPENAI_API_KEY` を設定してください。
  - 例（スクリプトから呼ぶ場合）:
    ```
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...)
    score_news(duckdb_conn, target_date, api_key="...") 
    ```

- 停止方法 / Kill Switch
  - 実行中の監視ループや ExecutionEngine はプロジェクト data ディレクトリに置かれるフラグファイルを参照します。
    - data/stop_requested.flag: run_monitoring / run_execution の外部停止フラグとして利用（起動スクリプトで使用）
    - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine 停止を要求（kill_flag_path は Settings から指定）
  - 手動で停止したい場合、`data/stop_requested.flag` を作成するとループは検知して終了します。

## 設定（Settings）
Settings クラスは環境変数から各種設定を読み込みます（src/kabusys/config.py）。主な設定と挙動：

- DB 関連
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（validation あり）
  - log level / PID ファイルパス / kill flagpath など
- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（不正値は例外）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込む実装があります（ただし OS 環境変数が優先されます）。

## ディレクトリ構成（抜粋）
プロジェクトの主要なファイル・パッケージ構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - run_monitoring.py  — SystemMonitor をポーリングする起動スクリプト
  - run_execution.py  — ExecutionEngine を起動するスクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポートツール
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (他に broker_factory, order_repository, execution_engine 等の実装想定)
  - utils/
    - process_priority.py

（上記はこの README を作成するために提供されたソースの主要箇所を反映しています。実際のリポジトリではさらに多くのモジュールが存在する可能性があります。）

## 運用上の注意
- 監視（Monitoring）は本番の監視 DB を参照する想定の箇所があるため、paper_trading と監視 DB を分離する設計になっています。paper_trading の実行は paper_trading 用 DB に限定されますが、Monitoring は KABUSYS_ENV によらず `SQLITE_PATH`（本番）を参照します。
- OpenAI を使う機能は API キーに依存します。API のエラーはリトライやフォールバック（スコア 0.0 等）で安全に扱う設計ですが、API キーがない場合は例外（ValueError）を投げる関数があります。
- process priority / CPU affinity 設定は OS に依存します。psutil での設定が失敗した場合はログに出力してスキップします。
- DuckDB / SQLite のスキーママイグレーション対応（簡易）を行うコードが含まれています（monitoring_db.init_monitoring_db）が、複雑なマイグレーションは手動対処が必要になる場合があります。

## よく使うコマンドまとめ
- 実行エンジン起動:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書かれている情報は提供されたソースコードを元に要約・整理したものであり、実運用では pyproject.toml / requirements.txt、実際の broker クライアント実装、運用手順書（起動スクリプト監視・ログローテーション・バックアップなど）を併せて整備してください。必要であれば各モジュールのより詳細なドキュメント（API 仕様、関数シグネチャ、例）も作成できます。