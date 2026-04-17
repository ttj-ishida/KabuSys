# KabuSys

日本株自動売買システムのコードベース（抜粋）。本リポジトリは取引実行エンジン、監視機構、ポートフォリオ構築ロジック、調査/リサーチ、AI（ニュースセンチメント／レジーム判定）等のコンポーネントを含みます。

以下はこのコードベースの概要、機能、セットアップ・使い方、ディレクトリ構成をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤（モジュール型）です。主な役割は以下のとおりです。

- シグナルに基づく発注 / 注文管理 / リコンシリエーション（Execution）
- システム稼働状態・注文状態・リスク指標の定期監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制約など）
- ファクター計算・特徴量探索などのリサーチ（DuckDB ベース）
- ニュースを LLM で解析して銘柄センチメントや市場レジームを算出（OpenAI）
- Paper Trading 環境を本番 DB と分離して検証可能

設計方針の一部：
- DuckDB / SQLite をデータ格納に使用（分析と監視用に分離）
- 環境変数 / .env による設定読み込み（プロジェクトルートから自動読み込み）
- 本番／Paper 環境の明確な分離（paper_trading 用 DB 等）

---

## 主な機能一覧

- Execution
  - OrderManager: 注文作成・状態遷移・ブローカー同期
  - Reconciler: 再起動時の注文／ポジション突合せ
  - RiskManager（設定に基づくリスク管理）
  - BrokerClientFactory（本番/モック切替）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 各 Monitor を束ねてポーリング
  - AlertManager: LINE Push による通知（トークン未設定時はログのみ）
  - KillSwitch: 条件によりフラグファイルを書いて Execution を停止

- Portfolio
  - 候補選定、等金額/スコア重み付け、リスクベースの株数算出
  - セクターキャップ、レジーム乗数（市場レジーム反映）

- Research
  - ファクター計算（モメンタム / ボラ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI
  - news_nlp: raw_news を LLM で解析し銘柄別スコアを ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して日次レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ベースの監視ダッシュボード（read-only）

---

## セットアップ手順（開発環境向け）

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主要依存（コードから読み取れる代表パッケージ）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ 実プロジェクトでは requirements.txt を用意している想定です。実行時に不足エラーが出たら追インストールしてください。

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数 / .env
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 主要環境変数（代表）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - SQLITE_PATH: data/monitoring.db（監視ログ用 SQLite、デフォルト）
   - DUCKDB_PATH: data/kabusys.duckdb（分析用）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT 等

---

## 使い方（主要スクリプト・コマンド例）

注意: リポジトリをパッケージとして使う場合、src 配下を PYTHONPATH に入れるかパッケージをインストールしてください。以下はソースツリー直下での実行を想定します。

1. 監視ループの起動（Monitoring）
   - 実行:
     - python -m kabusys.run_monitoring
   - 説明:
     - Settings.sqlite_path（デフォルト data/monitoring.db）へ接続し、SystemMonitor をポーリングします。
     - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位に上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
     - 停止はプロジェクトルートの data/stop_requested.flag を作成すると検知して終了します。

2. 実行エンジンの起動（Execution）
   - 実行:
     - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
     - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
     - 停止は同じく data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が書き込まれるとエンジン側で検出・停止します。
     - 実行中は pid ファイル（デフォルト data/execution.pid）を作成します。

3. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db /path/to/paper_trading.db
   - 出力:
     - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定します。

4. 監視ダッシュボード（Streamlit）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - SQLite を read-only で開き、ダッシュボードを表示します。MonitoringEngine がログを書き込んでいることが前提です。

5. AI モジュールの利用（プログラム内呼び出し）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡して銘柄別ニュースセンチメントを ai_scores テーブルへ書き込みます。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - 市場レジームを計算して market_regime テーブルへ書き込みます。

6. 停止・クリーンアップ
   - Execution や Monitoring を停止するにはプロジェクトルートの data/stop_requested.flag を作成します。
   - KillSwitch による強制停止は data/kill.flag が作成されます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと起動時に自動で削除できます。

---

## 重要な実装上の注意点

- Settings（kabusys.config）は .env/.env.local の自動読み込みを行いますが、OS 環境変数が優先されます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の init_monitoring_db は冪等でテーブルを作成・必要なマイグレーションを行います。
- Paper Trading は本番 DB と完全に分離される設計になっています（settings.is_paper チェック）。
- AI 系は OpenAI API を利用するため API キーの管理に注意してください（環境変数 OPENAI_API_KEY）。
- プロセス優先度・CPU affinity 設定は psutil を使っています。権限不足や未対応 OS の場合は警告ログを出して処理をスキップします。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 内の主要ファイル／パッケージのツリーです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数 / 設定管理
    - run_monitoring.py                # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                 # ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py   # Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py               # SQLite 永続化層（system_status 等）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py               # LINE 通知
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py            # （コードベースに含まれる想定）
      - broker_factory.py
      - broker_api.py
      - order_record.py
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
    - data/                             # 実行時に作成される想定（data/*.db, pid/flag ファイル 等）
    - utils/
      - __init__.py
      - process_priority.py

（実際の repository には上記以外のファイル・モジュールが存在する可能性があります。ここでは提供コードから主要部分を抜粋しています。）

---

## トラブルシューティング / よくある質問

- DB が見つからない・開けない
  - monitoring 用 DB（data/monitoring.db）や paper_trading.db のパスを Settings の環境変数で指定するか、ファイルが存在するか確認してください。
- OpenAI API 呼び出しが失敗する
  - OPENAI_API_KEY を設定してください。429/タイムアウト等はリトライ処理を行いますが、上限を超えるとスキップされます。
- LINE 通知が送れない
  - LINE_CHANNEL_ACCESS_TOKEN および LINE_USER_ID を設定しているか確認してください。未設定の場合はログ出力のみ行います。
- 実行が即終了する
  - run_execution と run_monitoring は data/stop_requested.flag の存在をチェックします。開始前に存在している場合は起動を行わず終了します。

---

以上がこのコードベースの README（日本語）です。必要であれば、実際の依存関係（requirements.txt）や実行例（systemd サービス定義、Dockerfile、CI 設定）のテンプレートも作成できます。どの追加情報が必要か教えてください。