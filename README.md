# KabuSys

日本株自動売買システムのライブラリ / ツール群の README（日本語）

このリポジトリは KabuSys（日本株自動売買）向けのコアモジュール群を含みます。戦略のためのファクター計算・探索、ポートフォリオ構築、注文管理、監視・アラート、AI（ニュース/NLP／レジーム判定）連携などを提供します。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株自動売買のためのモジュール群（戦略研究、ポートフォリオ構成、発注/実行、監視、AI ベースのニュースセンチメント/レジーム判定、運用検証ツール）
- 実装言語: Python
- コア設計方針:
  - DuckDB / SQLite を使ったデータ処理・永続化
  - 本番・Paper Trading を環境変数で切替
  - OpenAI を用いたニュースセンチメント評価（外部 API）
  - 監視ロジックはロギング＋SQLite に永続化し、LINE によるアラート送信が可能

---

## 主な機能一覧

- 戦略・リサーチ
  - ファクター計算（momentum / volatility / value 等） — kabusys.research.calc_*
  - 将来リターン・IC 計算、ファクター統計サマリー

- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算（単元丸め、aggregate cap）、セクター集中除外、レジーム乗数

- 実行・注文管理
  - OrderManager / ExecutionEngine（発注フロー、リスク管理、リコンシリエーション）
  - Reconciler による起動時の注文・ポジション同期

- 監視
  - SystemMonitor（プロセス生存、CPU/メモリ/ディスク、データ鮮度）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）、KillSwitch（停止フラグの書き込み）
  - MonitoringEngine: 各モニタを束ねて定期ポーリング、AlertManager（LINE Push）で通知
  - streamlit ベースの監視ダッシュボード（read-only 接続）

- AI（OpenAI 経由）
  - news_nlp: ニュースの銘柄別センチメントを LLM へ送り ai_scores に書き込む
  - regime_detector: ETF（1321）の MA やマクロニュースによる日次レジーム判定と書き込み

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード起動スクリプト

---

## 必要依存（抜粋）

実行に必要な外部パッケージ（コードから判別）:

- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使用する場合)

インストール例:
pip install duckdb psutil requests openai streamlit

（実際の requirements.txt がある場合はそちらを使用してください）

---

## 環境変数 / 設定

Settings クラス（kabusys.config）で環境変数から設定を取得します。主なキー:

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE Push 用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker fill モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除する場合 "1"
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、run_monitoring 用。デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合に "1"

.env の読み込みルール:
- プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env（上書き不可） → .env.local（override=True）を読み込む
- OS 環境変数が優先される（保護される）

---

## セットアップ手順（ローカル）

1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール:
   pip install -r requirements.txt
   または:
   pip install duckdb psutil requests openai streamlit
3. プロジェクトルートに .env（必要な環境変数）を用意
   - 例:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
4. データディレクトリを作成:
   mkdir -p data
5. （任意）DuckDB / SQLite の初期データを用意する（prices_daily, raw_financials, raw_news 等は戦略実行や AI 機能で参照されます）
6. （Paper Trading を使う場合）KABUSYS_ENV=paper_trading を指定すると paper 用 SQLite に分離して記録します

---

## 使い方（主要スクリプト）

- 監視ループを起動（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒指定できる（デフォルト 60）
  - 監視は Settings の sqlite_path（本番 DB）を常に使用します（環境にかかわらず）

- 実行エンジンを起動（Execution）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込む（本番 DB と完全分離）
  - 起動時にプロセス優先度を high に設定し、PID ファイルを使用します

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  追加オプション:
    --from YYYY-MM-DD   レポート開始日
    --to   YYYY-MM-DD   レポート終了日
    --db   PATH         SQLite DB パス（--db > 環境変数 PTPATH > data/paper_trading.db の順）
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit 監視ダッシュボード（開発用）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 機能（プログラム内から呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）
    - gpt-4o-mini を利用する設計
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要な挙動・運用注意

- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を使用）
- Monitoring は環境にかかわらず Settings.sqlite_path（本番 monitoring DB）を使用する仕様の箇所があります（設計上の意図に注意）
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine 側で停止シグナルとして扱われます。KillSwitch は監視コンポーネントからフラグを生成します
- PID ファイルの stale（存在するがプロセスがいない）検出時は自動で削除・アラート登録されます
- AI 呼び出しは外部 API（OpenAI）に依存するため、API 失敗時はフェイルセーフ（スコア=0 やスキップ）で継続する設計になっています
- MONITOR_POLL_INTERVAL に 0 や負の値を設定するとデフォルト（60秒）にフォールバックします

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / Settings 管理
    - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py          — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py   — 市場レジーム判定（MA + マクロニュース）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - __init__.py
      - monitoring_db.py      — SQLite テーブル初期化・CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
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
      - (その他のブローカ関連 / order_repository 等)
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py    — プロセス優先度 / CPU affinity

- data/ (既定)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag

---

## 開発者向けメモ

- Settings は .env, .env.local を自動でロードします（OS 環境変数は保護）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DB スキーマの初期化・マイグレーションは monitoring_db.init_monitoring_db() が担います。実行前に DB ファイルを作成するか、スクリプトが自動作成します
- OpenAI 呼び出し部分は retry/backoff のロジックやレスポンス検証が組み込まれており、フェイルセーフを重視した実装になっています
- streamlit ダッシュボードは monitoring DB を read-only で開きます（URI に ?mode=ro を付与）

---

## よく使うコマンドまとめ

- 監視ループ:
  KABUSYS_ENV=development MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README の内容はコードベースの抜粋に基づいて作成しています。追加のドキュメント（.env.example、requirements.txt、運用手順など）があればさらに具体的なセットアップ・運用手順を追記できます。必要なら .env.example や systemd/pm2 などの運用ユニットファイルの例も作成します。どの追加情報が欲しいか教えてください。