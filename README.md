# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。ポートフォリオ構築、注文実行、監視、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含み、ローカル SQLite / DuckDB を使ってデータ永続化や解析を行います。

以下はこのリポジトリの概要、機能、セットアップ手順、主要な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買に関する主要機能（ファクター計算、ポートフォリオ構築、発注エンジン、監視、AI を用いたニュース分析・レジーム判定）をモジュール化して提供。
- 永続化:
  - 監視ログ等: SQLite（デフォルト `data/monitoring.db`）
  - 分析データ: DuckDB（デフォルト `data/kabusys.duckdb`）
  - Paper Trading 用: `data/paper_trading.db`（`KABUSYS_ENV=paper_trading` 時に使用）
- 設計方針:
  - DuckDB によるデータ集計（prices_daily / raw_financials / raw_news 等）
  - API 呼び出し（ブローカー / OpenAI 等）は抽象化され、テストしやすい設計
  - 監視コンポーネントは別プロセスでポーリング運用可能

---

## 主な機能一覧

- execution（発注関連）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerClientFactory による本番 / モック切替（`KABUSYS_ENV=paper_trading` 時は MockBrokerClient）
  - OrderManager / OrderRepository / Reconciler による自動復旧と同期
  - RiskManager による発注制限（位置上限、利用率、ドローダウン等）

- monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス状態、データ鮮度を監視
  - TradeMonitor: 滞留注文、約定異常価格を検出
  - RiskMonitor: ドローダウン・ポジション上限を監視
  - KillSwitch: 指定条件で ExecutionEngine 停止フラグ（data/kill.flag）を生成
  - AlertManager: LINE へのプッシュ通知（クールダウン管理含む）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
  - 監視用 SQLite スキーマの初期化（init_monitoring_db）

- portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等配分 / スコア配分（calc_equal_weights / calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- research（リサーチ）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC 計算、統計サマリ（feature_exploration）

- ai（LLM を使った機能）
  - news_nlp: raw_news を LLM でスコアリングして ai_scores へ書込
  - regime_detector: マクロ記事 + ETF MA を組合せて市場レジーム判定（market_regime テーブルへ書込）

- tools
  - paper_verification_report: Paper Trading DB を集計して検証レポートを標準出力へ出力

---

## 前提 / 依存関係

- Python 3.10 以上（型ヒントで | 演算子を使用しているため）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
- これらはプロジェクトの requirements.txt があればそれを使うのがベストです。なければ個別にインストールしてください。
  - 例:
    - pip install duckdb psutil requests streamlit openai

---

## 環境変数 / .env

プロジェクトは .env / .env.local の自動読み込みをサポートします（プロジェクトルートに .git または pyproject.toml がある場合）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

重要な環境変数（主なもの）:

- KABUSYS_ENV: 実行環境（development | paper_trading | live）※デフォルトは development
  - paper_trading のときはブローカーがモックになり、DB は `PAPER_TRADING_SQLITE_PATH` を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィル動作（instant / partial / never / reject）
- PID_FILE_PATH: ExecutionEngine 用 pid ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

サンプル .env（.env.example をもとに作成してください）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
```

---

## セットアップ手順

1. リポジトリをクローンして、推奨 Python バージョンの仮想環境を作る:
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

2. 必要パッケージをインストール:
   - pip install --upgrade pip
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`。）

3. .env をプロジェクトルートに作成して必要な環境変数を設定:
   - .env.example を参照して設定してください。

4. データディレクトリを作成:
   - mkdir -p data

5. DuckDB / SQLite ファイルは初回起動時に自動でテーブルが作成されるコンポーネントが多いです（例: monitoring の init_monitoring_db）。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動（本番 / Paper 切替は KABUSYS_ENV で）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution
  - 動作: プロセス優先度を高く設定 → DB に接続 → BrokerClient を作成 → ExecutionEngine.run_session() を実行

- Monitoring（SystemMonitor 単体）をポーリングで起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 動作: 監視用 SQLite に記録し、System/Trade/Risk モニタを一定間隔で実行

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で開く）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI系関数（プログラムから呼び出す例）
  - ニューススコアリング:
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")

---

## 運用上の注意 / 実装メモ

- Paper Trading と本番は DB を分離しているため、`KABUSYS_ENV=paper_trading` を使うと実際の発注は発生せずテスト用 DB に記録されます。
- Monitoring は本番 sqlite_path を常に使う設計の箇所があるため（run_monitoring）、環境に関係なく本番 DB に記録したい場合は設定を確認してください（コードのコメント参照）。
- OpenAI 呼び出しはリトライ・フェイルセーフを備えており、API エラー時は（例: レスポンスが取れない場合）スコアをスキップまたはデフォルト値で続行する設計です。
- PID ファイル / kill.flag を使ったプロセス管理に対応（ExecutionEngine 側と連携）。
- MonitoringDB のスキーマは init_monitoring_db() で冪等に作成・マイグレーションできます。

---

## ディレクトリ構成（主要ファイル）

（`src/kabusys/` 以下）

- __init__.py
- config.py — 環境変数/設定管理（.env 自動読み込み）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- execution/
  - broker_factory.py (ブローカークライアント生成)
  - execution_engine.py (エンジン本体)
  - order_manager.py (発注状態管理)
  - order_repository.py (SQLite ベースの注文永続化)
  - reconciler.py (再起動時の同期・リコンシリエーション)
  - risk_manager.py (発注リスク管理)
  - ...（broker_api など）

- monitoring/
  - monitoring_db.py (SQLite テーブル定義 + MonitoringDB ラッパー)
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (LINE 通知)
  - monitoring_engine.py (複数 monitor を束ねる)
  - streamlit_dashboard.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py (momentum / value / volatility)
  - feature_exploration.py (forward returns / IC / summary)
  - __init__.py

- ai/
  - news_nlp.py (ニュース NLP スコアリング / OpenAI)
  - regime_detector.py (市場レジーム判定)
  - __init__.py

- tools/
  - paper_verification_report.py (Paper Trading 検証レポート)

- utils/
  - process_priority.py (プロセス優先度 / CPU affinity セット)

---

## よくある質問（Q&A）

- Q: Paper Trading と本番データは混ざりますか？
  - A: 原則分離されています。`KABUSYS_ENV=paper_trading` のときに `PAPER_TRADING_SQLITE_PATH` が使用されます。

- Q: 監視（monitoring）はどのように起動しますか？
  - A: `python -m kabusys.run_monitoring` を推奨。環境変数 `MONITOR_POLL_INTERVAL` で間隔（秒）を変更できます（デフォルト 60 秒）。

- Q: OpenAI キーはどの環境変数を使いますか？
  - A: `OPENAI_API_KEY`。ai モジュールの各関数は引数でキーを渡すことも可能です。

---

README に書かれている以外の詳細（実運用の仕組みや ExecutionEngine の内部実装、DB スキーマの細部など）は各モジュールの docstring を参照してください。必要であれば README に追記する内容（例: サンプル .env.example、systemd / supervisor 用の起動スクリプト例、CI / テスト手順など）を教えてください。