# KabuSys — README

本リポジトリは日本株自動売買システム「KabuSys」の一部を抜粋したコードベースです。ここでは構成、主要機能、セットアップ手順、起動方法、ディレクトリ構成などを日本語でまとめます。

注：この README はソースコード（src/ 以下）に基づく説明です。実動作させる場合は環境に応じた追加設定や外部 API キーの準備が必要です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（Execution）・監視（Monitoring）・研究（Research）・ポートフォリオ構築（Portfolio）・AI（ニュース NLP / レジーム判定）等のコンポーネントで構成されるシステムです。  
主な設計方針は以下です。

- DuckDB / SQLite を用いたオンプレ DB でのデータ処理（prices_daily, raw_financials, raw_news 等）。
- Execution と Monitoring は DB を介して分離（Paper Trading 用 DB を用意して完全分離可能）。
- 外部 LLM（OpenAI）を用いたニュースセンチメント評価・レジーム判定機能を提供（API キー必須）。
- 監視コンポーネントはログ・リスク判定・kill switch を提供し、必要に応じて Execution を停止できる。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文処理を行う（run_execution.py）。
  - Paper Trading モードでは MockBrokerClient を使用し、paper_trading 用 DB に記録（本番 DB と分離）。
  - 起動時の自動リコンシリエーション（Reconciler）で OrderSent 状態の同期処理。

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態・データ鮮度監視。
  - TradeMonitor: 注文滞留（stale order）や約定価格の異常検出。
  - RiskMonitor: ドローダウン・ポジション上限監視と Dashboard 更新。
  - KillSwitch / AlertManager: リスクトリガーで kill.flag を書き込み、LINE へ通知。
  - MonitoringEngine: これらをまとめてポーリングループで実行（run_monitoring.py）。

- 研究・データ処理（Research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）等の統計分析

- ポートフォリオ構築（Portfolio）
  - 候補選定、等金額・スコア加重配分、セクター制約の適用、ポジションサイズ計算（単元丸め・aggregate cap 等）

- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM でセンチメント評価して ai_scores に永続化
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定

- ユーティリティ
  - process_priority: プロセス優先度や CPU affinity 設定ユーティリティ
  - streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
  - 検証用スクリプト: tools/paper_verification_report.py（Paper Trading の指標を集計してレポート出力）

---

## 要求・前提

- Python 3.10 以上（ソース内で Union 型表記 A | B を使用しているため）
- 必要パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit  (ダッシュボード利用時)
- SQLite（標準ライブラリ）、その他ライブラリはコード参照に従ってインストールしてください。

（プロジェクトに requirements.txt がある場合はそれを使うのが望ましいです。）

---

## セットアップ手順（ローカル実行向けの基本手順）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai requests streamlit

   ※requirements.txt があれば:
   - pip install -r requirements.txt

4. 環境変数を設定
   - .env / .env.local に必要な変数を記載するか、OS 環境変数として設定します。
   - Settings で参照する主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合に必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (paper_trading 時の fill 動作: instant|partial|never|reject)
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring で使用）

   - 自動 .env ロード
     - リポジトリルートに .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

6. DB 初期化
   - monitoring テーブル等は run_monitoring / run_execution 実行時に自動作成されます（init_monitoring_db を呼ぶため）。

---

## 使い方（主なコマンド例）

- Execution エンジンを起動
  - 本番／dev（既定）:
    - python -m kabusys.run_execution
  - Paper Trading モード（MockBroker 使用、DB は data/paper_trading.db）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  動作: プロセス優先度を high に設定し、OrderManager / ExecutionEngine を起動します。起動時に data/stop_requested.flag が存在すると起動を中止します。実行中に stop flag が置かれると安全に停止します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  動作: SystemMonitor を中心に DB に監視ログを書き、必要であれば kill.flag を作成する等の処理を行います。Monitoring は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開き、最近のポジション・注文・システムステータス・リスクログ等を表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（プログラム的に呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キーが必要。例外や API 失敗はフェイルセーフで扱われる実装が多いですが、キー未設定だと ValueError を投げます。

---

## フラグ／制御ファイル

- 停止要求（外部からエンジンを止めたいとき）
  - data/stop_requested.flag — run_monitoring / run_execution が存在を検出するとループを終了または停止します。

- Execution 停止（強制停止トリガー）
  - data/kill.flag — KillSwitch が検出・書き込む。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して起動時の挙動や停止を制御します。

- PID ファイル
  - data/execution.pid（Settings.pid_file_path のデフォルト）: ExecutionEngine が PID を書きます。SystemMonitor はこのファイルの存在と PID の生存を確認してプロセス死活確認を行います。

---

## 注意点 / トラブルシュート

- Python バージョン
  - ソースコードは Python 3.10 以上を想定しています（PEP 604 の | 型表記など）。

- OpenAI API
  - AI 機能を使用するには OPENAI_API_KEY が必要です。キー未設定時は関連関数は ValueError を返します。
  - API 呼び出しはネットワークエラー・429・5xx 等に対してリトライやフォールバック処理が実装されていますが、API コストやレートに注意してください。

- DB ファイル権限
  - streamlit 等で DB を読み込む際に read-only URI を使っています。ファイルのパス・権限に注意してください。

- プロセス優先度設定
  - set_process_priority は psutil と OS 権限に依存します。権限不足で設定できない場合は警告ログが出ますが処理は継続します。

- MONITOR_POLL_INTERVAL
  - run_monitoring では環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます。1 以上の整数を指定してください。不正な値はデフォルト 60 秒にフォールバックします。

- 自動 .env 読み込み
  - リポジトリのプロジェクトルート（.git または pyproject.toml が存在する場所）を探索して `.env` と `.env.local` を自動読み込みします。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

（ファイル数が多いため、主要なモジュールのみ抜粋しています）

- src/
  - kabusys/
    - __init__.py
    - config.py
      - 環境変数と Settings の定義（.env 自動読み込みなど）
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプト（Paper Trading では MockBroker を使用）
    - tools/
      - paper_verification_report.py
        - Paper Trading の検証レポート作成スクリプト
    - ai/
      - news_nlp.py
        - ニュースセンチメント評価（OpenAI 呼び出し）
      - regime_detector.py
        - 市場レジーム判定（MA200 + マクロセンチメント）
      - __init__.py
    - monitoring/
      - monitoring_db.py
        - SQLite 用のスキーマ初期化／簡易永続化ラッパー（MonitoringDB）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
        - LINE notify 実装
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - execution/
      - order_manager.py
      - reconciler.py
      - （その他 Execution 関連コンポーネントは repository の一部）
    - utils/
      - process_priority.py
    - data/ (実行時に利用／生成される想定)
      - monitoring.db (default)
      - paper_trading.db (paper trading 用)
      - kabusys.duckdb (duckdb ファイル)
      - execution.pid / stop_requested.flag / kill.flag

---

## 開発者向け補足

- DB スキーマ変更やマイグレーションは簡易的に monitoring_db.init_monitoring_db が起動時に行います（冪等）。
- AI とのやり取りは JSON Mode（response_format）を利用し、結果のバリデーション処理を行っています。テスト時は _call_openai_api を patch する設計です。
- Execution と Monitoring は DB を介して相互作用するため、Paper Trading モードでは DB を必ず分離して運用してください（設定: KABUSYS_ENV=paper_trading）。

---

必要であれば、README に含める具体的な .env.example（環境変数の例）や requirements.txt、起動スクリプトの systemd ユニット例なども作成できます。どの情報を追加しますか？