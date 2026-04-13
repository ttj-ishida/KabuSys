# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。  
この README ではプロジェクトの概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の役割を持つコンポーネント群を含むシステムです。

- 戦略・ファクター計算（research）
- ポートフォリオ構築・ポジションサイズ決定（portfolio）
- 発注・ブローカー連携・注文管理（execution）
- 監視・アラート・KillSwitch（monitoring）
- ニュースの NLP によるセンチメント評価（ai）
- Paper Trading 検証ツール（tools）
- ユーティリティ類（utils）

設計方針として、可能な限り「副作用の少ない純粋関数」「DB・API へのアクセスとロジックの分離」を保ち、運用面（監視、リコンシリエーション、Kill flag 等）を重視しています。

---

## 機能一覧（抜粋）

- execution
  - OrderManager / ExecutionEngine：発注・状態管理、クラッシュ耐性を考慮した永続化フロー
  - Reconciler：起動時の注文・ポジション照合（自動復旧）
  - Broker クライアントを切り替え（本番 / paper_trading による分離）

- monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格検知
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じてフラグファイルを書き、ExecutionEngine に停止シグナルを送信
  - AlertManager：LINE Push による一方向通知（クールダウンあり）
  - MonitoringEngine：上記をまとめてポーリングする実行ループ
  - streamlit_dashboard：監視用ダッシュボード（Streamlit）

- ai
  - news_nlp.score_news：OpenAI を用いたニュースセンチメント集約・スコア保存
  - regime_detector.score_regime：ETF MA とマクロニュースを組み合わせた市場レジーム判定

- research
  - factor_research：Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration：IC 計算、将来リターン計算、統計サマリ

- portfolio
  - 銘柄候補選定・重み計算（等分配・スコア重み）
  - セクター制限・レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）

- tools
  - paper_verification_report：Paper Trading 用 DB を使った検証レポート生成

---

## セットアップ手順（開発 / 実行）

以下は一般的なセットアップ手順の例です。プロジェクトに requirements ファイルがある前提で説明します（本リポジトリでは抜粋ファイルのみ提供）。

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt / poetry があればそれに従ってください）

3. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数を設定：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   推奨の最低環境変数（.env の例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...          # ai モジュール使用時に必要
   - KABUSYS_ENV=development|paper_trading|live
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - LINE_CHANNEL_ACCESS_TOKEN=    # AlertManager 用（任意）
   - LINE_USER_ID=                 # AlertManager 用（任意）
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag

   Settings クラスは .env/.env.local をプロジェクトルート（.git あるいは pyproject.toml のあるディレクトリ）から自動で読み込みます。OS 環境変数は常に優先され、.env.local は .env より優先して上書きされます。

4. データディレクトリの作成
   - mkdir -p data

5. DuckDB / SQLite のスキーマ初期化は各起動スクリプト内で自動的に行われます（monitoring 用のテーブル作成などは init_monitoring_db が行います）。

---

## 使い方（代表的な実行コマンド）

- Monitoring を起動（ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 備考:
    - run_monitoring は Settings.sqlite_path（本番用 sqlite_path）を使用して監視 DB を開きます（KABUSYS_ENV に関わらず本番 DB を参照する設計）。

- ExecutionEngine を起動（注文実行）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、paper_trading 用 SQLite（デフォルト data/paper_trading.db）に分離して記録されます。
  - 実行:
    - python -m kabusys.run_execution

- Streamlit ダッシュボード（監視表示）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で DB を開きます。MonitoringEngine を先に起動してデータを収集してください。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - このスクリプトは PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定できます。

- AI モジュール（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定する必要があります（api_key を直接関数へ渡すことも可能）。
  - 例（Python REPL 内）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

---

## 重要な設計・運用上のポイント

- 環境（KABUSYS_ENV）
  - 有効値: development, paper_trading, live
  - paper_trading: ブローカー呼び出しはモックとなり DB が data/paper_trading.db に分離されます（本番データと完全分離）。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔を秒で指定する環境変数。1 未満や不正値は無視されデフォルト 60 秒にフォールバックします。

- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil を利用）。権限不足などで設定できない場合は警告でスキップされます。

- Kill Switch
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine はファイルの有無で停止シグナルを受け取る想定です。Kill flag のパスは Settings.kill_flag_path で制御します。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に古い kill.flag を自動で削除できます。

- DB マイグレーション
  - init_monitoring_db は既存 DB に対して冪等にテーブルを作成します。既存カラムの有無を確認して必要な ALTER を行う簡易マイグレーションも含んでいます（例: trade_logs.latency_ms や dashboard.peak_value の追加）。

- DuckDB の利用
  - research / ai のバッチ計算では DuckDB を使ってオンコロンデータを高速に集計します。Paths は Settings.duckdb_path で指定します。

---

## ディレクトリ構成（主要ファイルと説明）

（抜粋。src/kabusys 以下の主要モジュールを示します）

- src/kabusys/
  - __init__.py
    - パッケージ定義（version など）
  - config.py
    - Settings クラス：環境変数/.env 読み込み、各種パス・閾値・フラグを提供
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（paper_trading をサポート）
  - tools/
    - paper_verification_report.py
      - Paper Trading の SQLite DB から検証レポートを生成する CLI スクリプト
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算（select_candidates / calc_equal_weights / calc_score_weights）
    - position_sizing.py
      - ポジションサイズ計算（allocation_method, aggregation, lot 単位丸め）
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - monitoring/
    - monitoring_db.py
      - SQLite を使った監視ログの永続化 API（init / MonitoringDB クラス）
    - system_monitor.py
      - システム状態・データ鮮度をチェック
    - trade_monitor.py
      - 注文滞留・約定異常をチェック
    - risk_monitor.py
      - ドローダウン/ポジション上限の判定
    - kill_switch.py
      - kill.flag の作成 / 削除ロジック
    - alert_manager.py
      - LINE によるプッシュ通知
    - monitoring_engine.py
      - 各モニタを束ねる実行ループ
    - streamlit_dashboard.py
      - Streamlit による簡易ダッシュボード
  - ai/
    - news_nlp.py
      - raw_news を集約し OpenAI へ投げて ai_scores を更新
    - regime_detector.py
      - ETF MA とマクロニュースを組み合わせて daily regime を判定 / 保存
  - research/
    - factor_research.py
      - Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py
      - forward returns, IC, factor summary
  - execution/
    - order_manager.py
      - Order の作成 / 送信 / 同期などの外向き API
    - reconciler.py
      - 起動時の注文・ポジション突合
    - （その他：broker_factory, order_repository 等は実装の別ファイルとして存在）
  - utils/
    - process_priority.py
      - プロセス優先度 / CPU affinity のユーティリティ（psutil ベース）

（上記は抜粋です。リポジトリ全体にはさらに細かなモジュールが含まれます）

---

## 実運用に関する備考

- paper_trading モードは本番 DB と完全に分離されるよう設計されています。paper_trading を行う場合は KABUSYS_ENV=paper_trading を使用し PAPER_TRADING_SQLITE_PATH を指定してください。
- OpenAI API を使用する AI ワークフローはネットワーク障害や 429/5xx に対して指数バッファ・リトライを行いますが、API キーは必ず安全に管理してください。
- LINE アラートは channel token / user id が未設定の場合はスキップされます。運用では該当情報を .env に設定してください。
- PID ファイル（Settings.pid_file_path）によって ExecutionEngine の生存確認を行います。run_monitoring や SystemMonitor は PID ファイルが stale（壊れているか既に終了している PID）と判断するとファイルを削除してリスクイベントを記録します。

---

## 参考コマンド（まとめ）

- 開発仮想環境の作成・依存インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai requests streamlit

- 監視ループ起動
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring

- 実行エンジン起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、.env.example の雛形や systemd / supervisord 用のサービス定義、CI 用のテスト実行手順、または各モジュール（ExecutionEngine / BrokerFactory / OrderRepository 等）の詳細ドキュメントを追加で作成します。どの情報を優先して追加すべきか教えてください。