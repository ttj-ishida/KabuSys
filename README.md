# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行コンポーネント）。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（本番・模擬）、監視・アラート、LLM を使ったニュースセンチメント評価などの機能を含みます。

---

## プロジェクト概要

KabuSys は以下の主要領域で構成されています。

- execution: ブローカー連携、注文管理、再整合（reconciliation）やリスク管理を担う実行エンジン
- monitoring: システム状態・注文・リスク監視、ダッシュボード、アラート（LINE）および kill-switch
- research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制限などのポートフォリオ構築ロジック
- ai: ニュース NLP によるセンチメントスコアや市場レジーム判定（OpenAI API を使用）
- tools: Paper Trading の検証レポート生成スクリプトなど

設計方針の要点：
- DuckDB / SQLite をデータ層に使用（分析用は DuckDB、監視・注文ログは SQLite）
- 環境変数 / .env による設定（自動読み込み機能あり）
- 本番 / paper_trading（模擬）モードの分離
- LLM 呼び出しは堅牢に（リトライ・バリデーション・フェイルセーフ）

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/模擬（paper_trading）モードの切替
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler を組み合わせた処理
- Monitoring（run_monitoring.py / MonitoringEngine）
  - CPU/メモリ/ディスク、Execution プロセス監視
  - 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch による停止フラグ出力
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- AI / LLM
  - news_nlp.score_news: ニュース記事の銘柄別センチメント算出・ai_scores への書き込み
  - regime_detector.score_regime: ETF MA とマクロ記事の LLM センチメントを合成し市場レジーム判定
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- Portfolio
  - 候補選定、等金額/スコア重み付け、リスク調整（セクター上限、レジーム乗数）
  - 単元株丸め・aggregate cap を考慮したポジションサイズ算出
- Tools
  - paper_verification_report: Paper Trading データから検証レポートを生成

---

## セットアップ手順

以下は開発環境 / 実行環境を整える最低限の手順例です。

1. リポジトリをクローン
   - git clone ... && cd repository

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   主要な依存（ファイル内から推測）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   - そのほか必要に応じて（例: pytest 等）

   例:
   - pip install duckdb psutil openai requests streamlit

   ※ 実際の requirements.txt がある場合はそれを使ってください。

4. 環境変数設定（.env）
   プロジェクトルートに `.env` または `.env.local` を作成できます。.env.example（存在する場合）を参照してください。

   主要な環境変数（抜粋）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （任意/使用する場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須: 実ブローカー使用時）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB データファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）
   - LOG_LEVEL: DEBUG | INFO | ...（ログレベル）

   設定ファイルは自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。

5. データディレクトリの作成
   - mkdir -p data

   実行時に SQLite/ DuckDB ファイルは自動で作成・マイグレーションされます（monitoring DB は init_monitoring_db が実行されます）。

---

## 使い方（実行例）

- 監視ループを起動（Production 用 sqlite を使用）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き可能（秒、デフォルト 60）
  - python -m kabusys.run_monitoring

  例:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- 実行エンジンを起動（本番 / paper_trading 切替は KABUSYS_ENV により決定）
  - python -m kabusys.run_execution

  例（模擬運用）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - paper_trading 時は MockBrokerClient が使われ、データは data/paper_trading.db に保存されます（本番 DB と分離）。

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db PATH` で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

- AI 関連（プログラム呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意 / 補足:
- run_monitoring.py と run_execution.py は起動時にプロセス優先度を "high" に設定しようとします（psutil による操作）。権限が足りない場合は警告を出してスキップします。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を生成すると ExecutionEngine 側で停止トリガーとなる仕組みがあります。監視起動時の設定で必要に応じて消去されます。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード（本番ブローカー接続時必須）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, regime_detector）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb）
- PAPER_FILL_MODE: instant | partial | never | reject
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 読み込みと Settings
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py         — ETF MA + マクロセンチメント → レジーム判定
  - monitoring/
    - monitoring_db.py           — SQLite スキーマ / 永続化層
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
    - order_repository.py        (実装ファイル群は多数)
    - execution_engine.py       (エンジン本体)
    - broker_factory.py         (ブローカークライアント生成)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (想定データフォルダ)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)

上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。

---

## 追加の注意点 / 運用上のポイント

- Paper Trading モードは本番 DB と完全に分離されるよう設計されています。KABUSYS_ENV=paper_trading を利用してください。
- LLM 使用箇所（news_nlp / regime_detector）は OpenAI API キーが必要です。API 呼び出しは失敗時にフェイルセーフ（スコア 0.0 等）で継続する設計です。
- monitoring の DB マイグレーションは起動時に自動で処理されます（列追加等の簡易マイグレーション）。
- デバッグ時は Settings.log_level / LOG_LEVEL を調整してください。
- process priority / cpu affinity 設定は psutil を利用します。権限がない環境では無視されます。

---

必要に応じて README を拡張して、セットアップ用の requirements.txt、.env.example、起動用 systemd / supervisor unit ファイル、テストの実行方法などを追記できます。どの点をより詳しく記述したいか教えてください。