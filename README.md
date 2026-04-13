# KabuSys

日本株向け自動売買システムのコアライブラリ。ポートフォリオ構築、ポジションサイズ計算、注文管理、監視、AIベースのニュースセンチメント評価などを含むモジュール群を提供します。

この README はリポジトリ内の主要モジュールと実行方法、設定方法、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python モジュール群です。

- ファクター計算・研究（research）：モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上の価格データから算出
- ポートフォリオ構築（portfolio）：候補選定・重み付け・ポジションサイズ決定、セクター制約・レジーム調整
- 注文実行（execution）：OrderState 管理、ブローカーインターフェース、リコンシリエーション
- 監視（monitoring）：プロセス・システム・注文・リスク監視、アラート送信、Streamlit ダッシュボード
- AI モジュール（ai）：ニュースを LLM（OpenAI）でスコアリングして ai_scores に格納、レジーム判定
- ユーティリティ（utils）：プロセス優先度設定などのユーティリティ

設計方針として「外部 IO を呼ばない純粋関数」「ルックアヘッドバイアスを避ける設計」「フェイルセーフ（API失敗はデフォルト値で継続）」などが採用されています。

---

## 機能一覧

主な機能：

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：ファクターと将来リターンの解析ツール
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定・重み付け
  - calc_position_sizes：株数決定（単元丸め・リスク制限・aggregate cap）
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジームによる投下資金調整
- execution
  - OrderManager / Reconciler：注文ライフサイクル管理・起動時リコンシリエーション
  - BrokerClientFactory（実装により本番ブローカー or MockBroker）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：定期ポーリングで状態を監視し monitoring DB に永続化
  - KillSwitch：条件に応じた停止フラグ(data/kill.flag)の作成
  - AlertManager：LINE による通知（クールダウン管理）
  - MonitoringEngine：複数モニタを束ねたポーリングエンジン
  - Streamlit ダッシュボード（監視 UI）
  - paper_verification_report：Paper Trading 用の検証レポート生成
- ai
  - score_news：OpenAI を用いたニュースの銘柄別センチメントスコアリング
  - score_regime：ETF MA とマクロニュースを合成した市場レジーム判定

---

## セットアップ手順

前提：Python 3.9+ を想定（依存パッケージは環境に応じて調整してください）。

1. リポジトリをクローンし、仮想環境を作る
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     pip install --upgrade pip
     ```

2. 必要なパッケージをインストール
   - 代表的な依存（requirements.txt が無い場合の例）:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - 実行環境により追加パッケージが必要な場合があります（例: duckdb のバージョンや OpenAI SDK）。

3. 環境変数・.env
   - プロジェクトルートに `.env` / `.env.local` を置くことで環境変数を自動ロードします（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（必須/デフォルト）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （AI 機能利用時に必要）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading の SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - LOG_LEVEL（デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）
   - .env の書式は shell の export やクォート、コメントをある程度サポートします（config モジュール参照）。

4. DB 初期化
   - monitoring 用の SQLite は起動スクリプトが必要に応じてテーブルを作成します。手動で用意する必要は基本ありません。

---

## 使い方

主要な実行スクリプトと使い方例。

- 監視ループ起動（Monitoring）
  - 目的: SystemMonitor のポーリングを開始してデータを monitoring DB（既定: data/monitoring.db）へ記録
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔 (秒) を上書き可能（例: 30秒）
      ```
      export MONITOR_POLL_INTERVAL=30
      python -m kabusys.run_monitoring
      ```
  - 注意:
    - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（監視データは本番 DB を参照）。

- 注文実行エンジン起動（ExecutionEngine）
  - 目的: ExecutionEngine を起動して取引セッションを実行
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading モード:
    - KABUSYS_ENV を `paper_trading` に設定すると MockBrokerClient を使用し、paper_trading 用 SQLite（既定: data/paper_trading.db）に分離して記録します。
      ```
      export KABUSYS_ENV=paper_trading
      python -m kabusys.run_execution
      ```
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority が実行されます。権限によっては失敗して警告になることがあります）。

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System を表示します。

- Paper Trading 検証レポート
  - 目的: Paper Trading DB から検証指標（稼働率・注文成功率・レイテンシ等）を出力
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

---

## 実行上の注意点 / 運用メモ

- プロセス優先度
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼びます。OS により動作が異なり、アクセス権がない場合は警告が出ます。

- kill.flag / PID
  - ExecutionEngine と Monitoring は PID ファイル（デフォルト data/execution.pid）を使ってプロセス存在確認を行います。KillSwitch は data/kill.flag を作成して実行エンジンに停止信号を送ります。
  - Settings の kill_flag_clear_on_start が "1" の場合、起動時に既存の kill.flag を消去します。

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合、ブローカークライアントは MockBrokerClient を使用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。本番データと完全分離されます。

- DuckDB / SQLite
  - DuckDB は歴史的価格（prices_daily 等）や raw_financials を保管しておく想定です。パフォーマンス上の理由からクエリは DuckDB 接続を直接受け取ります（research / ai モジュール参照）。

- LINE 通知
  - AlertManager は LINE Messaging API を用いた一方向通知を行います。token / user_id が未設定の場合は送信をスキップしてログに記録します。クールダウン機能あり。

---

## ディレクトリ構成

（リポジトリ内の主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - utils/
    - __init__.py
    - process_priority.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager / Reconciler / order_repository 等 — 一部ファイルは省略)
    - reconciler.py
    - order_manager.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - research/（上記参照）
  - data/（実行時に生成する想定のディレクトリ）
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

（注）ここに記載の他にも実装ファイルが存在する場合があります。上記は主要モジュールの抜粋です。

---

## よく使うコマンドまとめ

- 依存インストール（例）
  ```
  pip install duckdb psutil requests openai streamlit
  ```

- 監視を起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン（本番 / paper）
  ```
  python -m kabusys.run_execution
  # paper trading
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて、この README をベースに環境固有の運用手順（サービス化、systemd / supervisor 用の unit ファイル、監視アラートの閾値調整など）を追記してください。質問や追加でドキュメント化してほしい点があれば教えてください。