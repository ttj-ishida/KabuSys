# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視を行う小規模なシステム群です。本リポジトリはトレーディング実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ用ファクター計算、LLMを用いたニュースセンチメント処理などのモジュールで構成されています。

以下はこのコードベースの概要、機能、セットアップ・実行方法、ディレクトリ構成のまとめです。

注意: 本ドキュメントはソース内の記述（docstring / コメント / コード）に基づいて作成しています。

---

## プロジェクト概要

- 目的: 日本株の自動売買に必要な実行ロジック、リスク管理、監視、リサーチ（ファクター計算）およびニュースの NLP スコアリングを提供する。
- 主なコンポーネント:
  - ExecutionEngine（発注・リスク管理・オーダー管理・リコンシリエーション）
  - Monitoring（システム状態、注文滞留、ドローダウン等の監視とアラート）
  - Portfolio construction（候補選定、重み付け、株数決定）
  - Research（ファクター計算、特徴量解析）
  - AI（ニュースNLP / 市場レジーム判定） — OpenAI API を利用
  - ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

---

## 主な機能一覧

- Execution
  - ブローカークライアントを透過的に利用（本番 / paper_trading 用に分離）
  - OrderManager による注文作成・同期（Duplicate チェック、状態遷移）
  - Reconciler による起動時の注文・ポジション照合（自動復旧）
  - RiskManager による発注前のリスクチェック（上限、利用率、ドローダウン等）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス健全性 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格監視
  - RiskMonitor: ドローダウン・ポジション上限監視（ダッシュボード更新 / リスクログ記録）
  - KillSwitch: リスクトリガーにより ExecutionEngine 停止（flagファイル書き込み）
  - AlertManager: LINE Push での通知（クールダウン管理）
  - Monitoring DB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard を永続化

- Portfolio
  - 候補選定、等配分／スコア配分、セクター制限、レジーム乗数、数量（lot）丸め、aggregate cap 調整

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Spearman）、統計サマリー、rank ユーティリティ

- AI
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコアを計算して書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: Monitoring DB を読み取る Streamlit ダッシュボード

---

## 動作環境・依存関係

- 推奨 Python バージョン: 3.10+
  - （ソースで | タイプ注釈や新しい構文を使用しているため）
- 主要パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使用する場合）
- インストール例:
  - 仮想環境作成後:
    - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt が無い場合は上記を参考にしてください）

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境 (development | paper_trading | live)。デフォルト: development
  - paper_trading の場合、MockBroker を使用し Paper 用 SQLite DB を分離して利用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB データパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

.env 自動読み込み:
- プロジェクトルートに .env / .env.local がある場合、自動で読み込まれます（ただし OS 環境変数が優先）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数が未設定の場合は Settings モジュールが ValueError を投げます（起動前に .env を準備してください）。

---

## セットアップ手順（ローカルで動かす場合）

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. .env を用意（ルートに配置）。例（最低限）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_token
   - KABU_API_PASSWORD=your_kabu_password
   - OPENAI_API_KEY=your_openai_key
   - KABUSYS_ENV=development
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
5. data ディレクトリや DB ファイルは自動で作成されますが、適宜ディレクトリ作成を行ってください:
   - mkdir -p data

---

## 実行方法（主要スクリプト）

注意: このプロジェクトはパッケージとして import 可能な状態で実行することを想定しています。ソースが `src/` にある場合、ルートで PYTHONPATH を通すかパッケージとしてインストールしてください。

- 監視ループ起動（Monitoring）
  - モジュール: src/kabusys/run_monitoring.py
  - 説明: SystemMonitor を周期的に実行して monitoring DB に記録する。常に本番 sqlite_path を使用（環境に関わらず）。
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト: 60）
  - 実行例:
    - PYTHONPATH=./src python -m kabusys.run_monitoring
  - 停止:
    - プロジェクトルートの data/stop_requested.flag を作成するとループが終了します（stop flag）。
    - または Ctrl+C（KeyboardInterrupt）。

- 実行エンジン起動（Execution）
  - モジュール: src/kabusys/run_execution.py
  - 説明: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録して実運用 DB と分離。
  - 実行例:
    - PYTHONPATH=./src KABUSYS_ENV=development python -m kabusys.run_execution
    - Paper trading:
      - PYTHONPATH=./src KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると安全に停止されます（または kill.flag が書き込まれていると起動を回避）。

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 説明: Paper Trading 用の SQLite（デフォルト data/paper_trading.db）から各種指標を集約して表示
  - 実行例:
    - PYTHONPATH=./src python -m kabusys.tools.paper_verification_report
    - 範囲指定:
      - PYTHONPATH=./src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - PYTHONPATH=./src python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- Streamlit ダッシュボード（監視）
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 起動例:
    - PYTHONPATH=./src streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: Monitoring DB の読み取り専用ビュー（ポジション、直近注文、システム状態、リスクログなど）。

- AI 機能（ニューススコアリング / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キー（OPENAI_API_KEY または引数）が必要。API 呼び出しはリトライ・フェイルセーフの処理を含みます。

---

## 停止・フラグファイル

- data/stop_requested.flag
  - run_monitoring / run_execution がポーリング中に存在を検出するとシャットダウン処理を行います（即時停止の合図）。
- data/kill.flag
  - KillSwitch が検出トリガー（ドローダウンやポジション上限等）により書き込むことで ExecutionEngine に対して停止指令を与えるために使用します。
- data/execution.pid
  - ExecutionEngine 起動時の PID を格納するファイル。SystemMonitor はこのファイルを見てプロセス健全性を判定します。stale PID は自動で削除されリスクログに記録されます。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys 配下）の主なファイル・モジュールです。実際のファイル一覧はリポジトリに依存しますが、ここでは現在の実装で存在するモジュールを示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py            — ニュースセンチメント処理（OpenAI）
      - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py       — monitoring SQLite テーブル定義 / ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - (その他 execution 関連モジュール: broker_factory / execution_engine / order_repository など)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/                     — 実行時に生成される（data/*.db, flags, pid など）

---

## 運用上の注意点 / 補足

- Paper Trading と本番データは意図的に分離されている:
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用。
- Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計箇所があるので運用時は注意。
- OpenAI API を使う処理は外部 API に依存するため、API キーの管理・レート制限・コストに注意してください。
- Process priority / CPU affinity は psutil を使って設定します。権限不足や未対応 OS では警告を出してスキップされます。
- DB マイグレーションは軽微な変更（カラム追加）を実行時に自動で行う実装があります（monitoring_db.init_monitoring_db）。
- .env の読み込みはプロジェクトルートを .git または pyproject.toml を基に探索します。CWD に依存しない仕様。

---

## よくある操作例（まとめ）

- 仮想環境・依存ライブラリの準備
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- 監視プロセス起動
  - PYTHONPATH=./src python -m kabusys.run_monitoring

- 実行エンジン起動（paper_trading）
  - PYTHONPATH=./src KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - PYTHONPATH=./src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - PYTHONPATH=./src streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

もし README に追加したい内容（例: サンプル .env.example、CI 用のセットアップ手順、より詳しい ExecutionEngine の設定項目や API モックの使い方、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記・整備します。