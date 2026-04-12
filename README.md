# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下を含みます：注文管理・実行エンジンの補助ロジック、監視（Monitoring）機能、ポートフォリオ構築ヘルパー、リサーチ用ファクター計算、ニュースの NLP スコアリングと市場レジーム判定など。

この README ではプロジェクト概要・機能一覧・セットアップ手順・使い方（起動方法）・ディレクトリ構成を日本語で説明します。

注意: 本 README はリポジトリに含まれるソースコード（src/kabusys 以下）を元に作成しています。実際の運用前に .env 設定や API キー、DB の初期化を必ず確認してください。

---

## プロジェクト概要

KabuSys は以下のような機能を提供するモジュール群です：

- 実行エンジン（ExecutionEngine）周辺のユーティリティ（OrderManager、Reconciler 等）
- 監視（Monitoring）：システム状態・注文滞留・リスク（ドローダウン／ポジション上限）を定期的にチェックしてログ・アラート・kill フラグを生成
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、将来リターン計算、IC 計算、統計サマリ）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコア）
- 市場レジーム判定（MA と LLM による合成）
- 各種ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計上のポイント：
- DuckDB / SQLite をデータ層に使う。DuckDB は主にリサーチ／AI 用の大規模クエリ向け、SQLite は監視ログや注文履歴の永続化に使用。
- 環境変数（.env / .env.local を自動ロード）で構成を切り替え。KABUSYS_ENV によって paper_trading / live / development を選択可能。
- OpenAI 呼び出しは冪等性・バックオフ・レスポンス検証を考慮して実装されている（news_nlp / regime_detector）。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動ロード
  - Settings クラス（KABUSYS_ENV / DB パス / 各種閾値 等）
- 監視（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセスの存在確認 / データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン検出・ポジション上限検出、ダッシュボード更新
  - KillSwitch: 指定条件で kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - MonitoringEngine: 上記を束ねたポーリングループ
  - Streamlit ダッシュボード（監視結果を可視化）
- 実行（execution）
  - OrderManager / OrderRepository / Reconciler：発注フローと起動時リコンシリエーション
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerFactory を通じて本番・Mock（paper_trading）を切り替え
- ポートフォリオ（portfolio）
  - 候補選定、等重・スコア重み付け、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ（research）
  - モメンタム / ボラティリティ / バリューファクターの算出（DuckDB 経由）
  - 将来リターン・IC（Spearman）・統計サマリ
- AI（ai）
  - news_nlp: OpenAI を用いた銘柄別センチメントスコア化（ai_scores に書き込み）
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成してレジーム判定（market_regime に書き込み）
- ツール
  - paper_verification_report.py: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

---

## セットアップ手順

前提: Python 3.10 以上（ソースの型アノテーションで | を使用しているため）。実環境の Python バージョンに合わせてください。

1. リポジトリをクローンし、ソースが入ったディレクトリへ移動
   - （例）git clone ... && cd repo

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - 一覧（代表例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   ※ 実運用では requirements.txt を用意して pip install -r requirements.txt してください（本リポジトリにファイルがない場合は上記パッケージを参考にしてください）。

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（読み込みは OS 環境変数より低優先）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主要な環境変数（例）:
     - KABUSYS_ENV = development | paper_trading | live
     - OPENAI_API_KEY = (AI を使う場合必須)
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading の場合、デフォルト: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (LINE 通知)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - MONITOR_POLL_INTERVAL (監視ポーリング間隔, 秒。run_monitoring で上書き可能)
     - PAPER_FILL_MODE (paper_trading の MockBroker の振る舞い: instant|partial|never|reject)

5. データディレクトリの作成
   - data ディレクトリを作成しておく（DB の出力先など）
   - mkdir -p data

---

## 使い方（起動 / 実行例）

注意: 実行はパッケージとして参照する前提です。パッケージがインストールされていない場合はプロジェクトルートから `python -m kabusys.<module>` で起動できます（src が PYTHONPATH に入っていること）。

1. 監視プロセスの起動（Monitoring）
   - 目的: SystemMonitor をポーリングして監視メトリクスを SQLite に保存
   - コマンド例:
     - KABUSYS_ENV=production MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
   - 振る舞い:
     - プロセス優先度を "high" に設定しようとします（psutil による。権限がないと警告）。
     - Settings に応じた sqlite_path (monitoring DB) と duckdb_path を開き、SystemMonitor を定期実行。
     - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を上書き可能（デフォルト: 60 秒）。

2. 実行エンジン（ExecutionEngine）の起動
   - 目的: 注文実行フローを開始（本番あるいは paper_trading）
   - コマンド例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 振る舞い:
     - KABUSYS_ENV==paper_trading の場合、MockBrokerClient を利用し、paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録します。
     - 本番時は本番設定の Broker を使用します（BrokerFactory 経由）。
     - プロセス優先度を "high" に設定しようとします。

3. Streamlit 監視ダッシュボード
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 機能:
     - Dashboard（portfolio value / cash / drawdown）
     - Positions / Orders / System（最新ステータス、最近のイベント等）
   - 注意:
     - Monitoring が生成する SQLite を読み取り専用で開くため、MonitoringEngine を先に起動しておくと有用です。

4. Paper Trading 検証レポート
   - 目的: Paper Trading DB（trade_logs / system_status 等）から検証レポートを生成
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   - 出力:
     - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など
     - PASS/FAIL 判定（閾値はコード内で定義）

5. AI を使ったニューススコアリング / レジーム判定（ライブラリ関数）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡してターゲット日を指定し、OpenAI API キーを渡す（または OPENAI_API_KEY 環境変数を準備）
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF の MA とマクロニュースを合成して market_regime テーブルへ保存

   - 注意:
     - OpenAI の API キー（OPENAI_API_KEY）が必要
     - API の呼び出しはレートリミット・サーバーエラー等に対してリトライ・フェイルセーフが実装されていますが、コストには注意してください。

6. その他ユーティリティ
   - 設定は Settings クラス（kabusys.config）を通じて読み取ります。自動的に .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
   - プロセス優先度・CPU affinity は psutil を通じて設定します。権限不足の場合は警告が出ます。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（default: development）
  - paper_trading の場合は Mock ブローカーと専用 SQLite を使用します
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の実行に必須）
- PDOCKDB_PATH: data/kabusys.duckdb（DuckDB のデフォルトパス）
- SQLITE_PATH: data/monitoring.db（監視ログのデフォルト SQLite）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 SQLite）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で読み込み）
- PID_FILE_PATH: 実行エンジン用 PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
    - パッケージ初期化（バージョン等）
  - config.py
    - 環境変数読み込み・Settings クラス
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替あり）

  - monitoring/
    - monitoring_db.py
      - SQLite ベースの監視 DB（テーブル作成・永続化メソッド）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度チェック
    - trade_monitor.py
      - 注文滞留・約定異常検出
    - risk_monitor.py
      - ドローダウン・ポジション上限監視、dashboard 更新
    - kill_switch.py
      - kill.flag の作成 / 判定ロジック
    - alert_manager.py
      - LINE API 経由の通知（クールダウン管理）
    - monitoring_engine.py
      - 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py
      - Streamlit を使った監視ダッシュボード

  - execution/
    - order_manager.py
    - order_repository.py (参照されるが詳細ファイル内容は長いため略)
    - reconciler.py
    - execution_engine.py (参照)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - risk_manager.py
    - order (その他関連モジュール)
    - （実行ロジックとブローカー API の抽象化）

  - portfolio/
    - portfolio_builder.py
      - 候補選定・等重・スコア重み計算
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
    - position_sizing.py
      - 株数決定・単元丸め・aggregate cap
    - __init__.py

  - research/
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ等の解析ユーティリティ
    - __init__.py

  - ai/
    - news_nlp.py
      - raw_news を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py
      - マクロニュース + ETF MA から市場レジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py
      - Paper Trading DB から検証レポートを生成
    - __init__.py

  - utils/
    - process_priority.py
      - プロセス優先度・CPU affinity のユーティリティ
    - __init__.py

（上記は主なファイル群の抜粋です。細かい補助モジュールや DB スキーマ等はソースをご参照ください）

---

## 運用上の注意点 / Tips

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading を使用すると paper SQLlite に書き込みます。
- OpenAI を使う処理は API コストとレート制限に注意してください。news_nlp / regime_detector はリトライ・フェイルセーフを備えていますが、運用ルールを決めてください。
- process priority / cpu affinity の設定は OS により挙動が異なり、権限が必要な場合があります。権限不足時は警告が出ますが、処理は継続します。
- monitoring のポーリングで MONITOR_POLL_INTERVAL が 0 以下など不正な値だと警告してデフォルト値にフォールバックします。
- .env のパースはシェルの export やクォート、コメント等に柔軟に対応する独自実装を含みますが、複雑なケースは避けるのが無難です。

---

この README はリポジトリ内のソースコードに基づく要約ドキュメントです。運用前には各モジュールのドキュメント・docstring を必ず確認し、環境ごとの設定（特に API キー・DB パス・閾値）を適切に構成してください。必要であれば README に追加したい項目（例：詳細な環境変数一覧、コマンド一覧、開発フロー）を教えてください。