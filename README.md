# KabuSys

日本株向けの自動売買システムのコアライブラリ（モジュール群）。  
主に以下の役割を持つコンポーネントを含みます。

- シグナル → 発注を行う ExecutionEngine（発注ロジック / Order 管理 / Reconciliation）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約など）
- 研究用ファクター計算（DuckDB 上の時系列データ参照）
- ニュース NLP / 市場レジーム判定（OpenAI を利用したセンチメント評価）
- 監視（システム・注文・リスク監視）、監視データ永続化（SQLite）、Streamlit ダッシュボード
- 実行プロセスの優先度設定・CPU Affinity ユーティリティ

以下はリポジトリ内のコードを基にした README（日本語）です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動例）
- 環境変数（主要項目）
- ディレクトリ構成（主要ファイル説明）
- 注意・トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株自動売買のための内部ロジック群です。  
価格・財務データを DuckDB で参照してファクター計算やポートフォリオ構築を行い、ExecutionEngine がブローカーへ発注します。監視コンポーネントはシステム状態や注文の異常を検知し、LINE に通知したり kill.flag を書くことで実行エンジンを安全に停止できます。AI 系機能（ニュースのセンチメント、レジーム検出）は OpenAI API を利用します。

---

## 機能一覧

- ポートフォリオ関連
  - 候補選定（select_candidates）
  - 等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用 / レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- リサーチ / ファクター
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン計算・IC（Information Coefficient）等の統計ユーティリティ
- 実行（Execution）
  - OrderManager（発注・同期・キャンセル）
  - Reconciler（再起動後の状態回復）
  - ExecutionEngine（シグナル処理ループ / push ドレイン）
  - RiskManager（レート制限・ドローダウン・利用率制御）※設定を注視
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite）による永続化
  - AlertManager（LINE Push 通知）
  - KillSwitch（data/kill.flag による停止指示）
  - Streamlit ベースの監視ダッシュボード
- AI
  - ニュースを集約して OpenAI でセンチメントを算出し ai_scores に書き込む（kabusys.ai.score_news）
  - ETF の MA とマクロニュースから市場レジームを判定して market_regime に書き込む（kabusys.ai.regime_detector.score_regime）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
  - 環境変数自動ロード（.env / .env.local をプロジェクトルートから読み込み）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 記法を使用）
- Git リポジトリ（.git または pyproject.toml がプロジェクトルートとして検出されます）

推奨手順（UNIX 系の例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数ファイル（.env）を用意
   - プロジェクトルートに .env（または .env.local）を作成します。
   - 主要な変数は下の「環境変数」セクションを参照してください。
   - 自動ロードはデフォルトで有効。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. DuckDB / SQLite の初期データ
   - research / ai 機能は DuckDB の prices_daily / raw_financials / raw_news 等テーブルを期待します。これらのスキーマとデータは別途準備してください（データ投入処理は本リポジトリに含まれていない場合があります）。
   - monitoring SQLite（data/monitoring.db）はスクリプト実行時に必要テーブルが自動作成されます（init_monitoring_db による冪等作成）。

---

## 使い方（起動例）

※ パッケージをインストールせず、ソースツリー直下で動かす場合は PYTHONPATH に src を含めて実行してください（例: PYTHONPATH=src python -m kabusys.run_monitoring）。

1. 監視ループの起動（System/Trade/Risk Monitor）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
   - 実行例:
     - python -m kabusys.run_monitoring
     - または: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   - 補足:
     - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用します。
     - 起動時にプロセス優先度を "high" に設定しようとします（psutil による設定。権限が無い場合は警告が出ます）。

2. ExecutionEngine（発注） の起動
   - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。
   - 実行例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - KABUSYS_ENV=live python -m kabusys.run_execution

   - 補足:
     - 起動時に pid ファイル（Settings.pid_file_path）を書き、KILL フラグやプロセスの存在を監視します。
     - Settings.kill_flag_clear_on_start が有効 (1) の場合、起動時に kill.flag をクリアします。

3. Streamlit ダッシュボード
   - 起動コマンド（Monitoring 側の db を読み取る・読み取り専用推奨）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

   - Streamlit は監視DBを read-only URI で開くため、MonitoringEngine が稼働していることを前提とします。

4. AI（ニューススコア・レジーム判定）
   - OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を設定）。
   - プログラム的に呼び出す例（REPL / スクリプト内）:
     - from kabusys.ai.news_nlp import score_news
       → score_news(duckdb_conn, target_date, api_key="sk-...")
     - from kabusys.ai.regime_detector import score_regime
       → score_regime(duckdb_conn, target_date, api_key="sk-...")

   - 失敗時は例外やログを出しますが、AI処理は失敗してもシステムを停止させない設計の箇所が多くあります（フェイルセーフ）。

---

## 主な環境変数（要約）

設定は .env / .env.local または OS 環境変数から読み込まれます。プロジェクトルートの .env が自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要変数（デフォルト値 / 説明）:

- KABUSYS_ENV (development | paper_trading | live)  
  - 動作モード。paper_trading の場合、専用 DB に切替えて MockBroker を使用。

- JQUANTS_REFRESH_TOKEN  
  - J-Quants API 用のトークン（必須扱いのプロパティあり）。

- KABU_API_PASSWORD  
  - kabu ステーション（ブローカー）API のパスワード。

- OPENAI_API_KEY  
  - OpenAI API キー（AI 機能に必要）。score_news / score_regime はキーがない場合例外になる。

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID  
  - AlertManager（LINE push）用。未設定時は送信をスキップしてログに出す。

- DUCKDB_PATH (data/kabusys.duckdb)  
  - DuckDB ファイルパス（価格・財務・ニュース等の参照先）。

- SQLITE_PATH (data/monitoring.db)  
  - 監視ログ用 SQLite（MonitoringDB）。Monitoring は常に本番 sqlite_path を使います。

- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)  
  - paper_trading モード時に使用する SQLite。

- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")  
  - MockBroker の約定振る舞い（paper_trading 用）。

- PID_FILE_PATH (data/execution.pid)  
  - ExecutionEngine が使用する PID ファイルパス。

- KILL_FLAG_PATH (data/kill.flag)  
  - KillSwitch が書き込むフラグファイルパス。

- KILL_FLAG_CLEAR_ON_START (0|1)  
  - ExecutionEngine 起動時に kill.flag を自動クリアするか。

- LOG_LEVEL (INFO 等)、MONITOR_POLL_INTERVAL（run_monitoring の秒数上書き）

- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT  
  - SystemMonitor の閾値（使用箇所で参照）。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 内の主要モジュールと概要です。

- kabusys/
  - __init__.py
    - パッケージ定義、バージョン
  - config.py
    - Settings クラス：環境変数・.env の自動読み込み、各種設定プロパティ（DBパス、env 判定 等）
  - utils/
    - process_priority.py
      - psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - position_sizing.py
      - 株数決定・aggregate cap など（calc_position_sizes）
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - research/
    - factor_research.py
      - momentum / volatility / value のファクター計算（DuckDB 接続必須）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI で銘柄ごとにセンチメント評価し ai_scores に書き込む
    - regime_detector.py
      - ETF MA とマクロニュースの LLM 評価を組み合わせて market_regime を判定・書き込み
  - monitoring/
    - monitoring_db.py
      - SQLite のテーブル初期化・読み書きラッパー（MonitoringDB）
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/実行プロセスの監視
    - trade_monitor.py
      - 注文滞留・約定異常チェック
    - risk_monitor.py
      - ダッシュボードからドローダウン/ポジション上限を判定しログ・リスクイベント記録
    - kill_switch.py
      - data/kill.flag の書き込み・削除ロジック
    - alert_manager.py
      - LINE Push 送信ラッパー（クールダウン管理あり）
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリングするエンジン
    - streamlit_dashboard.py
      - Streamlit を使った監視ダッシュボード（起動方法はファイル冒頭参照）
  - execution/
    - execution_engine.py
      - ExecutionEngine 本体（シグナル処理 + push ドレイン）
    - order_manager.py
      - 発注ワークフロー（create/send/sync/cancel）と永続化の扱い（クラッシュ安全設計）
    - reconciler.py
      - 起動時の再同期（OrderSent などの不整合解消）・ポジション差異検出
    - その他（order_repository, order_record, broker_api 等は本リポジトリ内にある前提）
  - run_monitoring.py
    - SystemMonitor をポーリングで回す起動スクリプト（MONITOR_POLL_INTERVAL による間隔指定可）
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（paper_trading モードは MockBroker を使用）

---

## 注意・トラブルシューティング

- OpenAI API
  - score_news / score_regime は OPENAI_API_KEY が未設定だと例外を送出します。テスト時やオフライン時は呼び出しを避けてください。
  - API レート制限やネットワーク障害はリトライ実装がありますが、過剰な呼び出しは避けてください。

- psutil による優先度変更
  - 高優先度設定は権限が必要な場合があります。設定に失敗すると警告ログが出ますが処理は続行します。

- データ鮮度
  - SystemMonitor は DuckDB の prices_daily テーブルから最終価格日を取得してデータ鮮度を判定します。DuckDB のデータが準備されていないとデータ鮮度 NG となります。

- paper_trading
  - KABUSYS_ENV=paper_trading のとき、発注は MockBrokerClient を使い data/paper_trading.db に記録されます。本番データベースとは完全に分離されますが、.env の DB パス設定を確認してください。

- kill.flag / PID 管理
  - Execution 起動時は pid ファイルを作成します。stale PID 検出時は PID ファイルを削除してリスクイベントに記録します。起動時に kill.flag を自動でクリアするかは設定で制御できます。

---

この README はリポジトリ内のソースコード（src/kabusys 以下）を基に作成しています。より詳細な設計書（PortfolioConstruction.md, StrategyModel.md など）はソース内コメントや別途文書を参照してください。必要であれば各コンポーネントの使い方や設定例を追記できます。